from datetime import datetime

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Cache(Base):
    """Cache genérico com validade: geocodificação, pontos de interesse do
    OpenStreetMap e interpretações de busca repetidas (economiza IA)."""

    __tablename__ = "cache"

    chave: Mapped[str] = mapped_column(String(64), primary_key=True)
    valor: Mapped[dict] = mapped_column(JSON, nullable=False)
    expira_em: Mapped[datetime] = mapped_column(DateTime, index=True, nullable=False)
