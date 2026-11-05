from pydantic import BaseModel, Field


class BairroEntrada(BaseModel):
    descricao: str = Field(default="", max_length=2000)
    valorizacao: str | None = Field(default=None, pattern=r"^(baixa|media|alta)$")
    valorizacao_justificativa: str = Field(default="", max_length=500)


class BairroSaida(BaseModel):
    nome: str
    imoveis: int
    descricao: str
    valorizacao: str | None
    valorizacao_justificativa: str
