from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Prova de consentimento LGPD: guardamos QUANDO e o TEXTO exato aceito,
    # não só um booleano — isso é o que sustenta a base legal em uma auditoria.
    consentimento_lgpd_em: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    consentimento_lgpd_texto: Mapped[str] = mapped_column(Text, nullable=False)

    buscas_salvas: Mapped[list["BuscaSalva"]] = relationship(
        back_populates="usuario", cascade="all, delete-orphan"
    )
