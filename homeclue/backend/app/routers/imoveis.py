import csv
import io
from datetime import timedelta

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.dependencies import exigir_dono, obter_imobiliaria_atual
from app.core.limiter import limiter
from app.core.planos import ANALISE_FOTOS, PLANTA_INTERATIVA, tem_recurso
from app.core.tempo import agora_utc
from app.db.session import obter_db
from app.models import Arquivo, Evento, Imobiliaria, Imovel, Lead, Usuario
from app.schemas.imovel import (
    CAMPOS_EDITAVEIS_EM_IMOVEL_DO_FEED,
    DescricaoGerada,
    ImovelEntrada,
    ImovelSaida,
    PedidoDescricao,
    PlantaEntrada,
    ResultadoImportacao,
)
from app.services import arquivos, cobranca, limites
from app.services.ia import descricao as ia_descricao
from app.services.tarefas import enfileirar
from app.services.vocabulario import CARACTERISTICAS, TIPOS, TIPOS_COMODO

router = APIRouter(prefix="/api/imoveis", tags=["imóveis"])

_TAMANHO_MAXIMO_CSV = 2 * 1024 * 1024


def _do_tenant(db: Session, imobiliaria: Imobiliaria, imovel_id: int) -> Imovel:
    imovel = db.get(Imovel, imovel_id)
    if imovel is None or imovel.imobiliaria_id != imobiliaria.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Imóvel não encontrado.")
    return imovel


def _validar_arquivos(db: Session, imobiliaria_id: int, urls: list[str]) -> None:
    """Fotos enviadas ao painel só podem ser usadas pela própria imobiliária."""
    for url in urls:
        if url and url.startswith("/api/arquivos/"):
            arquivo = db.get(Arquivo, url.rsplit("/", 1)[-1])
            if arquivo is None or arquivo.imobiliaria_id != imobiliaria_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Foto inválida.")


def _validar_corretor(db: Session, imobiliaria_id: int, corretor_id: int | None) -> None:
    if corretor_id is None:
        return
    corretor = db.get(Usuario, corretor_id)
    if corretor is None or corretor.imobiliaria_id != imobiliaria_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Corretor inválido.")


def _agendar_enriquecimento(db: Session, imobiliaria: Imobiliaria, imovel: Imovel, local_mudou: bool,
                            fotos_mudaram: bool) -> None:
    if local_mudou or imovel.contexto is None:
        enfileirar(db, "contexto_bairro", imobiliaria_id=imobiliaria.id, imovel_id=imovel.id, commit=False)
    if fotos_mudaram and imovel.fotos and imobiliaria.analisar_fotos and tem_recurso(imobiliaria.plano, ANALISE_FOTOS):
        imovel.analise_fotos = None
        enfileirar(db, "analisar_fotos", imobiliaria_id=imobiliaria.id, imovel_id=imovel.id, commit=False)


def _saida(imovel: Imovel, leads: dict[int, int], visitas: dict[int, int]) -> ImovelSaida:
    return ImovelSaida.model_validate(imovel).model_copy(
        update={"total_leads": leads.get(imovel.id, 0), "visualizacoes": visitas.get(imovel.id, 0)}
    )


@router.get("/vocabulario")
def vocabulario() -> dict:
    """Tipos, características e cômodos aceitos — o painel monta os formulários a partir daqui."""
    return {"tipos": TIPOS, "caracteristicas": CARACTERISTICAS, "tipos_comodo": TIPOS_COMODO}


@router.get("", response_model=list[ImovelSaida])
def listar(imobiliaria: Imobiliaria = Depends(obter_imobiliaria_atual), db: Session = Depends(obter_db)):
    leads = dict(db.execute(
        select(Lead.imovel_id, func.count(Lead.id))
        .where(Lead.imobiliaria_id == imobiliaria.id, Lead.imovel_id.is_not(None)).group_by(Lead.imovel_id)
    ).all())
    visitas = dict(db.execute(
        select(Evento.imovel_id, func.count(Evento.id))
        .where(Evento.imobiliaria_id == imobiliaria.id, Evento.tipo == "visualizacao",
               Evento.criado_em >= agora_utc() - timedelta(days=30))
        .group_by(Evento.imovel_id)
    ).all())
    imoveis = db.scalars(
        select(Imovel).where(Imovel.imobiliaria_id == imobiliaria.id)
        .order_by(Imovel.removido_do_feed_em.is_not(None), Imovel.criado_em.desc())
    ).all()
    return [_saida(i, leads, visitas) for i in imoveis]


