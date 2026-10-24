from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.tempo import agora_utc
from app.db.base import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    imobiliaria_id: Mapped[int] = mapped_column(ForeignKey("imobiliarias.id", ondelete="CASCADE"), index=True, nullable=False)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    papel: Mapped[str] = mapped_column(String(20), default="corretor", nullable=False)  # "dono" | "corretor"
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc, nullable=False)

    consentimento_em: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    consentimento_texto: Mapped[str] = mapped_column(Text, nullable=False)

    imobiliaria: Mapped["Imobiliaria"] = relationship(back_populates="usuarios")
