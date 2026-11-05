from pydantic import BaseModel, ConfigDict, Field, field_validator

STATUS_UNIDADE = ("disponivel", "reservada", "vendida")


class Torre(BaseModel):
    nome: str = Field(min_length=1, max_length=60)
    andares: int = Field(ge=1, le=80)
    unidades_por_andar: int = Field(ge=1, le=30)


class EmpreendimentoEntrada(BaseModel):
    nome: str = Field(min_length=2, max_length=200)
    bairro: str = Field(min_length=2, max_length=120)
    cidade: str = Field(min_length=2, max_length=120)
    descricao: str = Field(default="", max_length=6000)
    previsao_entrega: str | None = Field(default=None, max_length=40)
    fotos: list[dict] = Field(default_factory=list, max_length=30)
    torres: list[Torre] = Field(min_length=1, max_length=8)
    ativo: bool = True


class UnidadeEntrada(BaseModel):
    id: int
    status: str | None = None
    preco: float | None = Field(default=None, gt=0, lt=1_000_000_000)
    area_m2: float | None = Field(default=None, gt=0, lt=100_000)
    quartos: int | None = Field(default=None, ge=0, le=20)
    suites: int | None = Field(default=None, ge=0, le=20)
    vagas: int | None = Field(default=None, ge=0, le=20)
    tipologia: str | None = Field(default=None, max_length=120)

    @field_validator("status")
    @classmethod
    def _status_valido(cls, valor):
        if valor is not None and valor not in STATUS_UNIDADE:
            raise ValueError("Status deve ser disponivel, reservada ou vendida.")
        return valor


class UnidadeSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    torre: str
    andar: int
    posicao: int
    codigo: str
    status: str
    preco: float | None
    area_m2: float | None
    quartos: int | None
    suites: int | None
    vagas: int | None
    tipologia: str | None


class EmpreendimentoSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    bairro: str
    cidade: str
    descricao: str
    previsao_entrega: str | None
    fotos: list[dict]
    torres: list[dict]
    ativo: bool
    unidades: list[UnidadeSaida]
