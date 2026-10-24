import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.core.config import obter_settings

settings = obter_settings()

# bcrypt tem limite de 72 bytes por senha e lança erro acima disso, em vez
# de truncar em silêncio (o que faria duas senhas diferentes colidirem).
_MAX_BYTES_SENHA = 72


def gerar_hash_senha(senha: str) -> str:
    senha_bytes = senha.encode("utf-8")
    if len(senha_bytes) > _MAX_BYTES_SENHA:
        raise ValueError("Senha muito longa.")
    return bcrypt.hashpw(senha_bytes, bcrypt.gensalt()).decode("utf-8")


def verificar_senha(senha_texto_puro: str, senha_hash: str) -> bool:
    senha_bytes = senha_texto_puro.encode("utf-8")
    if len(senha_bytes) > _MAX_BYTES_SENHA:
        return False
    return bcrypt.checkpw(senha_bytes, senha_hash.encode("utf-8"))


def criar_token_acesso(dados: dict) -> str:
    para_codificar = dados.copy()
    para_codificar["exp"] = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expira_minutos)
    return jwt.encode(para_codificar, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decodificar_token_acesso(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None


def gerar_chave_publica() -> str:
    """Chave do widget. É pública (vai no HTML do site do cliente), então
    só dá acesso a buscar imóveis e enviar leads — nunca ao painel."""
    return "pk_" + secrets.token_urlsafe(18)


def gerar_senha_temporaria() -> str:
    return secrets.token_urlsafe(9)
