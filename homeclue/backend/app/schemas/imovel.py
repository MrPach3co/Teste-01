from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.services.vocabulario import TIPOS, caracteristicas_validas


class ImovelBase(BaseModel):
    titulo: str = Field(min_length=3, max_length=200)
    tipo: str
    finalidade: str = "venda"
    bairro: str = Field(min_length=2, max_length=120)
    cidade: str = Field(min_length=2, max_length=120)
    preco: float = Field(gt=0, lt=1_000_000_000)
    quartos: int = Field(default=0, ge=0, le=50)
    banheiros: int = Field(default=0, ge=0, le=50)
    vagas: int = Field(default=0, ge=0, le=50)
    area_m2: float = Field(default=0, ge=0, lt=1_000_000)
    descricao: str = Field(default="", max_length=5000)
    caracteristicas: list[str] = Field(default_factory=list)
    foto_url: str | None = Field(default=None, max_length=500, pattern=r"^https://")
    codigo_referencia: str | None = Field(default=None, max_length=50)
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
        if valor not in ("venda", "aluguel"):
            raise ValueError("Finalidade deve ser 'venda' ou 'aluguel'.")
        return valor

    @field_validator("caracteristicas")
    @classmethod
    def _filtrar_caracteristicas(cls, valor: list[str]) -> list[str]:
        return caracteristicas_validas(valor)

    @field_validator("foto_url", "codigo_referencia", mode="before")
    @classmethod
    def _vazio_vira_none(cls, valor):
        return valor or None


class ImovelEntrada(ImovelBase):
    pass


class ImovelSaida(ImovelBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    criado_em: datetime
    total_leads: int = 0


class PedidoDescricao(BaseModel):
    titulo: str = Field(default="", max_length=200)
    tipo: str = "apartamento"
    finalidade: str = "venda"
    bairro: str = Field(default="", max_length=120)
    cidade: str = Field(default="", max_length=120)
    preco: float = 0
    quartos: int = 0
    banheiros: int = 0
    vagas: int = 0
    area_m2: float = 0
    caracteristicas: list[str] = Field(default_factory=list)
    observacoes: str = Field(default="", max_length=1000)


class DescricaoGerada(BaseModel):
    descricao: str
    fonte: str


class ResultadoImportacao(BaseModel):
    importados: int
    erros: list[str]
