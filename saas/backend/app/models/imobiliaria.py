from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.tempo import agora_utc
from app.db.base import Base


class Imobiliaria(Base):
    """O cliente do SaaS (tenant). Todo dado de negócio pertence a uma."""

    __tablename__ = "imobiliarias"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    chave_publica: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    cor_primaria: Mapped[str] = mapped_column(String(7), default="#1F3B2C", nullable=False)
    whatsapp: Mapped[str | None] = mapped_column(String(20), nullable=True)

    plano: Mapped[str] = mapped_column(String(20), default="gratis", nullable=False)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc, nullable=False)

    usuarios: Mapped[list["Usuario"]] = relationship(back_populates="imobiliaria", cascade="all, delete-orphan")
    imoveis: Mapped[list["Imovel"]] = relationship(back_populates="imobiliaria", cascade="all, delete-orphan")
    leads: Mapped[list["Lead"]] = relationship(back_populates="imobiliaria", cascade="all, delete-orphan")
    buscas: Mapped[list["RegistroBusca"]] = relationship(back_populates="imobiliaria", cascade="all, delete-orphan")
