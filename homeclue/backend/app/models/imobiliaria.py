from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
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
    logo_arquivo_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # Opt-in: a IA olha as fotos dos anúncios para achar o que o texto não diz.
    analisar_fotos: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    plano: Mapped[str] = mapped_column(String(20), default="gratis", nullable=False)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Integração por feed XML (o mesmo que a imobiliária manda para os portais).
    feed_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    feed_formato: Mapped[str | None] = mapped_column(String(30), nullable=True)
    feed_status: Mapped[str | None] = mapped_column(String(20), nullable=True)  # ok | erro | pendente
    feed_mensagem: Mapped[str | None] = mapped_column(Text, nullable=True)
    feed_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    feed_ultima_sincronizacao: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    feed_proxima_sincronizacao: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)

    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc, nullable=False)

    usuarios: Mapped[list["Usuario"]] = relationship(back_populates="imobiliaria", cascade="all, delete-orphan")
    imoveis: Mapped[list["Imovel"]] = relationship(back_populates="imobiliaria", cascade="all, delete-orphan")
    leads: Mapped[list["Lead"]] = relationship(back_populates="imobiliaria", cascade="all, delete-orphan")
    buscas: Mapped[list["RegistroBusca"]] = relationship(back_populates="imobiliaria", cascade="all, delete-orphan")
    eventos: Mapped[list["Evento"]] = relationship(cascade="all, delete-orphan")
    arquivos: Mapped[list["Arquivo"]] = relationship(cascade="all, delete-orphan")
    bairros: Mapped[list["BairroInfo"]] = relationship(cascade="all, delete-orphan")
    empreendimentos: Mapped[list["Empreendimento"]] = relationship(cascade="all, delete-orphan")
    tarefas: Mapped[list["Tarefa"]] = relationship(cascade="all, delete-orphan")
