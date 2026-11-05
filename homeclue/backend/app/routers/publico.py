"""API pública usada pelo widget no site da imobiliária.

Autenticada só pela chave pública (visível no HTML do cliente), por isso:
só leitura de imóveis no ar, criação de leads e eventos, com rate limit por
IP. Nada aqui expõe dados de outros clientes nem dados pessoais de leads.
"""

import json
from collections import Counter
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.limiter import limiter
from app.core.planos import (
    BUSCA_POR_FOTO,
    COMPARADOR,
    CONTEXTO_BAIRRO,
    LANCAMENTOS,
    MAQUETE_3D,
    MIDIA_DRONE,
    PLANTA_INTERATIVA,
    RANKINGS,
    SEM_MARCA,
    tem_recurso,
)
from app.core.tempo import agora_utc
from app.core.textos_legais import TEXTO_CONSENTIMENTO_LEAD_V2
from app.db.session import obter_db
from app.models import BairroInfo, Empreendimento, Evento, Imobiliaria, Imovel, RegistroBusca, Unidade
from app.schemas.lead import LeadEntradaPublica
from app.schemas.publico import BuscaEntrada, BuscaResposta, ConfigWidget, EventoEntrada, ImovelResultado, PontoSaida
from app.services import leads as servico_leads
from app.services import limites
from app.services.arquivos import url_do_arquivo
from app.services.busca import mensagens, motor
from app.services.busca.avaliacao import ImovelBusca, avaliar, taxa_de_match
from app.services.busca.criterios import Criterios, formatar_reais
from app.services.ia import cliente as ia_cliente
from app.services.ia import visao
from app.services.seed import CHAVE_DEMO
from app.services.vocabulario import CARACTERISTICAS, TIPOS, TIPOS_COMODO

router = APIRouter(prefix="/api/publico", tags=["widget público"])

_TAMANHO_MAXIMO_FOTO = 12 * 1024 * 1024


def _imobiliaria_pela_chave(chave: str, db: Session) -> Imobiliaria:
    imobiliaria = db.scalar(select(Imobiliaria).where(Imobiliaria.chave_publica == chave))
    if imobiliaria is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Widget não encontrado.")
    return imobiliaria


def _imovel_visivel(db: Session, imobiliaria: Imobiliaria, imovel_id: int | None) -> Imovel | None:
    if imovel_id is None:
        return None
    imovel = db.get(Imovel, imovel_id)
    if imovel is None or imovel.imobiliaria_id != imobiliaria.id or not imovel.visivel:
        return None
    return imovel


def _tem_planta(imobiliaria: Imobiliaria, imovel: Imovel) -> bool:
    planta = imovel.planta or {}
    pode = tem_recurso(imobiliaria.plano, PLANTA_INTERATIVA) or imovel.maquete_liberada
    return bool(pode and planta.get("imagem") and planta.get("comodos"))


def _tem_maquete(imobiliaria: Imobiliaria, imovel: Imovel) -> bool:
    pode = tem_recurso(imobiliaria.plano, MAQUETE_3D) or imovel.maquete_liberada
    return bool(pode and len((imovel.planta or {}).get("comodos") or []) >= 2)


