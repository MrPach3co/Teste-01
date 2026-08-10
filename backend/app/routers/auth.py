from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.core.dependencies import obter_usuario_atual
from app.core.security import criar_token_acesso, gerar_hash_senha, verificar_senha
from app.core.textos_legais import TEXTO_CONSENTIMENTO_LGPD_V1
from app.db.session import obter_db
from app.models.usuario import Usuario
from app.schemas.usuario import TokenAcesso, UsuarioCadastro, UsuarioLogin, UsuarioPublico

router = APIRouter(prefix="/api/auth", tags=["autenticação"])

limiter = Limiter(key_func=get_remote_address)


@router.post("/cadastro", response_model=UsuarioPublico, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def cadastrar(request: Request, dados: UsuarioCadastro, db: Session = Depends(obter_db)) -> Usuario:
    if not dados.aceitou_termos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="É necessário aceitar os termos de uso e privacidade para criar conta.",
        )

    ja_existe = db.query(Usuario).filter(Usuario.email == dados.email).first()
    if ja_existe:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe uma conta com este e-mail.",
        )

    try:
        senha_hash = gerar_hash_senha(dados.senha)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Senha muito longa (máximo de 72 bytes).",
        )

    usuario = Usuario(
        email=dados.email,
        senha_hash=senha_hash,
        consentimento_lgpd_em=datetime.now(timezone.utc),
        consentimento_lgpd_texto=TEXTO_CONSENTIMENTO_LGPD_V1,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


@router.post("/login", response_model=TokenAcesso)
@limiter.limit("10/minute")
def login(request: Request, dados: UsuarioLogin, db: Session = Depends(obter_db)) -> TokenAcesso:
    usuario = db.query(Usuario).filter(Usuario.email == dados.email).first()

    credenciais_invalidas = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="E-mail ou senha incorretos.",
    )

    if usuario is None or not verificar_senha(dados.senha, usuario.senha_hash):
        raise credenciais_invalidas

    token = criar_token_acesso({"sub": str(usuario.id)})
    return TokenAcesso(access_token=token)


@router.get("/me", response_model=UsuarioPublico)
def eu(usuario_atual: Usuario = Depends(obter_usuario_atual)) -> Usuario:
    return usuario_atual


@router.get("/me/dados")
def exportar_meus_dados(usuario_atual: Usuario = Depends(obter_usuario_atual)) -> dict:
    """Direito de acesso/portabilidade da LGPD: exporta tudo que temos sobre o titular."""
    return {
        "id": usuario_atual.id,
        "email": usuario_atual.email,
        "criado_em": usuario_atual.criado_em.isoformat(),
        "consentimento_lgpd_em": usuario_atual.consentimento_lgpd_em.isoformat(),
        "consentimento_lgpd_texto": usuario_atual.consentimento_lgpd_texto,
        "buscas_salvas": [
            {"texto_busca": b.texto_busca, "criado_em": b.criado_em.isoformat()}
            for b in usuario_atual.buscas_salvas
        ],
    }


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def excluir_minha_conta(
    usuario_atual: Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(obter_db),
) -> None:
    """Direito de eliminação da LGPD: apaga a conta e os dados associados."""
    db.delete(usuario_atual)
    db.commit()
