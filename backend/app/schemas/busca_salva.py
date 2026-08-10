from datetime import datetime

from pydantic import BaseModel, Field


class BuscaSalvaEntrada(BaseModel):
    texto_busca: str = Field(min_length=1, max_length=500)


class BuscaSalvaPublica(BaseModel):
    id: int
    texto_busca: str
    criado_em: datetime

    model_config = {"from_attributes": True}