@router.get("/{imovel_id}", response_model=ImovelSaida)
def obter(imovel_id: int, imobiliaria: Imobiliaria = Depends(obter_imobiliaria_atual), db: Session = Depends(obter_db)):
    return _saida(_do_tenant(db, imobiliaria, imovel_id), {}, {})


@router.post("", response_model=ImovelSaida, status_code=status.HTTP_201_CREATED)
def criar(dados: ImovelEntrada, imobiliaria: Imobiliaria = Depends(obter_imobiliaria_atual),
          db: Session = Depends(obter_db)):
    limites.garantir_vaga_imovel(db, imobiliaria)
    _validar_arquivos(db, imobiliaria.id, [f.url for f in dados.fotos])
    _validar_corretor(db, imobiliaria.id, dados.corretor_id)
    campos = dados.model_dump()
    campos["fotos"] = [f.model_dump() for f in dados.fotos]
    imovel = Imovel(imobiliaria_id=imobiliaria.id, origem="manual",
                    coordenadas_aproximadas=dados.latitude is None, **campos)
    db.add(imovel)
    db.flush()
    _agendar_enriquecimento(db, imobiliaria, imovel, local_mudou=True, fotos_mudaram=True)
    db.commit()
    db.refresh(imovel)
    return _saida(imovel, {}, {})


@router.put("/{imovel_id}", response_model=ImovelSaida)
def atualizar(imovel_id: int, dados: ImovelEntrada, imobiliaria: Imobiliaria = Depends(obter_imobiliaria_atual),
              db: Session = Depends(obter_db)):
    imovel = _do_tenant(db, imobiliaria, imovel_id)
    _validar_arquivos(db, imobiliaria.id, [f.url for f in dados.fotos])
    _validar_corretor(db, imobiliaria.id, dados.corretor_id)
    campos = dados.model_dump()
    campos["fotos"] = [f.model_dump() for f in dados.fotos]
    if imovel.origem == "feed":
        # O feed é a fonte da verdade do anúncio; aqui só o que é da Homeclue.
        campos = {k: v for k, v in campos.items() if k in CAMPOS_EDITAVEIS_EM_IMOVEL_DO_FEED}
    local_antes = (imovel.bairro, imovel.cidade, imovel.latitude, imovel.longitude)
    fotos_antes = [f.get("url") for f in imovel.fotos or []]
    for campo, valor in campos.items():
        setattr(imovel, campo, valor)
    if "latitude" in campos:
        imovel.coordenadas_aproximadas = campos["latitude"] is None
        if campos["latitude"] is None:
            imovel.longitude = None
    local_mudou = local_antes != (imovel.bairro, imovel.cidade, imovel.latitude, imovel.longitude)
    if local_mudou and imovel.latitude is None:
        imovel.contexto = None  # o bairro mudou: o contexto antigo não vale mais
    _agendar_enriquecimento(db, imobiliaria, imovel, local_mudou,
                            fotos_antes != [f.get("url") for f in imovel.fotos or []])
    db.commit()
    db.refresh(imovel)
    return _saida(imovel, {}, {})


@router.delete("/{imovel_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(imovel_id: int, imobiliaria: Imobiliaria = Depends(obter_imobiliaria_atual),
            db: Session = Depends(obter_db)) -> None:
    imovel = _do_tenant(db, imobiliaria, imovel_id)
    if imovel.origem == "feed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Este imóvel vem do feed: tire-o do seu sistema ou desative-o aqui.")
    db.delete(imovel)
    db.commit()


