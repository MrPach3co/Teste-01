from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.tempo import agora_utc
from app.db.base import Base


class Imovel(Base):
    __tablename__ = "imoveis"

    id: Mapped[int] = mapped_column(primary_key=True)
    imobiliaria_id: Mapped[int] = mapped_column(ForeignKey("imobiliarias.id", ondelete="CASCADE"), index=True, nullable=False)

    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    tipo: Mapped[str] = mapped_column(String(30), nullable=False)  # ver services.vocabulario.TIPOS
    finalidade: Mapped[str] = mapped_column(String(10), default="venda", nullable=False)  # "venda" | "aluguel"
    bairro: Mapped[str] = mapped_column(String(120), nullable=False)
    cidade: Mapped[str] = mapped_column(String(120), nullable=False)
    preco: Mapped[float] = mapped_column(Float, nullable=False)
    quartos: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    banheiros: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    vagas: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    area_m2: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    descricao: Mapped[str] = mapped_column(Text, default="", nullable=False)
    caracteristicas: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    foto_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    codigo_referencia: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc, nullable=False)

    imobiliaria: Mapped["Imobiliaria"] = relationship(back_populates="imoveis")
