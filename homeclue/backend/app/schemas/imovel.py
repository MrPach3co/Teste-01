from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.services.vocabulario import TIPOS, TIPOS_COMODO, caracteristicas_validas

_URL_OU_ARQUIVO = r"^(https://\S+|/api/arquivos/[0-9a-f]{32})$"


class Foto(BaseModel):
    url: str = Field(max_length=500, pattern=_URL_OU_ARQUIVO)
    legenda: str = Field(default="", max_length=120)


class ImovelEntrada(BaseModel):
    titulo: str = Field(min_length=3, max_length=200)
    tipo: str
    finalidade: str = "venda"
    preco: float = Field(gt=0, lt=1_000_000_000)
    preco_aluguel: float | None = Field(default=None, gt=0, lt=10_000_000)
    condominio: float | None = Field(default=None, ge=0, lt=1_000_000)
    iptu: float | None = Field(default=None, ge=0, lt=10_000_000)
    bairro: str = Field(min_length=2, max_length=120)
    cidade: str = Field(min_length=2, max_length=120)
    uf: str | None = Field(default=None, pattern=r"^[A-Za-z]{2}$")
    endereco: str | None = Field(default=None, max_length=300)
    mostrar_endereco: bool = False
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    quartos: int | None = Field(default=None, ge=0, le=50)
    suites: int | None = Field(default=None, ge=0, le=50)
    banheiros: int | None = Field(default=None, ge=0, le=50)
    vagas: int | None = Field(default=None, ge=0, le=50)
    area_m2: float | None = Field(default=None, gt=0, lt=1_000_000)
    area_terreno: float | None = Field(default=None, gt=0, lt=100_000_000)
    descricao: str = Field(default="", max_length=8000)
    caracteristicas: list[str] = Field(default_factory=list)
    comodidades: list[str] = Field(default_factory=list, max_length=40)
    fotos: list[Foto] = Field(default_factory=list, max_length=40)
    video_url: str | None = Field(default=None, max_length=500, pattern=r"^https://\S+$")
    video_drone_url: str | None = Field(default=None, max_length=500, pattern=r"^https://\S+$")
    url_anuncio: str | None = Field(default=None, max_length=500, pattern=r"^https?://\S+$")
    codigo_referencia: str | None = Field(default=None, max_length=80)
    corretor_id: int | None = None
    ativo: bool = True

    @field_validator("tipo")
    @classmethod
    def _tipo_valido(cls, valor: str) -> str:
        if valor not in TIPOS:
            raise ValueError(f"Tipo inválido. Use um destes: {', '.join(TIPOS)}.")
        return valor

    @field_validator("finalidade")
    @classmethod
    def _finalidade_valida(cls, valor: str) -> str:
        if valor not in ("venda", "aluguel", "venda_aluguel"):
            raise ValueError("Finalidade deve ser 'venda', 'aluguel' ou 'venda_aluguel'.")
        return valor

    @field_validator("caracteristicas")
    @classmethod
    def _filtrar_caracteristicas(cls, valor: list[str]) -> list[str]:
        return caracteristicas_validas(valor)

    @field_validator("comodidades")
    @classmethod
    def _limpar_comodidades(cls, valor: list[str]) -> list[str]:
        return [" ".join(v.split())[:80] for v in valor if v and v.strip()]

    @field_validator("video_url", "video_drone_url", "url_anuncio", "codigo_referencia", "endereco", "uf", mode="before")
    @classmethod
    def _vazio_vira_none(cls, valor):
        return valor or None

    @model_validator(mode="after")
    def _aluguel_quando_ambos(self):
        if self.finalidade == "venda_aluguel" and not self.preco_aluguel:
            raise ValueError("Informe o valor do aluguel quando o imóvel é para venda e aluguel.")
        if self.finalidade != "venda_aluguel":
            self.preco_aluguel = None
        return self


# Campos que a imobiliária pode mudar no painel num imóvel que vem do feed
# (o resto o feed sobrescreve na próxima sincronização).
CAMPOS_EDITAVEIS_EM_IMOVEL_DO_FEED = {"ativo", "corretor_id", "video_drone_url"}


class ImovelSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    origem: str
    titulo: str
    tipo: str
    finalidade: str
    preco: float
    preco_aluguel: float | None
    condominio: float | None
    iptu: float | None
    bairro: str
    cidade: str
    uf: str | None
    endereco: str | None
    mostrar_endereco: bool
    latitude: float | None
    longitude: float | None
    coordenadas_aproximadas: bool
    quartos: int | None
    suites: int | None
    banheiros: int | None
    vagas: int | None
    area_m2: float | None
    area_terreno: float | None
    descricao: str
    caracteristicas: list[str]
    comodidades: list[str]
    fotos: list[dict]
    video_url: str | None
    video_drone_url: str | None
    url_anuncio: str | None
    codigo_referencia: str | None
    corretor_id: int | None
    planta: dict | None
    maquete_liberada: bool
    contexto: dict | None
    analise_fotos: dict | None
    ativo: bool
    removido_do_feed_em: datetime | None
    criado_em: datetime
    atualizado_em: datetime
    total_leads: int = 0
    visualizacoes: int = 0


class Comodo(BaseModel):
    id: str = Field(min_length=1, max_length=40)
    tipo: str
    nome: str = Field(default="", max_length=60)
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    w: float = Field(gt=0, le=1)
    h: float = Field(gt=0, le=1)
    area_m2: float | None = Field(default=None, gt=0, lt=10_000)
    notas: str = Field(default="", max_length=300)
    fotos: list[str] = Field(default_factory=list, max_length=12)

    @field_validator("tipo")
    @classmethod
    def _tipo_valido(cls, valor: str) -> str:
        if valor not in TIPOS_COMODO:
            raise ValueError("Tipo de cômodo inválido.")
        return valor

    @model_validator(mode="after")
    def _dentro_da_planta(self):
        if self.x + self.w > 1.0001 or self.y + self.h > 1.0001:
            raise ValueError("O cômodo precisa ficar dentro da planta.")
        return self


class PlantaEntrada(BaseModel):
    imagem: str | None = Field(default=None, max_length=500, pattern=_URL_OU_ARQUIVO)
    comodos: list[Comodo] = Field(default_factory=list, max_length=60)


class PedidoDescricao(BaseModel):
    titulo: str = Field(default="", max_length=200)
    tipo: str = "apartamento"
    finalidade: str = "venda"
    bairro: str = Field(default="", max_length=120)
    cidade: str = Field(default="", max_length=120)
    preco: float | None = None
    quartos: int | None = None
    suites: int | None = None
    banheiros: int | None = None
    vagas: int | None = None
    area_m2: float | None = None
    caracteristicas: list[str] = Field(default_factory=list)
    observacoes: str = Field(default="", max_length=1000)


class DescricaoGerada(BaseModel):
    descricao: str
    fonte: str


class ResultadoImportacao(BaseModel):
    importados: int
    erros: list[str]
