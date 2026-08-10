from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.core.textos_legais import TEXTO_CONSENTIMENTO_LGPD_V1
from app.db.session import obter_db
from app.models.lista_espera import ListaEspera
from app.schemas.lista_espera import ListaEsperaEntrada, ListaEsperaPublico

router = APIRouter(prefix="/api/lista-espera", tags=["lista de espera"])

limiter = Limiter(key_func=get_remote_address)


@router.post("", response_model=ListaEsperaPublico, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def entrar_na_lista(
    request: Request, dados: ListaEsperaEntrada, db: Session = Depends(obter_db)
) -> ListaEspera:
    if not dados.aceitou_termos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="É necessário aceitar o uso do seu e-mail para entrar na lista de espera.",
        )

    existente = db.query(ListaEspera).filter(ListaEspera.email == dados.email).first()
    if existente:
        return existente

    entrada = ListaEspera(
        email=dados.email,
        consentimento_lgpd_em=datetime.now(timezone.utc),
        consentimento_lgpd_texto=TEXTO_CONSENTIMENTO_LGPD_V1,
    )
    db.add(entrada)
    db.commit()
    db.refresh(entrada)
    return entrada


@router.delete("/{email}", status_code=status.HTTP_204_NO_CONTENT)
def sair_da_lista(email: str, db: Session = Depends(obter_db)) -> None:
    """Direito de eliminação da LGPD para quem só entrou na lista de espera (sem conta)."""
    entrada = db.query(ListaEspera).filter(ListaEspera.email == email).first()
    if entrada is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="E-mail não encontrado na lista.")
    db.delete(entrada)
    db.commit()
