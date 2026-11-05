from datetime import datetime

from pydantic import BaseModel, Field


class FeedConfig(BaseModel):
    url: str = Field(min_length=10, max_length=1000, pattern=r"^https?://\S+$")


class FeedStatus(BaseModel):
    url: str | None
    formato: str | None
    status: str | None
    mensagem: str | None
    total: int | None
    ultima_sincronizacao: datetime | None
    proxima_sincronizacao: datetime | None
