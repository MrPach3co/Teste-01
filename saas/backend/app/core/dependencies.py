from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decodificar_token_acesso
from app.db.session import obter_db
from app.models import Imobiliaria, Usuario

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

_erro_credenciais = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Não foi possível validar suas credenciais.",
    headers={"WWW-Authenticate": "Bearer"},
)


def obter_usuario_atual(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(obter_db),
) -> Usuario:
    if token is None:
        raise _erro_credenciais

    payload = decodificar_token_acesso(token)
    if payload is None or payload.get("sub") is None:
        raise _erro_credenciais

    usuario = db.get(Usuario, int(payload["sub"]))
    if usuario is None:
        raise _erro_credenciais

    return usuario


def obter_imobiliaria_atual(usuario: Usuario = Depends(obter_usuario_atual)) -> Imobiliaria:
    """Todo dado do painel é filtrado por esta imobiliária — é o que isola
    um cliente do outro (multi-tenant)."""
    return usuario.imobiliaria


def exigir_dono(usuario: Usuario = Depends(obter_usuario_atual)) -> Usuario:
    if usuario.papel != "dono":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas o dono da conta pode fazer isso.",
        )
    return usuario
