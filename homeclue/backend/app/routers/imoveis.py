import csv
import io

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.dependencies import obter_imobiliaria_atual
from app.core.limiter import limiter
from app.db.session import obter_db
from app.models import Imobiliaria, Imovel, Lead
from app.schemas.imovel import (
    DescricaoGerada,
    ImovelEntrada,
    ImovelSaida,
    PedidoDescricao,
    ResultadoImportacao,
)
from app.services import ia, limites
from app.services.vocabulario import CARACTERISTICAS, TIPOS

router = APIRouter(prefix="/api/imoveis", tags=["imóveis"])

_TAMANHO_MAXIMO_CSV = 2 * 1024 * 1024


def _do_tenant(db: Session, imobiliaria: Imobiliaria, imovel_id: int) -> Imovel:
    imovel = db.get(Imovel, imovel_id)
    if imovel is None or imovel.imobiliaria_id != imobiliaria.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Imóvel não encontrado.")
    return imovel


@router.get("/vocabulario")
def vocabulario() -> dict:
    """Tipos e características aceitos — o painel monta o formulário a partir daqui."""
    return {"tipos": TIPOS, "caracteristicas": CARACTERISTICAS}


@router.get("", response_model=list[ImovelSaida])
def listar(imobiliaria: Imobiliaria = Depends(obter_imobiliaria_atual), db: Session = Depends(obter_db)) -> list[ImovelSaida]:
    leads_por_imovel = dict(
        db.execute(
            select(Lead.imovel_id, func.count(Lead.id))
            .where(Lead.imobiliaria_id == imobiliaria.id, Lead.imovel_id.is_not(None))
            .group_by(Lead.imovel_id)
        ).all()
    )
    imoveis = db.scalars(
        select(Imovel).where(Imovel.imobiliaria_id == imobiliaria.id).order_by(Imovel.criado_em.desc())
    ).all()
    return [
        ImovelSaida.model_validate(i).model_copy(update={"total_leads": leads_por_imovel.get(i.id, 0)})
        for i in imoveis
    ]


@router.post("", response_model=ImovelSaida, status_code=status.HTTP_201_CREATED)
def criar(
    dados: ImovelEntrada,
    imobiliaria: Imobiliaria = Depends(obter_imobiliaria_atual),
    db: Session = Depends(obter_db),
) -> Imovel:
    limites.garantir_vaga_imovel(db, imobiliaria)
    imovel = Imovel(imobiliaria_id=imobiliaria.id, **dados.model_dump())
    db.add(imovel)
    db.commit()
    db.refresh(imovel)
    return imovel


@router.put("/{imovel_id}", response_model=ImovelSaida)
def atualizar(
    imovel_id: int,
    dados: ImovelEntrada,
    imobiliaria: Imobiliaria = Depends(obter_imobiliaria_atual),
    db: Session = Depends(obter_db),
) -> Imovel:
    imovel = _do_tenant(db, imobiliaria, imovel_id)
    for campo, valor in dados.model_dump().items():
        setattr(imovel, campo, valor)
    db.commit()
    db.refresh(imovel)
    return imovel


@router.delete("/{imovel_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(
    imovel_id: int,
    imobiliaria: Imobiliaria = Depends(obter_imobiliaria_atual),
    db: Session = Depends(obter_db),
) -> None:
    db.delete(_do_tenant(db, imobiliaria, imovel_id))
    db.commit()


@router.post("/gerar-descricao", response_model=DescricaoGerada)
@limiter.limit("20/minute")
def gerar_descricao(
    request: Request,
    dados: PedidoDescricao,
    imobiliaria: Imobiliaria = Depends(obter_imobiliaria_atual),
) -> DescricaoGerada:
    descricao, fonte = ia.gerar_descricao(dados.model_dump())
    return DescricaoGerada(descricao=descricao, fonte=fonte)


@router.post("/importar", response_model=ResultadoImportacao)
async def importar_csv(
    arquivo: UploadFile = File(...),
    imobiliaria: Imobiliaria = Depends(obter_imobiliaria_atual),
    db: Session = Depends(obter_db),
) -> ResultadoImportacao:
    """Importa imóveis de uma planilha CSV (modelo disponível no painel).

    Colunas: titulo, tipo, finalidade, bairro, cidade, preco, quartos,
    banheiros, vagas, area_m2, caracteristicas (separadas por "|"),
    descricao, foto_url, codigo_referencia.
    """
    conteudo = await arquivo.read(_TAMANHO_MAXIMO_CSV + 1)
    if len(conteudo) > _TAMANHO_MAXIMO_CSV:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="Arquivo maior que 2 MB.")

    try:
        texto = conteudo.decode("utf-8-sig")
    except UnicodeDecodeError:
        texto = conteudo.decode("latin-1")

    # Planilhas brasileiras costumam exportar CSV com ";".
    cabecalho = texto.splitlines()[0] if texto.strip() else ""
    if not cabecalho:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Arquivo vazio.")
    delimitador = ";" if cabecalho.count(";") > cabecalho.count(",") else ","
    leitor = csv.DictReader(io.StringIO(texto), delimiter=delimitador)

    validos: list[ImovelEntrada] = []
    erros: list[str] = []
    for numero, linha in enumerate(leitor, start=2):
        linha = {(k or "").strip().lower(): (v or "").strip() for k, v in linha.items()}
        linha["caracteristicas"] = [c.strip() for c in linha.get("caracteristicas", "").split("|") if c.strip()]
        linha["preco"] = linha.get("preco", "").replace("R$", "").replace(".", "").replace(",", ".").strip()
        linha.setdefault("finalidade", "venda")
        linha["finalidade"] = linha["finalidade"] or "venda"
        for campo in ("quartos", "banheiros", "vagas", "area_m2"):
            if not linha.get(campo):
                linha[campo] = "0"
        try:
            validos.append(ImovelEntrada.model_validate(linha))
        except ValidationError as erro:
            primeiro = erro.errors()[0]
            campo = ".".join(str(p) for p in primeiro["loc"]) or "linha"
            erros.append(f"Linha {numero}: {campo} — {primeiro['msg']}")

    if validos:
        limites.garantir_vaga_imovel(db, imobiliaria, quantidade=len(validos))
        db.add_all(Imovel(imobiliaria_id=imobiliaria.id, **i.model_dump()) for i in validos)
        db.commit()

    return ResultadoImportacao(importados=len(validos), erros=erros[:50])
