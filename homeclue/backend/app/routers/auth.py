from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import eh_admin, obter_usuario_atual
from app.core.limiter import limiter
from app.core.planos import obter_plano
from app.core.security import criar_token_acesso, gerar_chave_publica, gerar_hash_senha, verificar_senha
from app.core.tempo import agora_utc
from app.core.textos_legais import TEXTO_CONSENTIMENTO_CONTA_V2
from app.db.session import obter_db
from app.models import Imobiliaria, Usuario
from app.schemas.conta import (
    Cadastro,
    ImobiliariaPublica,
    Login,
    PerfilAtualizacao,
    PlanoResumo,
    Sessao,
    TokenAcesso,
    TrocaSenha,
    UsuarioPublico,
)
from app.services.arquivos import url_do_arquivo
from app.services.ia import cliente as ia_cliente

router = APIRouter(prefix="/api/auth", tags=["autenticação"])


def imobiliaria_publica(imobiliaria: Imobiliaria) -> ImobiliariaPublica:
    dados = ImobiliariaPublica.model_validate(imobiliaria)
    if imobiliaria.logo_arquivo_id:
        dados.logo_url = url_do_arquivo(imobiliaria.logo_arquivo_id)
    return dados


@router.post("/cadastro", response_model=TokenAcesso, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def cadastrar(request: Request, dados: Cadastro, db: Session = Depends(obter_db)) -> TokenAcesso:
    """Cria a imobiliária (no teste grátis) e o usuário dono, já logado."""
    if not dados.aceitou_termos:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="É necessário aceitar os termos de uso e a política de privacidade.")
    if db.scalar(select(Usuario).where(Usuario.email == dados.email)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Já existe uma conta com este e-mail.")
    try:
        senha_hash = gerar_hash_senha(dados.senha)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Senha muito longa (máximo de 72 bytes).")

    imobiliaria = Imobiliaria(nome=dados.nome_imobiliaria.strip(), chave_publica=gerar_chave_publica())
    db.add(imobiliaria)
    db.flush()
    usuario = Usuario(
        imobiliaria_id=imobiliaria.id, nome=dados.nome.strip(), email=dados.email, senha_hash=senha_hash,
        papel="dono", consentimento_em=agora_utc(), consentimento_texto=TEXTO_CONSENTIMENTO_CONTA_V2,
    )
    db.add(usuario)
    db.commit()
    return TokenAcesso(access_token=criar_token_acesso({"sub": str(usuario.id)}))


@router.post("/login", response_model=TokenAcesso)
@limiter.limit("10/minute")
def login(request: Request, dados: Login, db: Session = Depends(obter_db)) -> TokenAcesso:
    usuario = db.scalar(select(Usuario).where(Usuario.email == dados.email))
    if usuario is None or not verificar_senha(dados.senha, usuario.senha_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="E-mail ou senha incorretos.")
    return TokenAcesso(access_token=criar_token_acesso({"sub": str(usuario.id)}))


@router.get("/sessao", response_model=Sessao)
def sessao(usuario: Usuario = Depends(obter_usuario_atual)) -> Sessao:
    plano = obter_plano(usuario.imobiliaria.plano)
    return Sessao(
        usuario=usuario,
        imobiliaria=imobiliaria_publica(usuario.imobiliaria),
        plano=PlanoResumo(id=plano.id, nome=plano.nome, recursos=sorted(plano.recursos),
                          limite_imoveis=plano.limite_imoveis, limite_buscas_mes=plano.limite_buscas_mes,
                          limite_usuarios=plano.limite_usuarios),
        admin=eh_admin(usuario),
        ia_ativa=ia_cliente.disponivel(),
    )


@router.patch("/perfil", response_model=UsuarioPublico)
def atualizar_perfil(dados: PerfilAtualizacao, usuario: Usuario = Depends(obter_usuario_atual),
                     db: Session = Depends(obter_db)) -> Usuario:
    campos = dados.model_dump(exclude_unset=True)
    if campos.get("nome"):
        usuario.nome = campos["nome"].strip()
    if "whatsapp" in campos:
        usuario.whatsapp = campos["whatsapp"] or None
    db.commit()
    return usuario


@router.post("/trocar-senha", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("5/minute")
def trocar_senha(request: Request, dados: TrocaSenha, usuario: Usuario = Depends(obter_usuario_atual),
                 db: Session = Depends(obter_db)) -> None:
    if not verificar_senha(dados.senha_atual, usuario.senha_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Senha atual incorreta.")
    usuario.senha_hash = gerar_hash_senha(dados.nova_senha)
    db.commit()


@router.get("/meus-dados")
def exportar_meus_dados(usuario: Usuario = Depends(obter_usuario_atual)) -> dict:
    """Direito de acesso/portabilidade (LGPD) do usuário do painel."""
    return {
        "id": usuario.id, "nome": usuario.nome, "email": usuario.email, "papel": usuario.papel,
        "whatsapp": usuario.whatsapp, "imobiliaria": usuario.imobiliaria.nome,
        "criado_em": usuario.criado_em.isoformat(), "consentimento_em": usuario.consentimento_em.isoformat(),
        "consentimento_texto": usuario.consentimento_texto,
    }


@router.delete("/minha-conta", status_code=status.HTTP_204_NO_CONTENT)
def excluir_minha_conta(usuario: Usuario = Depends(obter_usuario_atual), db: Session = Depends(obter_db)) -> None:
    """Direito de eliminação (LGPD). Se for o dono, apaga a imobiliária
    inteira — imóveis, leads, equipe e arquivos — porque a conta deixa de existir."""
    if usuario.papel == "dono":
        db.delete(usuario.imobiliaria)
    else:
        db.delete(usuario)
    db.commit()
