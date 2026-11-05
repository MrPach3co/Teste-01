from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.dependencies import exigir_dono, obter_imobiliaria_atual
from app.core.security import gerar_chave_publica, gerar_hash_senha, gerar_senha_temporaria
from app.core.tempo import agora_utc
from app.core.textos_legais import TEXTO_CONSENTIMENTO_CONTA_V2
from app.db.session import obter_db
from app.models import Arquivo, Imobiliaria, Usuario
from app.routers.auth import imobiliaria_publica
from app.schemas.conta import (
    CorretorCriado,
    ImobiliariaAtualizacao,
    ImobiliariaPublica,
    NovoCorretor,
    PerfilAtualizacao,
    UsuarioPublico,
)
from app.services import arquivos, limites

router = APIRouter(prefix="/api", tags=["conta"])


@router.patch("/imobiliaria", response_model=ImobiliariaPublica)
def atualizar_imobiliaria(dados: ImobiliariaAtualizacao, dono: Usuario = Depends(exigir_dono),
                          db: Session = Depends(obter_db)) -> ImobiliariaPublica:
    imobiliaria = dono.imobiliaria
    campos = dados.model_dump(exclude_unset=True)
    if campos.get("nome"):
        imobiliaria.nome = campos["nome"].strip()
    if campos.get("cor_primaria"):
        imobiliaria.cor_primaria = campos["cor_primaria"]
    if "whatsapp" in campos:
        imobiliaria.whatsapp = campos["whatsapp"]
    if campos.get("analisar_fotos") is not None:
        imobiliaria.analisar_fotos = campos["analisar_fotos"]
    db.commit()
    return imobiliaria_publica(imobiliaria)


@router.post("/imobiliaria/logo", response_model=ImobiliariaPublica)
async def enviar_logo(arquivo: UploadFile = File(...), dono: Usuario = Depends(exigir_dono),
                      db: Session = Depends(obter_db)) -> ImobiliariaPublica:
    conteudo = await arquivo.read(arquivos.TAMANHO_MAXIMO_ENVIO + 1)
    try:
        novo = arquivos.salvar_imagem(db, dono.imobiliaria_id, conteudo, "logo")
    except arquivos.ImagemInvalida as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro))
    antigo = dono.imobiliaria.logo_arquivo_id
    dono.imobiliaria.logo_arquivo_id = novo.id
    if antigo:
        velho = db.get(Arquivo, antigo)
        if velho is not None:
            db.delete(velho)
    db.commit()
    return imobiliaria_publica(dono.imobiliaria)


@router.delete("/imobiliaria/logo", response_model=ImobiliariaPublica)
def remover_logo(dono: Usuario = Depends(exigir_dono), db: Session = Depends(obter_db)) -> ImobiliariaPublica:
    if dono.imobiliaria.logo_arquivo_id:
        velho = db.get(Arquivo, dono.imobiliaria.logo_arquivo_id)
        dono.imobiliaria.logo_arquivo_id = None
        if velho is not None:
            db.delete(velho)
        db.commit()
    return imobiliaria_publica(dono.imobiliaria)


@router.post("/imobiliaria/regenerar-chave", response_model=ImobiliariaPublica)
def regenerar_chave(dono: Usuario = Depends(exigir_dono), db: Session = Depends(obter_db)) -> ImobiliariaPublica:
    """Invalida o snippet antigo — útil se a chave estiver sendo usada num site que não é seu."""
    dono.imobiliaria.chave_publica = gerar_chave_publica()
    db.commit()
    return imobiliaria_publica(dono.imobiliaria)


@router.get("/equipe", response_model=list[UsuarioPublico])
def listar_equipe(imobiliaria: Imobiliaria = Depends(obter_imobiliaria_atual)) -> list[Usuario]:
    return sorted(imobiliaria.usuarios, key=lambda u: (u.papel != "dono", u.criado_em))


@router.post("/equipe", response_model=CorretorCriado, status_code=status.HTTP_201_CREATED)
def adicionar_corretor(dados: NovoCorretor, dono: Usuario = Depends(exigir_dono),
                       db: Session = Depends(obter_db)) -> CorretorCriado:
    limites.garantir_vaga_usuario(db, dono.imobiliaria)
    if db.scalar(select(Usuario).where(func.lower(Usuario.email) == dados.email)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Já existe um usuário com este e-mail.")
    senha = gerar_senha_temporaria()
    corretor = Usuario(
        imobiliaria_id=dono.imobiliaria_id, nome=dados.nome.strip(), email=dados.email,
        senha_hash=gerar_hash_senha(senha), papel="corretor", whatsapp=dados.whatsapp or None,
        # O dono aceita os termos em nome da equipe que ele cadastra.
        consentimento_em=agora_utc(), consentimento_texto=TEXTO_CONSENTIMENTO_CONTA_V2,
    )
    db.add(corretor)
    db.commit()
    db.refresh(corretor)
    return CorretorCriado(usuario=corretor, senha_temporaria=senha)


def _da_equipe(db: Session, dono: Usuario, usuario_id: int) -> Usuario:
    alvo = db.get(Usuario, usuario_id)
    if alvo is None or alvo.imobiliaria_id != dono.imobiliaria_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado.")
    return alvo


@router.patch("/equipe/{usuario_id}", response_model=UsuarioPublico)
def atualizar_corretor(usuario_id: int, dados: PerfilAtualizacao, dono: Usuario = Depends(exigir_dono),
                       db: Session = Depends(obter_db)) -> Usuario:
    alvo = _da_equipe(db, dono, usuario_id)
    campos = dados.model_dump(exclude_unset=True)
    if campos.get("nome"):
        alvo.nome = campos["nome"].strip()
    if "whatsapp" in campos:
        alvo.whatsapp = campos["whatsapp"] or None
    db.commit()
    return alvo


@router.delete("/equipe/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_corretor(usuario_id: int, dono: Usuario = Depends(exigir_dono), db: Session = Depends(obter_db)) -> None:
    alvo = _da_equipe(db, dono, usuario_id)
    if alvo.id == dono.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="O dono não pode remover a si mesmo.")
    db.delete(alvo)
    db.commit()