@router.post("/{imovel_id}/fotos")
async def enviar_foto(imovel_id: int, arquivo: UploadFile = File(...),
                      imobiliaria: Imobiliaria = Depends(obter_imobiliaria_atual), db: Session = Depends(obter_db)):
    """Envia uma foto e devolve a URL. O painel decide onde usar (galeria do
    imóvel manual ou foto de um cômodo da planta)."""
    _do_tenant(db, imobiliaria, imovel_id)
    conteudo = await arquivo.read(arquivos.TAMANHO_MAXIMO_ENVIO + 1)
    try:
        novo = arquivos.salvar_imagem(db, imobiliaria.id, conteudo, "foto")
    except arquivos.ImagemInvalida as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro))
    db.commit()
    return {"url": arquivos.url_do_arquivo(novo.id), "largura": novo.largura, "altura": novo.altura}


@router.post("/{imovel_id}/planta/imagem")
async def enviar_planta(imovel_id: int, arquivo: UploadFile = File(...),
                        imobiliaria: Imobiliaria = Depends(obter_imobiliaria_atual), db: Session = Depends(obter_db)):
    imovel = _do_tenant(db, imobiliaria, imovel_id)
    if not (tem_recurso(imobiliaria.plano, PLANTA_INTERATIVA) or imovel.maquete_liberada):
        limites.garantir_recurso(imobiliaria, PLANTA_INTERATIVA)
    conteudo = await arquivo.read(arquivos.TAMANHO_MAXIMO_ENVIO + 1)
    try:
        novo = arquivos.salvar_imagem(db, imobiliaria.id, conteudo, "planta")
    except arquivos.ImagemInvalida as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro))
    db.commit()
    return {"url": arquivos.url_do_arquivo(novo.id), "largura": novo.largura, "altura": novo.altura}


@router.put("/{imovel_id}/planta", response_model=ImovelSaida)
def salvar_planta(imovel_id: int, dados: PlantaEntrada, imobiliaria: Imobiliaria = Depends(obter_imobiliaria_atual),
                  db: Session = Depends(obter_db)):
    imovel = _do_tenant(db, imobiliaria, imovel_id)
    if not (tem_recurso(imobiliaria.plano, PLANTA_INTERATIVA) or imovel.maquete_liberada):
        limites.garantir_recurso(imobiliaria, PLANTA_INTERATIVA)
    urls = [dados.imagem or ""] + [u for c in dados.comodos for u in c.fotos]
    _validar_arquivos(db, imobiliaria.id, urls)
    if not dados.imagem and not dados.comodos:
        imovel.planta = None
    else:
        imovel.planta = {"imagem": dados.imagem, "comodos": [c.model_dump() for c in dados.comodos]}
    db.commit()
    db.refresh(imovel)
    return _saida(imovel, {}, {})


@router.post("/{imovel_id}/contexto", status_code=status.HTTP_202_ACCEPTED)
def atualizar_contexto(imovel_id: int, imobiliaria: Imobiliaria = Depends(obter_imobiliaria_atual),
                       db: Session = Depends(obter_db)) -> dict:
    imovel = _do_tenant(db, imobiliaria, imovel_id)
    enfileirar(db, "contexto_bairro", imobiliaria_id=imobiliaria.id, imovel_id=imovel.id)
    return {"mensagem": "O contexto do bairro está sendo calculado e aparece em alguns minutos."}


@router.post("/{imovel_id}/analisar-fotos", status_code=status.HTTP_202_ACCEPTED)
def analisar_fotos(imovel_id: int, imobiliaria: Imobiliaria = Depends(obter_imobiliaria_atual),
                   db: Session = Depends(obter_db)) -> dict:
    imovel = _do_tenant(db, imobiliaria, imovel_id)
    limites.garantir_recurso(imobiliaria, ANALISE_FOTOS)
    if not imobiliaria.analisar_fotos:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Ative a análise de fotos em Widget no site → Inteligência das fotos.")
    enfileirar(db, "analisar_fotos", imobiliaria_id=imobiliaria.id, imovel_id=imovel.id)
    return {"mensagem": "As fotos estão sendo analisadas."}


