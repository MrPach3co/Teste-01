from pydantic import BaseModel, Field

from app.schemas.imovel import ImovelResultado


class BuscaEntrada(BaseModel):
    texto: str = Field(min_length=1, max_length=500)


class BuscaResposta(BaseModel):
    mensagem: str
    fonte: str  # "ia" (Claude interpretou o pedido) ou "regras" (motor determinístico)
    resultados: list[ImovelResultado]
