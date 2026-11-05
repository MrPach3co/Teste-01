from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.tempo import agora_utc
from app.db.base import Base


class Evento(Base):
    """Interações do visitante que viram métrica: "visualizacao" (abriu o
    imóvel), "comparacao", "planta", "maquete", "espelho"."""

    __tablename__ = "eventos"

    id: Mapped[int] = mapped_column(primary_key=True)
    imobiliaria_id: Mapped[int] = mapped_column(ForeignKey("imobiliarias.id", ondelete="CASCADE"), index=True, nullable=False)
    imovel_id: Mapped[int | None] = mapped_column(ForeignKey("imoveis.id", ondelete="SET NULL"), index=True, nullable=True)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    sessao: Mapped[str | None] = mapped_column(String(64), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc, index=True, nullable=False)
