from pydantic import BaseModel, Field


class ConfigWidget(BaseModel):
    nome: str
    cor_primaria: str
    whatsapp: str | None
    mostrar_marca: bool
    exemplos: list[str]


class BuscaEntrada(BaseModel):
    texto: str = Field(min_length=2, max_length=300)


class ImovelResultado(BaseModel):
    id: int
    titulo: str
    tipo: str
    finalidade: str
    bairro: str
    cidade: str
    preco: float
    quartos: int
    banheiros: int
    vagas: int
    area_m2: float
    foto_url: str | None
    descricao: str
    match: int
    motivos: list[str]


class BuscaResposta(BaseModel):
    mensagem: str
    fonte: str
    entendido: list[str]
    resultados: list[ImovelResultado]
