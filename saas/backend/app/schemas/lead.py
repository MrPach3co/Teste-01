from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

STATUS_LEAD = ["novo", "em_contato", "visita", "proposta", "fechado", "perdido"]


class LeadEntradaPublica(BaseModel):
    nome: str = Field(min_length=2, max_length=200)
    email: EmailStr | None = None
    telefone: str | None = Field(default=None, max_length=30, pattern=r"^\+?[0-9 ()-]{8,}$")
    mensagem: str = Field(default="", max_length=2000)
    imovel_id: int | None = None
    busca_texto: str | None = Field(default=None, max_length=300)
    aceitou_contato: bool

    @field_validator("email", "telefone", mode="before")
    @classmethod
    def _vazio_vira_none(cls, valor):
        return valor or None

    @model_validator(mode="after")
    def _precisa_de_um_contato(self):
        if not self.email and not self.telefone:
            raise ValueError("Informe um e-mail ou telefone para contato.")
        return self


class LeadAtualizacao(BaseModel):
    status: str | None = None
    notas: str | None = Field(default=None, max_length=5000)

    @field_validator("status")
    @classmethod
    def _status_valido(cls, valor: str | None) -> str | None:
        if valor is not None and valor not in STATUS_LEAD:
            raise ValueError(f"Status inválido. Use um destes: {', '.join(STATUS_LEAD)}.")
        return valor


class LeadSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    email: str | None
    telefone: str | None
    mensagem: str
    busca_texto: str | None
    status: str
    notas: str
    imovel_id: int | None
    imovel_titulo: str | None = None
    criado_em: datetime
