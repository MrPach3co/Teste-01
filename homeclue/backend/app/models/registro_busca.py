from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.tempo import agora_utc
from app.db.base import Base


class RegistroBusca(Base):
    """Cada turno de busca no widget. Alimenta as métricas, o relatório de
    demanda, o limite mensal do plano e a medição de custo de IA."""

    __tablename__ = "registros_busca"

    id: Mapped[int] = mapped_column(primary_key=True)
    imobiliaria_id: Mapped[int] = mapped_column(ForeignKey("imobiliarias.id", ondelete="CASCADE"), index=True, nullable=False)
    sessao: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    turno: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    modo: Mapped[str] = mapped_column(String(10), default="texto", nullable=False)  # texto | voz | foto
    texto: Mapped[str] = mapped_column(Text, nullable=False)
    fonte: Mapped[str] = mapped_column(String(10), nullable=False)  # "ia" | "regras"
    criterios: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    resumo: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_resultados: Mapped[int] = mapped_column(Integer, nullable=False)
    melhor_match: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bons_resultados: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # match >= 70%
    resultados_ids: Mapped[list[int]] = mapped_column(JSON, default=list, nullable=False)

    modelo: Mapped[str | None] = mapped_column(String(60), nullable=True)
    tokens_entrada: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tokens_saida: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    custo_usd: Mapped[float] = mapped_column(Float, default=0, nullable=False)

    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc, index=True, nullable=False)

    imobiliaria: Mapped["Imobiliaria"] = relationship(back_populates="buscas")
