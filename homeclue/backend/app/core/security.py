import hashlib
import hmac
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


def impressao_da_senha(senha_hash: str) -> str:
    """Muda sempre que a senha muda. Vai dentro dos tokens: trocar a senha
    derruba as sessões abertas em outros aparelhos e os links de redefinição."""
    return hmac.new(settings.jwt_secret_key.encode(), senha_hash.encode(), hashlib.sha256).hexdigest()[:16]


def token_de_sessao(usuario) -> str:
    return criar_token_acesso({"sub": str(usuario.id), "fp": impressao_da_senha(usuario.senha_hash)})


_FIM_REDEFINICAO = "redefinir_senha"
VALIDADE_REDEFINICAO = timedelta(hours=1)


def _chave_redefinicao() -> str:
    # Chave própria: um link de redefinição nunca vale como token de sessão.
    return hmac.new(settings.jwt_secret_key.encode(), b"homeclue:redefinir-senha", hashlib.sha256).hexdigest()


def criar_token_redefinicao(usuario) -> str:
    dados = {"sub": str(usuario.id), "fp": impressao_da_senha(usuario.senha_hash), "fim": _FIM_REDEFINICAO,
             "exp": datetime.now(timezone.utc) + VALIDADE_REDEFINICAO}
    return jwt.encode(dados, _chave_redefinicao(), algorithm=settings.jwt_algorithm)


def ler_token_redefinicao(token: str) -> tuple[int, str] | None:
    """(id do usuário, impressão da senha de quando o link foi criado)."""
    try:
        dados = jwt.decode(token, _chave_redefinicao(), algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
    if dados.get("fim") != _FIM_REDEFINICAO or not str(dados.get("sub", "")).isdigit():
        return None
    return int(dados["sub"]), str(dados.get("fp", ""))


def gerar_chave_publica() -> str:
    """Chave do widget. É pública (vai no HTML do site do cliente), então
    só dá acesso a buscar imóveis e enviar leads — nunca ao painel."""
    return "pk_" + secrets.token_urlsafe(18)


def gerar_senha_temporaria() -> str:
    return secrets.token_urlsafe(9)


# Sem 0/O, 1/I/L: o corretor lê o código na conversa do WhatsApp e digita no painel.
_ALFABETO_CODIGO = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"


def gerar_codigo_lead() -> str:
    return "".join(secrets.choice(_ALFABETO_CODIGO) for _ in range(6))
