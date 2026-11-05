from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.tempo import agora_utc
from app.db.base import Base


class Lead(Base):
    """Um contato gerado pela busca.

    origem "formulario": a pessoa deixou nome e telefone/e-mail no widget.
    origem "whatsapp": a pessoa clicou para falar no WhatsApp. Nesse caso não
    guardamos dado pessoal nenhum — só o imóvel, o resumo da busca e um
    código curto que vai na mensagem, para o corretor achar o lead no painel
    e acompanhar até o fechamento.
    """

    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(primary_key=True)
    imobiliaria_id: Mapped[int] = mapped_column(ForeignKey("imobiliarias.id", ondelete="CASCADE"), index=True, nullable=False)
    imovel_id: Mapped[int | None] = mapped_column(ForeignKey("imoveis.id", ondelete="SET NULL"), nullable=True)
    unidade_id: Mapped[int | None] = mapped_column(ForeignKey("unidades.id", ondelete="SET NULL"), nullable=True)
    busca_id: Mapped[int | None] = mapped_column(ForeignKey("registros_busca.id", ondelete="SET NULL"), nullable=True)
    corretor_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)

    origem: Mapped[str] = mapped_column(String(15), default="formulario", nullable=False)
    codigo: Mapped[str | None] = mapped_column(String(10), index=True, nullable=True)
    sessao: Mapped[str | None] = mapped_column(String(64), nullable=True)

    nome: Mapped[str | None] = mapped_column(String(200), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telefone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    mensagem: Mapped[str] = mapped_column(Text, default="", nullable=False)
    busca_texto: Mapped[str | None] = mapped_column(Text, nullable=True)
    resumo_busca: Mapped[str | None] = mapped_column(Text, nullable=True)
    criterios: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    match: Mapped[int | None] = mapped_column(nullable=True)

    status: Mapped[str] = mapped_column(String(20), default="novo", nullable=False)  # ver schemas.lead.STATUS_LEAD
    notas: Mapped[str] = mapped_column(Text, default="", nullable=False)
    valor_negocio: Mapped[float | None] = mapped_column(Float, nullable=True)
    fechado_em: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    consentimento_em: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    consentimento_texto: Mapped[str | None] = mapped_column(Text, nullable=True)

    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc, index=True, nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc, onupdate=agora_utc, nullable=False)

    imobiliaria: Mapped["Imobiliaria"] = relationship(back_populates="leads")
    imovel: Mapped["Imovel | None"] = relationship()
    unidade: Mapped["Unidade | None"] = relationship()
    corretor: Mapped["Usuario | None"] = relationship()
