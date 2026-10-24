from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.tempo import agora_utc
from app.db.base import Base


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(primary_key=True)
    imobiliaria_id: Mapped[int] = mapped_column(ForeignKey("imobiliarias.id", ondelete="CASCADE"), index=True, nullable=False)
    imovel_id: Mapped[int | None] = mapped_column(ForeignKey("imoveis.id", ondelete="SET NULL"), nullable=True)

    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telefone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    mensagem: Mapped[str] = mapped_column(Text, default="", nullable=False)
    busca_texto: Mapped[str | None] = mapped_column(Text, nullable=True)  # o que a pessoa digitou no widget

    status: Mapped[str] = mapped_column(String(20), default="novo", nullable=False)  # ver schemas.lead.STATUS_LEAD
    notas: Mapped[str] = mapped_column(Text, default="", nullable=False)

    consentimento_em: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    consentimento_texto: Mapped[str] = mapped_column(Text, nullable=False)

    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc, index=True, nullable=False)

    imobiliaria: Mapped["Imobiliaria"] = relationship(back_populates="leads")
    imovel: Mapped["Imovel | None"] = relationship()
