from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import exigir_dono, obter_imobiliaria_atual
from app.core.security import (
    gerar_chave_publica,
    gerar_hash_senha,
    gerar_senha_temporaria,
)
from app.core.textos_legais import TEXTO_CONSENTIMENTO_CONTA_V1
from app.db.session import obter_db
from app.models import Imobiliaria, Usuario
from app.schemas.conta import (
    CorretorCriado,
    ImobiliariaAtualizacao,
    ImobiliariaPublica,
    NovoCorretor,
    UsuarioPublico,
)
from app.services import limites

router = APIRouter(prefix="/api", tags=["conta"])


@router.patch("/imobiliaria", response_model=ImobiliariaPublica)
def atualizar_imobiliaria(
    dados: ImobiliariaAtualizacao,
    dono: Usuario = Depends(exigir_dono),
    db: Session = Depends(obter_db),
) -> Imobiliaria:
    imobiliaria = dono.imobiliaria
    campos = dados.model_dump(exclude_unset=True)
    if campos.get("nome"):
        imobiliaria.nome = campos["nome"].strip()
    if campos.get("cor_primaria"):
        imobiliaria.cor_primaria = campos["cor_primaria"]
    if "whatsapp" in campos:
        imobiliaria.whatsapp = campos["whatsapp"] or None  # string vazia remove o botão de WhatsApp
    db.commit()
    return imobiliaria


@router.post("/imobiliaria/regenerar-chave", response_model=ImobiliariaPublica)
def regenerar_chave(dono: Usuario = Depends(exigir_dono), db: Session = Depends(obter_db)) -> Imobiliaria:
    """Invalida o snippet antigo — útil se a chave estiver sendo usada num site que não é seu."""
    dono.imobiliaria.chave_publica = gerar_chave_publica()
    db.commit()
    return dono.imobiliaria


@router.get("/equipe", response_model=list[UsuarioPublico])
def listar_equipe(imobiliaria: Imobiliaria = Depends(obter_imobiliaria_atual)) -> list[Usuario]:
    return sorted(imobiliaria.usuarios, key=lambda u: (u.papel != "dono", u.criado_em))


@router.post("/equipe", response_model=CorretorCriado, status_code=status.HTTP_201_CREATED)
def adicionar_corretor(
    dados: NovoCorretor,
    dono: Usuario = Depends(exigir_dono),
    db: Session = Depends(obter_db),
) -> CorretorCriado:
    limites.garantir_vaga_usuario(db, dono.imobiliaria)

    if db.scalar(select(Usuario).where(Usuario.email == dados.email)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Já existe um usuário com este e-mail.")

    senha = gerar_senha_temporaria()
    corretor = Usuario(
        imobiliaria_id=dono.imobiliaria_id,
        nome=dados.nome.strip(),
        email=dados.email,
        senha_hash=gerar_hash_senha(senha),
        papel="corretor",
        # O dono aceita os termos em nome da equipe que ele cadastra.
        consentimento_em=datetime.now(timezone.utc),
        consentimento_texto=TEXTO_CONSENTIMENTO_CONTA_V1,
    )
    db.add(corretor)
    db.commit()
    db.refresh(corretor)
    return CorretorCriado(usuario=corretor, senha_temporaria=senha)


@router.delete("/equipe/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_corretor(usuario_id: int, dono: Usuario = Depends(exigir_dono), db: Session = Depends(obter_db)) -> None:
    alvo = db.get(Usuario, usuario_id)
    if alvo is None or alvo.imobiliaria_id != dono.imobiliaria_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado.")
    if alvo.id == dono.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="O dono não pode remover a si mesmo.")
    db.delete(alvo)
    db.commit()
