from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.tempo import agora_utc
from app.db.base import Base


class Arquivo(Base):
    """Imagens enviadas pela imobiliária (logo, planta, fotos de cômodos).

    Ficam no próprio banco para o produto não depender de um storage externo
    no começo. Toda imagem é reprocessada (redimensionada, sem metadados)
    antes de entrar aqui — ver services.arquivos.
    """

    __tablename__ = "arquivos"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    imobiliaria_id: Mapped[int] = mapped_column(ForeignKey("imobiliarias.id", ondelete="CASCADE"), index=True, nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)  # logo | planta | foto
    content_type: Mapped[str] = mapped_column(String(40), nullable=False)
    dados: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    tamanho: Mapped[int] = mapped_column(Integer, nullable=False)
    largura: Mapped[int] = mapped_column(Integer, nullable=False)
    altura: Mapped[int] = mapped_column(Integer, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=agora_utc, nullable=False)
