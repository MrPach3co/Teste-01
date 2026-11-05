from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BairroInfo(Base):
    """O que a imobiliária sabe sobre um bairro e quer contar ao comprador.
    Tudo aqui aparece atribuído a ela ("Segundo a imobiliária…")."""

    __tablename__ = "bairros_info"
    __table_args__ = (UniqueConstraint("imobiliaria_id", "nome", name="uq_bairro_imobiliaria"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    imobiliaria_id: Mapped[int] = mapped_column(ForeignKey("imobiliarias.id", ondelete="CASCADE"), index=True, nullable=False)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    descricao: Mapped[str] = mapped_column(Text, default="", nullable=False)
    valorizacao: Mapped[str | None] = mapped_column(String(10), nullable=True)  # baixa | media | alta
    valorizacao_justificativa: Mapped[str] = mapped_column(Text, default="", nullable=False)
