"""Verificação dos limites do plano contratado."""

from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.planos import obter_plano
from app.core.tempo import agora_utc
from app.models import Imobiliaria, Imovel, RegistroBusca, Usuario


def inicio_do_mes(agora: datetime | None = None) -> datetime:
    agora = agora or agora_utc()
    return agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def contar_buscas_mes(db: Session, imobiliaria_id: int) -> int:
    return db.scalar(
        select(func.count(RegistroBusca.id)).where(
            RegistroBusca.imobiliaria_id == imobiliaria_id,
            RegistroBusca.criado_em >= inicio_do_mes(),
        )
    ) or 0


def contar_imoveis(db: Session, imobiliaria_id: int) -> int:
    return db.scalar(select(func.count(Imovel.id)).where(Imovel.imobiliaria_id == imobiliaria_id)) or 0


def contar_usuarios(db: Session, imobiliaria_id: int) -> int:
    return db.scalar(select(func.count(Usuario.id)).where(Usuario.imobiliaria_id == imobiliaria_id)) or 0


def _bloquear(mensagem: str) -> None:
    raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail=mensagem)


def garantir_vaga_imovel(db: Session, imobiliaria: Imobiliaria, quantidade: int = 1) -> None:
    plano = obter_plano(imobiliaria.plano)
    if plano.limite_imoveis is not None and contar_imoveis(db, imobiliaria.id) + quantidade > plano.limite_imoveis:
        _bloquear(
            f"Seu plano {plano.nome} permite até {plano.limite_imoveis} imóveis. "
            "Faça upgrade para cadastrar mais."
        )


def garantir_vaga_usuario(db: Session, imobiliaria: Imobiliaria) -> None:
    plano = obter_plano(imobiliaria.plano)
    if contar_usuarios(db, imobiliaria.id) >= plano.limite_usuarios:
        _bloquear(
            f"Seu plano {plano.nome} permite até {plano.limite_usuarios} usuário(s). "
            "Faça upgrade para adicionar mais corretores."
        )


def cota_de_buscas_esgotada(db: Session, imobiliaria: Imobiliaria) -> bool:
    plano = obter_plano(imobiliaria.plano)
    return plano.limite_buscas_mes is not None and contar_buscas_mes(db, imobiliaria.id) >= plano.limite_buscas_mes
