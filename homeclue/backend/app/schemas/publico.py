from pydantic import BaseModel, Field


class ConfigWidget(BaseModel):
    nome: str
    cor_primaria: str
    logo_url: str | None
    whatsapp: bool
    mostrar_marca: bool
    exemplos: list[str]
    recursos: dict[str, bool]
    lancamentos: int


class BuscaEntrada(BaseModel):
    texto: str = Field(default="", max_length=400)
    sessao: str | None = Field(default=None, max_length=64)
    turno: int = Field(default=1, ge=1, le=200)
    criterios: dict | None = None
    historico: list[str] = Field(default_factory=list, max_length=12)
    modo: str = Field(default="texto", pattern=r"^(texto|voz)$")


class PontoSaida(BaseModel):
    chave: str
    criterio: str
    status: str
    evidencia: str
    fonte: str
    foto: str | None = None


class ImovelResultado(BaseModel):
    id: int
    titulo: str
    tipo: str
    tipo_rotulo: str
    finalidade: str
    preco: float
    preco_aluguel: float | None
    condominio: float | None
    bairro: str
    cidade: str
    quartos: int | None
    suites: int | None
    banheiros: int | None
    vagas: int | None
    area_m2: float | None
    codigo_referencia: str | None
    foto: str | None
    total_fotos: int
    match: int | None
    pontos: list[PontoSaida]
    tem_planta: bool
    tem_maquete: bool
    tem_video: bool


class RankingItem(BaseModel):
    imovel_id: int
    motivo: str


class Ranking(BaseModel):
    id: str
    titulo: str
    explicacao: str
    itens: list[RankingItem]


class BuscaResposta(BaseModel):
    busca_id: int
    mensagem: str
    fonte: str
    criterios: dict
    entendido: list[str]
    resumo: str | None
    avisos: list[str]
    sugestoes: list[str]
    resultados: list[ImovelResultado]
    rankings: list[Ranking]
    descricao_foto: str | None = None


class EventoEntrada(BaseModel):
    tipo: str = Field(pattern=r"^(comparacao|planta|maquete|espelho|video)$")
    imovel_id: int | None = None
    sessao: str | None = Field(default=None, max_length=64)
