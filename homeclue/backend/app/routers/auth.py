from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.dependencies import eh_admin, obter_usuario_atual
from app.core.limiter import limiter
from app.core.planos import obter_plano
from app.core.security import (
    gerar_chave_publica,
    gerar_hash_senha,
    impressao_da_senha,
    ler_token_redefinicao,
    token_de_sessao,
    verificar_senha,
)
from app.core.tempo import agora_utc
from app.core.textos_legais import TEXTO_CONSENTIMENTO_CONTA_V2
from app.db.session import obter_db
from app.models import Imobiliaria, Tarefa, Usuario
from app.schemas.conta import (
    Cadastro,
    ImobiliariaPublica,
    Login,
    PedidoRedefinicao,
    PerfilAtualizacao,
    PlanoResumo,
    Redefinicao,
    Sessao,
    TokenAcesso,
    TrocaSenha,
    UsuarioPublico,
)
from app.services import cobranca
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
    if db.scalar(select(Usuario).where(func.lower(Usuario.email) == dados.email)):
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
    return TokenAcesso(access_token=token_de_sessao(usuario))


@router.post("/login", response_model=TokenAcesso)
@limiter.limit("10/minute")
def login(request: Request, dados: Login, db: Session = Depends(obter_db)) -> TokenAcesso:
    usuario = db.scalar(select(Usuario).where(func.lower(Usuario.email) == dados.email))
    if usuario is None or not verificar_senha(dados.senha, usuario.senha_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="E-mail ou senha incorretos.")
    return TokenAcesso(access_token=token_de_sessao(usuario))


_RESPOSTA_PEDIDO = {"mensagem": "Se houver uma conta com este e-mail, enviamos um link para criar uma nova senha. "
                                "Ele vale por 1 hora."}


@router.post("/esqueci-senha", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("3/minute")
def esqueci_senha(request: Request, dados: PedidoRedefinicao, db: Session = Depends(obter_db)) -> dict:
    """Sempre responde igual (não revela quais e-mails têm conta) e manda o
    e-mail pela fila, então o tempo de resposta também não revela nada."""
    usuario = db.scalar(select(Usuario).where(func.lower(Usuario.email) == dados.email))
    if usuario is not None:
        recente = db.scalar(select(Tarefa.id).where(
            Tarefa.tipo == "email_redefinir_senha", Tarefa.referencia == str(usuario.id),
            Tarefa.criado_em >= agora_utc() - timedelta(minutes=2),
        ).limit(1))
        if recente is None:  # no máximo um e-mail a cada 2 minutos por conta
            db.add(Tarefa(tipo="email_redefinir_senha", referencia=str(usuario.id), executar_em=agora_utc()))
            db.commit()
    return _RESPOSTA_PEDIDO


@router.post("/redefinir-senha", response_model=TokenAcesso)
@limiter.limit("10/minute")
def redefinir_senha(request: Request, dados: Redefinicao, db: Session = Depends(obter_db)) -> TokenAcesso:
    lido = ler_token_redefinicao(dados.token)
    usuario = db.get(Usuario, lido[0]) if lido else None
    # O link é de uso único: depois que a senha muda, a impressão muda e ele para de valer.
    if usuario is None or lido[1] != impressao_da_senha(usuario.senha_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Este link é inválido ou já expirou. Peça um novo em “Esqueci minha senha”.")
    usuario.senha_hash = gerar_hash_senha(dados.nova_senha)
    db.commit()
    return TokenAcesso(access_token=token_de_sessao(usuario))


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


@router.post("/trocar-senha", response_model=TokenAcesso)
@limiter.limit("5/minute")
def trocar_senha(request: Request, dados: TrocaSenha, usuario: Usuario = Depends(obter_usuario_atual),
                 db: Session = Depends(obter_db)) -> TokenAcesso:
    """Devolve um token novo: este aparelho continua logado, os outros saem."""
    if not verificar_senha(dados.senha_atual, usuario.senha_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Senha atual incorreta.")
    usuario.senha_hash = gerar_hash_senha(dados.nova_senha)
    db.commit()
    return TokenAcesso(access_token=token_de_sessao(usuario))


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
    inteira — imóveis, leads, equipe e arquivos — porque a conta deixa de existir.
    Antes, cancela a assinatura: conta que não existe não pode continuar sendo cobrada."""
    if usuario.papel == "dono":
        try:
            cobranca.cancelar_assinatura(usuario.imobiliaria)
        except cobranca.FalhaAoCancelar:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Não conseguimos cancelar sua assinatura agora, então a conta não foi excluída. "
                       "Tente de novo em alguns minutos.",
            )
        db.delete(usuario.imobiliaria)
    else:
        db.delete(usuario)
    db.commit()
