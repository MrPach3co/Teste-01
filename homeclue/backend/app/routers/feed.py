from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.dependencies import exigir_dono, obter_imobiliaria_atual
from app.core.tempo import agora_utc
from app.db.session import obter_db
from app.models import Imobiliaria, Usuario
from app.schemas.feed import FeedConfig, FeedStatus
from app.services.feed import baixar, sincronizar
from app.services.feed.parser import FormatoNaoReconhecido

router = APIRouter(prefix="/api/feed", tags=["feed XML"])

_TAMANHO_MAXIMO_ARQUIVO = baixar.TAMANHO_MAXIMO


def _status(imobiliaria: Imobiliaria) -> FeedStatus:
    return FeedStatus(
        url=imobiliaria.feed_url, formato=imobiliaria.feed_formato, status=imobiliaria.feed_status,
        mensagem=imobiliaria.feed_mensagem, total=imobiliaria.feed_total,
        ultima_sincronizacao=imobiliaria.feed_ultima_sincronizacao,
        proxima_sincronizacao=imobiliaria.feed_proxima_sincronizacao if imobiliaria.feed_url else None,
    )


def _rodar(db: Session, imobiliaria: Imobiliaria, conteudo: bytes | None) -> FeedStatus:
    try:
        sincronizar.sincronizar(db, imobiliaria, conteudo)
    except (baixar.FeedInvalido, FormatoNaoReconhecido, sincronizar.SincronizacaoFalhou) as erro:
        sincronizar.registrar_falha(db, imobiliaria, str(erro))
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(erro))
    return _status(imobiliaria)


@router.get("", response_model=FeedStatus)
def obter(imobiliaria: Imobiliaria = Depends(obter_imobiliaria_atual)) -> FeedStatus:
    return _status(imobiliaria)


@router.put("", response_model=FeedStatus)
def configurar(dados: FeedConfig, dono: Usuario = Depends(exigir_dono), db: Session = Depends(obter_db)) -> FeedStatus:
    """Salva o endereço do feed e já sincroniza uma vez, para a imobiliária
    ver na hora se deu certo."""
    try:
        baixar.validar_endereco(dados.url)
    except baixar.FeedInvalido as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro))
    imobiliaria = dono.imobiliaria
    imobiliaria.feed_url = dados.url
    imobiliaria.feed_status = "pendente"
    imobiliaria.feed_proxima_sincronizacao = agora_utc()
    db.commit()
    return _rodar(db, imobiliaria, None)


@router.post("/sincronizar", response_model=FeedStatus)
def sincronizar_agora(dono: Usuario = Depends(exigir_dono), db: Session = Depends(obter_db)) -> FeedStatus:
    if not dono.imobiliaria.feed_url:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Configure o endereço do feed primeiro.")
    return _rodar(db, dono.imobiliaria, None)


@router.post("/arquivo", response_model=FeedStatus)
async def enviar_arquivo(arquivo: UploadFile = File(...), dono: Usuario = Depends(exigir_dono),
                         db: Session = Depends(obter_db)) -> FeedStatus:
    """Para sistemas que só exportam o XML como arquivo (ou para testar)."""
    conteudo = await arquivo.read(_TAMANHO_MAXIMO_ARQUIVO + 1)
    if len(conteudo) > _TAMANHO_MAXIMO_ARQUIVO:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="Arquivo maior que 60 MB.")
    try:
        conteudo = baixar._descompactar_se_preciso(conteudo)
    except baixar.FeedInvalido as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro))
    return _rodar(db, dono.imobiliaria, conteudo)


@router.delete("", response_model=FeedStatus)
def remover(dono: Usuario = Depends(exigir_dono), db: Session = Depends(obter_db)) -> FeedStatus:
    """Para de sincronizar. Os imóveis que vieram do feed continuam no ar até
    serem desativados."""
    imobiliaria = dono.imobiliaria
    imobiliaria.feed_url = None
    imobiliaria.feed_proxima_sincronizacao = None
    imobiliaria.feed_status = None
    db.commit()
    return _status(imobiliaria)
