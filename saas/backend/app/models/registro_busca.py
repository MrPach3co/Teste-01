from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.tempo import agora_utc
from app.db.base import Base


class RegistroBusca(Base):
    """Cada busca feita no widget. Alimenta as métricas do painel e o
    limite mensal do plano."""

    __tablename__ = "registros_busca"

    id: Mapped[int] = mapped_column(primary_key=True)
    imobiliaria_id: Mapped[int] = mapped_column(ForeignKey("imobiliarias.id", ondelete="CASCADE"), index=True, nullable=False)
    texto: Mapped[str] = mapped_column(Text, nullable=False)
    fonte: Mapped[str] = mapped_column(String(10), nullable=False)  # "ia" | "regras"
    total_resultados: Mapped[int] = mapped_column(Integer, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc, index=True, nullable=False)

    imobiliaria: Mapped["Imobiliaria"] = relationship(back_populates="buscas")
