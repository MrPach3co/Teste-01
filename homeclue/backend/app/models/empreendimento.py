from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.tempo import agora_utc
from app.db.base import Base


class Empreendimento(Base):
    """Lançamento com espelho de vendas (torres × andares × unidades)."""

    __tablename__ = "empreendimentos"

    id: Mapped[int] = mapped_column(primary_key=True)
    imobiliaria_id: Mapped[int] = mapped_column(ForeignKey("imobiliarias.id", ondelete="CASCADE"), index=True, nullable=False)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    bairro: Mapped[str] = mapped_column(String(120), nullable=False)
    cidade: Mapped[str] = mapped_column(String(120), nullable=False)
    descricao: Mapped[str] = mapped_column(Text, default="", nullable=False)
    previsao_entrega: Mapped[str | None] = mapped_column(String(40), nullable=True)
    fotos: Mapped[list[dict]] = mapped_column(JSON, default=list, nullable=False)
    torres: Mapped[list[dict]] = mapped_column(JSON, default=list, nullable=False)  # [{"nome", "andares", "unidades_por_andar"}]
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc, nullable=False)

    unidades: Mapped[list["Unidade"]] = relationship(
        back_populates="empreendimento", cascade="all, delete-orphan", order_by="Unidade.id"
    )


class Unidade(Base):
    __tablename__ = "unidades"

    id: Mapped[int] = mapped_column(primary_key=True)
    empreendimento_id: Mapped[int] = mapped_column(ForeignKey("empreendimentos.id", ondelete="CASCADE"), index=True, nullable=False)
    torre: Mapped[str] = mapped_column(String(60), nullable=False)
    andar: Mapped[int] = mapped_column(Integer, nullable=False)
    posicao: Mapped[int] = mapped_column(Integer, nullable=False)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(15), default="disponivel", nullable=False)  # disponivel | reservada | vendida
    preco: Mapped[float | None] = mapped_column(Float, nullable=True)
    area_m2: Mapped[float | None] = mapped_column(Float, nullable=True)
    quartos: Mapped[int | None] = mapped_column(Integer, nullable=True)
    suites: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vagas: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tipologia: Mapped[str | None] = mapped_column(String(120), nullable=True)

    empreendimento: Mapped["Empreendimento"] = relationship(back_populates="unidades")
