from sqlalchemy import Float, ForeignKey, Integer, String, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

imovel_tag = Table(
    "imovel_tag",
    Base.metadata,
    Column("imovel_id", ForeignKey("imoveis.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)

    imoveis: Mapped[list["Imovel"]] = relationship(secondary=imovel_tag, back_populates="tags")


class Imovel(Base):
    __tablename__ = "imoveis"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    bairro: Mapped[str] = mapped_column(String(200), nullable=False)
    preco: Mapped[float] = mapped_column(Float, nullable=False)
    quartos: Mapped[int] = mapped_column(Integer, nullable=False)
    area_m2: Mapped[float] = mapped_column(Float, nullable=False)

    # Metadados visuais do card (o front monta o gradiente CSS a partir daqui).
    cor_inicio: Mapped[str] = mapped_column(String(7), nullable=False)
    cor_fim: Mapped[str] = mapped_column(String(7), nullable=False)

    descricao_diferencial: Mapped[str] = mapped_column(String(300), nullable=False)

    tags: Mapped[list["Tag"]] = relationship(secondary=imovel_tag, back_populates="imoveis")