@router.post("/{imovel_id}/maquete-avulsa")
def comprar_maquete(imovel_id: int, dono: Usuario = Depends(exigir_dono), db: Session = Depends(obter_db)) -> dict:
    imovel = _do_tenant(db, dono.imobiliaria, imovel_id)
    try:
        return {"url": cobranca.criar_checkout_maquete(dono.imobiliaria, dono.email, imovel)}
    except cobranca.CobrancaIndisponivel as erro:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(erro))


@router.post("/gerar-descricao", response_model=DescricaoGerada)
@limiter.limit("20/minute")
def gerar_descricao(request: Request, dados: PedidoDescricao,
                    imobiliaria: Imobiliaria = Depends(obter_imobiliaria_atual)) -> DescricaoGerada:
    texto, fonte, _uso = ia_descricao.gerar(dados.model_dump())
    return DescricaoGerada(descricao=texto, fonte=fonte)


_COLUNAS_NUMERICAS = ("quartos", "suites", "banheiros", "vagas", "area_m2", "area_terreno", "condominio", "iptu")


def _numero_csv(valor: str) -> str | None:
    valor = valor.replace("R$", "").strip()
    if not valor:
        return None
    if "," in valor:
        valor = valor.replace(".", "").replace(",", ".")
    elif valor.count(".") >= 1 and len(valor.split(".")[-1]) == 3:
        valor = valor.replace(".", "")
    return valor


@router.post("/importar", response_model=ResultadoImportacao)
async def importar_csv(arquivo: UploadFile = File(...), imobiliaria: Imobiliaria = Depends(obter_imobiliaria_atual),
                       db: Session = Depends(obter_db)) -> ResultadoImportacao:
    """Importa imóveis de uma planilha CSV (modelo disponível no painel).

    Colunas: titulo, tipo, finalidade, bairro, cidade, preco, quartos, suites,
    banheiros, vagas, area_m2, caracteristicas (separadas por "|"), descricao,
    foto_url, codigo_referencia.
    """
    conteudo = await arquivo.read(_TAMANHO_MAXIMO_CSV + 1)
    if len(conteudo) > _TAMANHO_MAXIMO_CSV:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="Arquivo maior que 2 MB.")
    try:
        texto = conteudo.decode("utf-8-sig")
    except UnicodeDecodeError:
        texto = conteudo.decode("latin-1")
    cabecalho = texto.splitlines()[0] if texto.strip() else ""
    if not cabecalho:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Arquivo vazio.")
    delimitador = ";" if cabecalho.count(";") > cabecalho.count(",") else ","

    validos: list[ImovelEntrada] = []
    erros: list[str] = []
    for numero, linha in enumerate(csv.DictReader(io.StringIO(texto), delimiter=delimitador), start=2):
        linha = {(k or "").strip().lower(): (v or "").strip() for k, v in linha.items()}
        foto = linha.pop("foto_url", "")
        linha["fotos"] = [{"url": foto}] if foto else []
        linha["caracteristicas"] = [c.strip() for c in linha.get("caracteristicas", "").split("|") if c.strip()]
        linha["preco"] = _numero_csv(linha.get("preco", "")) or ""
        linha["finalidade"] = linha.get("finalidade") or "venda"
        for campo in _COLUNAS_NUMERICAS:
            linha[campo] = _numero_csv(linha.get(campo, ""))
        try:
            validos.append(ImovelEntrada.model_validate(linha))
        except ValidationError as erro:
            primeiro = erro.errors()[0]
            campo = ".".join(str(p) for p in primeiro["loc"]) or "linha"
            erros.append(f"Linha {numero}: {campo} — {primeiro['msg']}")

    if validos:
        limites.garantir_vaga_imovel(db, imobiliaria, quantidade=len(validos))
        for dados in validos:
            campos = dados.model_dump()
            campos["fotos"] = [f.model_dump() for f in dados.fotos]
            imovel = Imovel(imobiliaria_id=imobiliaria.id, origem="manual", **campos)
            db.add(imovel)
            db.flush()
            _agendar_enriquecimento(db, imobiliaria, imovel, local_mudou=True, fotos_mudaram=True)
        db.commit()
    return ResultadoImportacao(importados=len(validos), erros=erros[:50])
