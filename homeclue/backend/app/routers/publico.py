"""API pública usada pelo widget embutido no site da imobiliária.

Autenticada só pela chave pública (que fica visível no HTML do cliente),
por isso: só leitura de imóveis ativos + criação de leads, e com rate
limit por IP.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.limiter import limiter
from app.core.planos import obter_plano
from app.core.textos_legais import TEXTO_CONSENTIMENTO_LEAD_V1
from app.db.session import obter_db
from app.models import Imobiliaria, Imovel, Lead, RegistroBusca
from app.schemas.lead import LeadEntradaPublica
from app.schemas.publico import (
    BuscaEntrada,
    BuscaResposta,
    ConfigWidget,
    ImovelResultado,
)
from app.services import busca, ia, limites

router = APIRouter(prefix="/api/publico", tags=["widget público"])


def _imobiliaria_pela_chave(chave: str, db: Session) -> Imobiliaria:
    imobiliaria = db.scalar(select(Imobiliaria).where(Imobiliaria.chave_publica == chave))
    if imobiliaria is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Widget não encontrado.")
    return imobiliaria


def _exemplos(imoveis: list[Imovel]) -> list[str]:
    """Sugestões de busca montadas a partir da carteira real da imobiliária."""
    exemplos: list[str] = []
    for imovel in imoveis[:12]:
        if len(exemplos) == 3:
            break
        verbo = "Alugar" if imovel.finalidade == "aluguel" else "Comprar"
        quartos = f" com {imovel.quartos} quartos" if imovel.quartos >= 2 else ""
        exemplo = f"{verbo} {imovel.tipo}{quartos} em {imovel.bairro}"
        if exemplo not in exemplos:
            exemplos.append(exemplo)
    return exemplos or ["Apartamento com 2 quartos perto do metrô", "Casa com piscina até 1 milhão"]


@router.get("/{chave}/config", response_model=ConfigWidget)
@limiter.limit("60/minute")
def config(request: Request, chave: str, db: Session = Depends(obter_db)) -> ConfigWidget:
    imobiliaria = _imobiliaria_pela_chave(chave, db)
    imoveis = db.scalars(
        select(Imovel).where(Imovel.imobiliaria_id == imobiliaria.id, Imovel.ativo.is_(True)).order_by(Imovel.id)
    ).all()
    return ConfigWidget(
        nome=imobiliaria.nome,
        cor_primaria=imobiliaria.cor_primaria,
        whatsapp=imobiliaria.whatsapp,
        mostrar_marca=obter_plano(imobiliaria.plano).marca_kaza_no_widget,
        exemplos=_exemplos(list(imoveis)),
    )


@router.post("/{chave}/buscar", response_model=BuscaResposta)
@limiter.limit("20/minute")
def buscar(request: Request, chave: str, dados: BuscaEntrada, db: Session = Depends(obter_db)) -> BuscaResposta:
    imobiliaria = _imobiliaria_pela_chave(chave, db)

    if limites.cota_de_buscas_esgotada(db, imobiliaria):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="A busca inteligente está temporariamente indisponível. Fale com a imobiliária pelo contato abaixo.",
        )

    imoveis = list(db.scalars(
        select(Imovel).where(Imovel.imobiliaria_id == imobiliaria.id, Imovel.ativo.is_(True))
    ).all())
    bairros = sorted({i.bairro for i in imoveis})

    filtros, fonte = ia.interpretar_busca(dados.texto, bairros)
    ranqueados = busca.ranquear(imoveis, filtros)

    db.add(RegistroBusca(
        imobiliaria_id=imobiliaria.id, texto=dados.texto, fonte=fonte, total_resultados=len(ranqueados)
    ))
    db.commit()

    resultados = [
        ImovelResultado(
            id=r.imovel.id,
            titulo=r.imovel.titulo,
            tipo=r.imovel.tipo,
            finalidade=r.imovel.finalidade,
            bairro=r.imovel.bairro,
            cidade=r.imovel.cidade,
            preco=r.imovel.preco,
            quartos=r.imovel.quartos,
            banheiros=r.imovel.banheiros,
            vagas=r.imovel.vagas,
            area_m2=r.imovel.area_m2,
            foto_url=r.imovel.foto_url,
            descricao=r.imovel.descricao,
            match=r.match,
            motivos=r.motivos,
        )
        for r in ranqueados
    ]

    if not resultados:
        mensagem = "Não encontrei imóveis com esse perfil agora. Deixe seu contato que um corretor te avisa quando surgir."
    else:
        melhor = resultados[0]
        mensagem = (
            f"Encontrei {len(resultados)} opç{'ões' if len(resultados) > 1 else 'ão'} para você. "
            f'A que mais combina é "{melhor.titulo}" ({melhor.match}% de match).'
        )

    return BuscaResposta(mensagem=mensagem, fonte=fonte, entendido=busca.resumir_filtros(filtros), resultados=resultados)


@router.post("/{chave}/leads", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def criar_lead(request: Request, chave: str, dados: LeadEntradaPublica, db: Session = Depends(obter_db)) -> dict:
    imobiliaria = _imobiliaria_pela_chave(chave, db)

    if not dados.aceitou_contato:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="É preciso autorizar o contato para enviarmos seus dados ao corretor.",
        )

    imovel_id = None
    if dados.imovel_id is not None:
        imovel = db.get(Imovel, dados.imovel_id)
        # Ignora silenciosamente um imovel_id de outra imobiliária.
        if imovel is not None and imovel.imobiliaria_id == imobiliaria.id:
            imovel_id = imovel.id

    db.add(Lead(
        imobiliaria_id=imobiliaria.id,
        imovel_id=imovel_id,
        nome=dados.nome.strip(),
        email=dados.email,
        telefone=dados.telefone,
        mensagem=dados.mensagem.strip(),
        busca_texto=dados.busca_texto,
        consentimento_em=datetime.now(timezone.utc),
        consentimento_texto=TEXTO_CONSENTIMENTO_LEAD_V1,
    ))
    db.commit()
    return {"mensagem": "Recebemos seu contato! Um corretor vai falar com você em breve."}
