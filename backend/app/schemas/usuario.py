from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UsuarioCadastro(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=8, max_length=128)
    aceitou_termos: bool = Field(
        description="Precisa ser true — é o consentimento explícito exigido pela LGPD."
    )


class UsuarioLogin(BaseModel):
    email: EmailStr
    senha: str


class UsuarioPublico(BaseModel):
    id: int
    email: EmailStr
    criado_em: datetime

    model_config = {"from_attributes": True}


class TokenAcesso(BaseModel):
    access_token: str
    token_type: str = "bearer"
