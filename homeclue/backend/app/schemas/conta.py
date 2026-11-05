from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class Cadastro(BaseModel):
    nome_imobiliaria: str = Field(min_length=2, max_length=200)
    nome: str = Field(min_length=2, max_length=200)
    email: EmailStr
    senha: str = Field(min_length=8, max_length=72)
    aceitou_termos: bool


class Login(BaseModel):
    email: EmailStr
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
    criado_em: datetime


class TrocaSenha(BaseModel):
    senha_atual: str
    nova_senha: str = Field(min_length=8, max_length=72)


class NovoCorretor(BaseModel):
    nome: str = Field(min_length=2, max_length=200)
    email: EmailStr


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
    plano: str
    criado_em: datetime


class ImobiliariaAtualizacao(BaseModel):
    nome: str | None = Field(default=None, min_length=2, max_length=200)
    cor_primaria: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    whatsapp: str | None = Field(default=None, max_length=20, pattern=r"^\+?[0-9 ()-]*$")


class Sessao(BaseModel):
    usuario: UsuarioPublico
    imobiliaria: ImobiliariaPublica
