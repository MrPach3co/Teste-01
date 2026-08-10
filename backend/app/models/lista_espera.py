from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ListaEspera(Base):
    __tablename__ = "lista_espera"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    consentimento_lgpd_em: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    consentimento_lgpd_texto: Mapped[str] = mapped_column(Text, nullable=False)
