from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import obter_usuario_atual
from app.db.session import obter_db
from app.models.busca_salva import BuscaSalva
from app.models.usuario import Usuario
from app.schemas.busca_salva import BuscaSalvaEntrada, BuscaSalvaPublica

router = APIRouter(prefix="/api/buscas-salvas", tags=["buscas salvas"])


@router.get("", response_model=list[BuscaSalvaPublica])
def listar_minhas_buscas(usuario_atual: Usuario = Depends(obter_usuario_atual)) -> list[BuscaSalva]:
    return usuario_atual.buscas_salvas


@router.post("", response_model=BuscaSalvaPublica, status_code=status.HTTP_201_CREATED)
def salvar_busca(
    dados: BuscaSalvaEntrada,
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(obter_db),
) -> BuscaSalva:
    busca = BuscaSalva(usuario_id=usuario_atual.id, texto_busca=dados.texto_busca)
    db.add(busca)
    db.commit()
    db.refresh(busca)
    return busca
