from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decodificar_token_acesso
from app.db.session import obter_db
from app.models.usuario import Usuario

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
    if payload is None:
        raise _erro_credenciais

    usuario_id = payload.get("sub")
    if usuario_id is None:
        raise _erro_credenciais

    usuario = db.get(Usuario, int(usuario_id))
    if usuario is None:
        raise _erro_credenciais

    return usuario
