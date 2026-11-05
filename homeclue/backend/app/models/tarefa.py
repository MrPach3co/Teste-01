from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.tempo import agora_utc
from app.db.base import Base


class Tarefa(Base):
    """Fila de tarefas em segundo plano guardada no próprio banco.

    Vários processos podem rodar o executor ao mesmo tempo: cada tarefa é
    "travada" com um UPDATE condicional antes de rodar, então ninguém
    executa a mesma tarefa duas vezes.
    """

    __tablename__ = "tarefas"
    __table_args__ = (Index("ix_tarefas_fila", "status", "executar_em"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    tipo: Mapped[str] = mapped_column(String(40), nullable=False)
    imobiliaria_id: Mapped[int | None] = mapped_column(ForeignKey("imobiliarias.id", ondelete="CASCADE"), nullable=True)
    imovel_id: Mapped[int | None] = mapped_column(ForeignKey("imoveis.id", ondelete="CASCADE"), nullable=True)
    referencia: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(15), default="pendente", nullable=False)  # pendente | executando | concluida | erro
    tentativas: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    executar_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc, nullable=False)
    travado_ate: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    erro: Mapped[str | None] = mapped_column(Text, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc, nullable=False)
    concluido_em: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