def _exemplos(imoveis: list[Imovel]) -> list[str]:
    """Sugestões de busca montadas a partir da carteira real da imobiliária."""
    combinacoes = Counter((i.finalidade, i.tipo, i.bairro) for i in imoveis)
    exemplos: list[str] = []
    for (finalidade, tipo, bairro), _ in combinacoes.most_common(6):
        precos = sorted(i.preco for i in imoveis if (i.finalidade, i.tipo, i.bairro) == (finalidade, tipo, bairro))
        teto = precos[len(precos) // 2] * 1.15
        passo = 500 if finalidade == "aluguel" else 50_000
        teto = ((teto + passo - 1) // passo) * passo
        nome = TIPOS[tipo].split(" / ")[0].lower()
        if finalidade == "aluguel":
            exemplos.append(f"Alugar {nome} em {bairro} até {formatar_reais(teto)} por mês")
        else:
            exemplos.append(f"{nome.capitalize()} em {bairro} até {formatar_reais(teto)}")
        if len(exemplos) == 2:
            break
    itens = Counter(c for i in imoveis for c in i.caracteristicas)
    if itens["jardim"] and itens["pet-friendly"]:
        exemplos.append("Casa com quintal pra cachorro e 3 quartos")
    if itens["lareira"] or itens["vista-montanha"]:
        exemplos.append("Quero lareira e vista para a serra, perto de escola")
    if len(exemplos) < 3:
        exemplos.append("Apartamento de 2 quartos com sala clara, perto do comércio")
    return exemplos[:4]


@router.get("/{chave}/config", response_model=ConfigWidget)
@limiter.limit("60/minute")
def config(request: Request, chave: str, db: Session = Depends(obter_db)) -> ConfigWidget:
    imobiliaria = _imobiliaria_pela_chave(chave, db)
    imoveis = motor.imoveis_visiveis(db, imobiliaria.id)
    lancamentos = 0
    if tem_recurso(imobiliaria.plano, LANCAMENTOS):
        lancamentos = len(db.scalars(select(Empreendimento.id).where(
            Empreendimento.imobiliaria_id == imobiliaria.id, Empreendimento.ativo.is_(True))).all())
    plano = imobiliaria.plano
    return ConfigWidget(
        nome=imobiliaria.nome,
        cor_primaria=imobiliaria.cor_primaria,
        logo_url=url_do_arquivo(imobiliaria.logo_arquivo_id) if imobiliaria.logo_arquivo_id else None,
        whatsapp=servico_leads.destino_whatsapp(imobiliaria, None) is not None
        or any(i.corretor and i.corretor.whatsapp for i in imoveis),
        mostrar_marca=not tem_recurso(plano, SEM_MARCA),
        exemplos=_exemplos(imoveis),
        recursos={
            "voz": True,
            "busca_por_foto": tem_recurso(plano, BUSCA_POR_FOTO) and ia_cliente.disponivel()
            and not limites.cota_de_buscas_esgotada(db, imobiliaria),
            "comparador": tem_recurso(plano, COMPARADOR),
            "rankings": tem_recurso(plano, RANKINGS),
            "contexto_bairro": tem_recurso(plano, CONTEXTO_BAIRRO),
        },
        lancamentos=lancamentos,
    )


def _resultado(imobiliaria: Imobiliaria, item: motor.ItemResultado) -> ImovelResultado:
    imovel = item.imovel
    return ImovelResultado(
        id=imovel.id, titulo=imovel.titulo, tipo=imovel.tipo, tipo_rotulo=TIPOS.get(imovel.tipo, imovel.tipo),
        finalidade=imovel.finalidade, preco=imovel.preco, preco_aluguel=imovel.preco_aluguel,
        condominio=imovel.condominio, bairro=imovel.bairro, cidade=imovel.cidade, quartos=imovel.quartos,
        suites=imovel.suites, banheiros=imovel.banheiros, vagas=imovel.vagas, area_m2=imovel.area_m2,
        codigo_referencia=imovel.codigo_referencia, foto=(imovel.fotos[0]["url"] if imovel.fotos else None),
        total_fotos=len(imovel.fotos or []), match=item.match,
        pontos=[PontoSaida(**{k: v for k, v in p.para_dict().items() if k != "peso"}) for p in item.pontos],
        tem_planta=_tem_planta(imobiliaria, imovel), tem_maquete=_tem_maquete(imobiliaria, imovel),
        tem_video=bool(imovel.video_url or (imovel.video_drone_url and tem_recurso(imobiliaria.plano, MIDIA_DRONE))),
    )


def _registrar_e_responder(db: Session, imobiliaria: Imobiliaria, resultado: motor.ResultadoBusca, texto: str,
                           sessao: str | None, turno: int, modo: str, descricao_foto: str | None = None) -> BuscaResposta:
    lacunas = {
        str(i.imovel.id): [p.criterio for p in i.pontos if p.status == "nao_informado"]
        for i in resultado.itens if any(p.status == "nao_informado" for p in i.pontos)
    }
    matches = [i.match for i in resultado.itens if i.match is not None]
    criterios_dict = resultado.criterios.para_dict()
    registro = RegistroBusca(
        imobiliaria_id=imobiliaria.id, sessao=sessao, turno=turno, modo=modo, texto=texto or "(foto)",
        fonte=resultado.fonte, criterios=criterios_dict,
        resumo=None if resultado.criterios.vazio() else resultado.criterios.resumo(),
        total_resultados=len(resultado.itens), melhor_match=max(matches) if matches else None,
        bons_resultados=sum(1 for m in matches if m >= 70), resultados_ids=[i.imovel.id for i in resultado.itens],
        lacunas=lacunas, modelo=resultado.uso.modelo, tokens_entrada=resultado.uso.tokens_entrada,
        tokens_saida=resultado.uso.tokens_saida, custo_usd=resultado.uso.custo_usd,
    )
    db.add(registro)
    db.commit()
    return BuscaResposta(
        busca_id=registro.id, mensagem=resultado.mensagem, fonte=resultado.fonte, criterios=criterios_dict,
        entendido=resultado.criterios.rotulos(), resumo=registro.resumo, avisos=resultado.avisos,
        sugestoes=resultado.sugestoes, resultados=[_resultado(imobiliaria, i) for i in resultado.itens],
        rankings=resultado.rankings, descricao_foto=descricao_foto,
    )


def _garantir_cota(db: Session, imobiliaria: Imobiliaria) -> None:
    if limites.cota_de_buscas_esgotada(db, imobiliaria):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="A busca inteligente está temporariamente indisponível. Fale com a imobiliária pelo contato abaixo.",
        )


@router.post("/{chave}/buscar", response_model=BuscaResposta)
@limiter.limit("20/minute")
def buscar(request: Request, chave: str, dados: BuscaEntrada, db: Session = Depends(obter_db)) -> BuscaResposta:
    imobiliaria = _imobiliaria_pela_chave(chave, db)
    # Cota de buscas com IA esgotada: a busca do site continua funcionando no
    # motor de regras (sem custo) até virar o mês ou a imobiliária mudar de plano.
    com_ia = not limites.cota_de_buscas_esgotada(db, imobiliaria)
    resultado = motor.executar(db, imobiliaria, dados.texto, Criterios.de_dict(dados.criterios), dados.historico,
                               usar_ia=com_ia)
    return _registrar_e_responder(db, imobiliaria, resultado, dados.texto, dados.sessao, dados.turno, dados.modo)


@router.post("/{chave}/buscar-por-foto", response_model=BuscaResposta)
@limiter.limit("6/minute")
async def buscar_por_foto(request: Request, chave: str, foto: UploadFile = File(...), sessao: str | None = Form(None),
                          turno: int = Form(1), criterios: str | None = Form(None),
                          db: Session = Depends(obter_db)) -> BuscaResposta:
    """O comprador manda uma foto de referência. A foto é usada só para esta
    busca e não é guardada."""
    imobiliaria = _imobiliaria_pela_chave(chave, db)
    if not (tem_recurso(imobiliaria.plano, BUSCA_POR_FOTO) and ia_cliente.disponivel()):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Busca por foto indisponível.")
    _garantir_cota(db, imobiliaria)
    conteudo = await foto.read(_TAMANHO_MAXIMO_FOTO + 1)
    if len(conteudo) > _TAMANHO_MAXIMO_FOTO:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="Foto maior que 12 MB.")
    uso = ia_cliente.UsoIA()
    try:
        descricao = visao.descrever_foto_referencia(conteudo, uso)
    except visao.FotoInvalida as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro))
    if descricao is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="Não conseguimos analisar a foto agora. Tente descrever com palavras.")
    if not descricao["e_imovel"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Essa foto não parece ser de um imóvel. Tente outra, ou descreva o que procura.")
    try:
        anteriores = Criterios.de_dict(json.loads(criterios)) if criterios else Criterios()
    except json.JSONDecodeError:
        anteriores = Criterios()
    resultado = motor.executar(db, imobiliaria, "", anteriores, [], criterios_extra=visao.criterios_da_foto(descricao))
    resultado.uso.tokens_entrada += uso.tokens_entrada
    resultado.uso.tokens_saida += uso.tokens_saida
    resultado.uso.custo_usd += uso.custo_usd
    resultado.uso.modelo = uso.modelo
    return _registrar_e_responder(db, imobiliaria, resultado, "", sessao, turno, "foto",
                                  descricao_foto=descricao["descricao"])


def _contexto_publico(imovel: Imovel) -> dict | None:
    contexto = imovel.contexto or {}
    if not contexto.get("categorias"):
        return None
    return {"categorias": contexto["categorias"], "aproximado": contexto.get("aproximado", True),
            "fonte": "© colaboradores do OpenStreetMap"}


@router.get("/{chave}/imoveis/{imovel_id}")
@limiter.limit("60/minute")
def detalhe(request: Request, chave: str, imovel_id: int, sessao: str | None = None,
            db: Session = Depends(obter_db)) -> dict:
    imobiliaria = _imobiliaria_pela_chave(chave, db)
    imovel = _imovel_visivel(db, imobiliaria, imovel_id)
    if imovel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Imóvel não encontrado.")
    db.add(Evento(imobiliaria_id=imobiliaria.id, imovel_id=imovel.id, tipo="visualizacao", sessao=sessao))
    db.commit()

    plano = imobiliaria.plano
    bairro = db.scalar(select(BairroInfo).where(BairroInfo.imobiliaria_id == imobiliaria.id,
                                                BairroInfo.nome == imovel.bairro))
    planta = None
    if _tem_planta(imobiliaria, imovel):
        planta = {"imagem": imovel.planta["imagem"], "comodos": imovel.planta["comodos"],
                  "tipos": TIPOS_COMODO}
    return {
        "id": imovel.id, "titulo": imovel.titulo, "tipo": imovel.tipo, "tipo_rotulo": TIPOS.get(imovel.tipo),
        "finalidade": imovel.finalidade, "preco": imovel.preco, "preco_aluguel": imovel.preco_aluguel,
        "condominio": imovel.condominio, "iptu": imovel.iptu, "bairro": imovel.bairro, "cidade": imovel.cidade,
        "uf": imovel.uf, "endereco": imovel.endereco if imovel.mostrar_endereco else None,
        "quartos": imovel.quartos, "suites": imovel.suites, "banheiros": imovel.banheiros, "vagas": imovel.vagas,
        "area_m2": imovel.area_m2, "area_terreno": imovel.area_terreno, "descricao": imovel.descricao,
        "caracteristicas": [CARACTERISTICAS[c] for c in imovel.caracteristicas if c in CARACTERISTICAS],
        "comodidades": imovel.comodidades, "fotos": imovel.fotos, "codigo_referencia": imovel.codigo_referencia,
        "url_anuncio": imovel.url_anuncio, "video_url": imovel.video_url,
        "video_drone_url": imovel.video_drone_url if tem_recurso(plano, MIDIA_DRONE) else None,
        "planta": planta, "maquete": _tem_maquete(imobiliaria, imovel),
        "area_para_maquete": imovel.area_m2,
        "contexto": _contexto_publico(imovel) if tem_recurso(plano, CONTEXTO_BAIRRO) else None,
        "bairro_info": {"descricao": bairro.descricao, "valorizacao": bairro.valorizacao,
                        "valorizacao_justificativa": bairro.valorizacao_justificativa} if bairro else None,
        "whatsapp": servico_leads.destino_whatsapp(imobiliaria, imovel) is not None,
    }


def _pagina_simples(titulo: str, texto: str) -> HTMLResponse:
    html = (f"<!doctype html><html lang='pt-BR'><meta charset='utf-8'><meta name='viewport' "
            f"content='width=device-width,initial-scale=1'><title>{titulo}</title><body style='font-family:system-ui;"
            f"padding:32px;max-width:520px;margin:auto;color:#1B1A17'><h2>{titulo}</h2><p>{texto}</p></body></html>")
    return HTMLResponse(html, status_code=404)


@router.get("/{chave}/whatsapp", include_in_schema=False)
@limiter.limit("15/minute")
def whatsapp(request: Request, chave: str, imovel: int | None = None, unidade: int | None = None,
             busca: int | None = None, sessao: str | None = None, db: Session = Depends(obter_db)):
    """Botão de lead: registra o contato (sem dado pessoal) e leva a pessoa ao
    WhatsApp do corretor com o resumo da busca e um código para acompanhar."""
    imobiliaria = _imobiliaria_pela_chave(chave, db)
    imovel_obj = _imovel_visivel(db, imobiliaria, imovel)
    unidade_obj = db.get(Unidade, unidade) if unidade else None
    if unidade_obj is not None and unidade_obj.empreendimento.imobiliaria_id != imobiliaria.id:
        unidade_obj = None
    registro = db.get(RegistroBusca, busca) if busca else None
    if registro is not None and registro.imobiliaria_id != imobiliaria.id:
        registro = None

    numero = servico_leads.destino_whatsapp(imobiliaria, imovel_obj)
    if numero is None:
        return _pagina_simples("WhatsApp indisponível",
                               f"A {imobiliaria.nome} ainda não configurou um WhatsApp. Volte e use o formulário de contato.")

    criterios = Criterios.de_dict(registro.criterios) if registro and registro.criterios else Criterios()
    match, pontos_ok = None, []
    if imovel_obj is not None and not criterios.vazio():
        pontos = avaliar(ImovelBusca.de_imovel(imovel_obj), criterios)
        match = taxa_de_match(pontos)
        pontos_ok = [p.criterio for p in pontos if p.status == "atende"]

    lead = servico_leads.criar_lead(db, imobiliaria, origem="whatsapp", imovel=imovel_obj, unidade=unidade_obj,
                                    busca=registro, sessao=sessao, match=match)
    descricao_unidade = None
    if unidade_obj is not None:
        u = unidade_obj
        detalhes = ", ".join(x for x in [f"{u.quartos} quartos" if u.quartos else "", f"{u.area_m2:g} m²" if u.area_m2 else "",
                                          formatar_reais(u.preco) if u.preco else ""] if x)
        descricao_unidade = f"unidade {u.codigo} ({u.torre}) do {u.empreendimento.nome}" + (f" — {detalhes}" if detalhes else "")
    texto = mensagens.texto_whatsapp(
        imobiliaria=imobiliaria.nome, titulo=imovel_obj.titulo if imovel_obj else None,
        codigo_ref=imovel_obj.codigo_referencia if imovel_obj else None,
        preco=imovel_obj.preco_para(criterios.finalidade) if imovel_obj else None,
        aluguel=bool(imovel_obj and (criterios.finalidade == "aluguel" or imovel_obj.finalidade == "aluguel")),
        url_anuncio=imovel_obj.url_anuncio if imovel_obj else None,
        resumo=None if criterios.vazio() else criterios.resumo(), match=match, pontos_ok=pontos_ok,
        codigo_lead=lead.codigo, unidade=descricao_unidade,
    )
    if imobiliaria.chave_publica == CHAVE_DEMO:
        return _previa_whatsapp_demo(texto, lead.codigo)
    return RedirectResponse(f"https://wa.me/{numero}?text={quote(texto)}", status_code=status.HTTP_302_FOUND)


def _previa_whatsapp_demo(texto: str, codigo: str) -> HTMLResponse:
    """Na demonstração não existe corretor de verdade: mostramos a mensagem que
    iria para o WhatsApp em vez de abrir uma conversa com um número qualquer."""
    from html import escape

    html = (
        "<!doctype html><html lang='pt-BR'><meta charset='utf-8'><meta name='viewport' content='width=device-width,"
        "initial-scale=1'><title>Prévia do WhatsApp — Homeclue</title><body style='font-family:system-ui;background:"
        "#efeae2;margin:0;padding:24px;color:#1B1A17'><div style='max-width:460px;margin:auto'>"
        "<p style='font-size:14px;color:#5A564C'>Demonstração: numa imobiliária de verdade, este botão abre o "
        "WhatsApp do corretor já com a mensagem abaixo escrita.</p><div style='background:#d9fdd3;border-radius:"
        "12px;padding:14px 16px;white-space:pre-wrap;font-size:15px;line-height:1.45;box-shadow:0 1px 1px "
        f"rgba(0,0,0,.08)'>{escape(texto)}</div><p style='font-size:14px;color:#5A564C;margin-top:16px'>O lead "
        f"<strong>{escape(codigo)}</strong> também entrou no painel da imobiliária, com o resumo da busca, para o "
        "corretor acompanhar até o fechamento.</p></div></body></html>"
    )
    return HTMLResponse(html)


@router.post("/{chave}/leads", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def criar_lead(request: Request, chave: str, dados: LeadEntradaPublica, db: Session = Depends(obter_db)) -> dict:
    imobiliaria = _imobiliaria_pela_chave(chave, db)
    if not dados.aceitou_contato:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="É preciso autorizar o contato para enviarmos seus dados ao corretor.")
    imovel = _imovel_visivel(db, imobiliaria, dados.imovel_id)  # ignora imóvel de outra imobiliária
    unidade = db.get(Unidade, dados.unidade_id) if dados.unidade_id else None
    if unidade is not None and unidade.empreendimento.imobiliaria_id != imobiliaria.id:
        unidade = None
    registro = db.get(RegistroBusca, dados.busca_id) if dados.busca_id else None
    if registro is not None and registro.imobiliaria_id != imobiliaria.id:
        registro = None
    lead = servico_leads.criar_lead(
        db, imobiliaria, origem="formulario", imovel=imovel, unidade=unidade, busca=registro, sessao=dados.sessao,
        nome=dados.nome.strip(), email=dados.email, telefone=dados.telefone, mensagem=dados.mensagem.strip(),
        consentimento_em=agora_utc(), consentimento_texto=TEXTO_CONSENTIMENTO_LEAD_V2,
    )
    return {"mensagem": "Recebemos seu contato! Um corretor vai falar com você em breve.", "codigo": lead.codigo}


@router.post("/{chave}/eventos", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("60/minute")
def registrar_evento(request: Request, chave: str, dados: EventoEntrada, db: Session = Depends(obter_db)) -> None:
    imobiliaria = _imobiliaria_pela_chave(chave, db)
    imovel = _imovel_visivel(db, imobiliaria, dados.imovel_id)
    db.add(Evento(imobiliaria_id=imobiliaria.id, imovel_id=imovel.id if imovel else None, tipo=dados.tipo,
                  sessao=dados.sessao))
    db.commit()


def _resumo_unidades(unidades: list[Unidade]) -> dict:
    contagem = Counter(u.status for u in unidades)
    precos = [u.preco for u in unidades if u.preco and u.status == "disponivel"]
    return {"disponivel": contagem["disponivel"], "reservada": contagem["reservada"], "vendida": contagem["vendida"],
            "preco_a_partir": min(precos) if precos else None}


@router.get("/{chave}/lancamentos")
@limiter.limit("60/minute")
def listar_lancamentos(request: Request, chave: str, db: Session = Depends(obter_db)) -> list[dict]:
    imobiliaria = _imobiliaria_pela_chave(chave, db)
    if not tem_recurso(imobiliaria.plano, LANCAMENTOS):
        return []
    return [
        {"id": e.id, "nome": e.nome, "bairro": e.bairro, "cidade": e.cidade, "previsao_entrega": e.previsao_entrega,
         "foto": e.fotos[0]["url"] if e.fotos else None, **_resumo_unidades(e.unidades)}
        for e in db.scalars(select(Empreendimento).where(Empreendimento.imobiliaria_id == imobiliaria.id,
                                                         Empreendimento.ativo.is_(True))).all()
    ]


@router.get("/{chave}/lancamentos/{empreendimento_id}")
@limiter.limit("60/minute")
def espelho(request: Request, chave: str, empreendimento_id: int, sessao: str | None = None,
            db: Session = Depends(obter_db)) -> dict:
    imobiliaria = _imobiliaria_pela_chave(chave, db)
    emp = db.get(Empreendimento, empreendimento_id)
    if emp is None or emp.imobiliaria_id != imobiliaria.id or not emp.ativo or not tem_recurso(imobiliaria.plano, LANCAMENTOS):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lançamento não encontrado.")
    db.add(Evento(imobiliaria_id=imobiliaria.id, tipo="espelho", sessao=sessao))
    db.commit()
    return {
        "id": emp.id, "nome": emp.nome, "bairro": emp.bairro, "cidade": emp.cidade, "descricao": emp.descricao,
        "previsao_entrega": emp.previsao_entrega, "fotos": emp.fotos, "torres": emp.torres,
        "resumo": _resumo_unidades(emp.unidades),
        "unidades": [
            {"id": u.id, "torre": u.torre, "andar": u.andar, "posicao": u.posicao, "codigo": u.codigo,
             "status": u.status, "preco": u.preco if u.status != "vendida" else None, "area_m2": u.area_m2,
             "quartos": u.quartos, "suites": u.suites, "vagas": u.vagas, "tipologia": u.tipologia}
            for u in emp.unidades
        ],
        "whatsapp": servico_leads.destino_whatsapp(imobiliaria, None) is not None,
    }



