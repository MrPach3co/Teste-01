from pydantic import BaseModel


class ImovelResultado(BaseModel):
    id: int
    nome: str
    bairro: str
    preco: float
    quartos: int
    area_m2: float
    cor_inicio: str
    cor_fim: str
    match: int
    motivo: str
