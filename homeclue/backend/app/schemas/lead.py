from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.schemas.conta import Email

STATUS_LEAD = ["novo", "em_contato", "visita", "proposta", "fechado", "perdido"]


class LeadEntradaPublica(BaseModel):
    nome: str = Field(min_length=2, max_length=200)
    email: Email | None = None
    telefone: str | None = Field(default=None, max_length=30, pattern=r"^\+?[0-9 ()-]{8,}$")
    mensagem: str = Field(default="", max_length=2000)
    imovel_id: int | None = None
    unidade_id: int | None = None
    busca_id: int | None = None
    sessao: str | None = Field(default=None, max_length=64)
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
    valor_negocio: float | None = Field(default=None, ge=0, lt=1_000_000_000)
    # Leads de WhatsApp chegam sem dados pessoais; o corretor completa depois da conversa.
    nome: str | None = Field(default=None, max_length=200)
    telefone: str | None = Field(default=None, max_length=30)
    email: Email | None = None

    @field_validator("status")
    @classmethod
    def _status_valido(cls, valor: str | None) -> str | None:
        if valor is not None and valor not in STATUS_LEAD:
            raise ValueError(f"Status inválido. Use um destes: {', '.join(STATUS_LEAD)}.")
        return valor

    @field_validator("email", mode="before")
    @classmethod
    def _email_vazio(cls, valor):
        return valor or None


class LeadSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    origem: str
    codigo: str | None
    nome: str | None
    email: str | None
    telefone: str | None
    mensagem: str
    busca_texto: str | None
    resumo_busca: str | None
    match: int | None
    status: str
    notas: str
    valor_negocio: float | None
    fechado_em: datetime | None
    imovel_id: int | None
    imovel_titulo: str | None = None
    unidade_descricao: str | None = None
    corretor_nome: str | None = None
    criado_em: datetime
