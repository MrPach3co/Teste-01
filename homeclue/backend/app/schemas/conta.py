from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field, field_validator

_PADRAO_TELEFONE = r"^\+?[0-9 ()-]*$"

# E-mail digitado vira minúsculas: "Ana@Imob.com" e "ana@imob.com" são a mesma conta.
Email = Annotated[EmailStr, AfterValidator(lambda valor: valor.strip().lower())]


class Cadastro(BaseModel):
    nome_imobiliaria: str = Field(min_length=2, max_length=200)
    nome: str = Field(min_length=2, max_length=200)
    email: Email
    senha: str = Field(min_length=8, max_length=72)
    aceitou_termos: bool


class Login(BaseModel):
    email: Email
    senha: str


class TokenAcesso(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UsuarioPublico(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    email: EmailStr
    papel: str
    whatsapp: str | None = None
    criado_em: datetime


class PerfilAtualizacao(BaseModel):
    nome: str | None = Field(default=None, min_length=2, max_length=200)
    whatsapp: str | None = Field(default=None, max_length=20, pattern=_PADRAO_TELEFONE)


class PedidoRedefinicao(BaseModel):
    email: Email


class Redefinicao(BaseModel):
    token: str = Field(min_length=10, max_length=2000)
    nova_senha: str = Field(min_length=8, max_length=72)


class TrocaSenha(BaseModel):
    senha_atual: str
    nova_senha: str = Field(min_length=8, max_length=72)


class NovoCorretor(BaseModel):
    nome: str = Field(min_length=2, max_length=200)
    email: Email
    whatsapp: str | None = Field(default=None, max_length=20, pattern=_PADRAO_TELEFONE)


class CorretorCriado(BaseModel):
    usuario: UsuarioPublico
    senha_temporaria: str


class ImobiliariaPublica(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    chave_publica: str
    cor_primaria: str
    whatsapp: str | None
    logo_url: str | None = None
    analisar_fotos: bool
    plano: str
    criado_em: datetime


class ImobiliariaAtualizacao(BaseModel):
    nome: str | None = Field(default=None, min_length=2, max_length=200)
    cor_primaria: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    whatsapp: str | None = Field(default=None, max_length=20, pattern=_PADRAO_TELEFONE)
    analisar_fotos: bool | None = None

    @field_validator("whatsapp")
    @classmethod
    def _vazio_vira_none(cls, valor):
        return valor or None


class PlanoResumo(BaseModel):
    id: str
    nome: str
    recursos: list[str]
    limite_imoveis: int | None
    limite_buscas_mes: int | None
    limite_usuarios: int


class Sessao(BaseModel):
    usuario: UsuarioPublico
    imobiliaria: ImobiliariaPublica
    plano: PlanoResumo
    admin: bool
    ia_ativa: bool
