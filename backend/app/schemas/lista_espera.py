from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class ListaEsperaEntrada(BaseModel):
    email: EmailStr
    aceitou_termos: bool = Field(
        description="Precisa ser true — é o consentimento explícito exigido pela LGPD."
    )


class ListaEsperaPublico(BaseModel):
    email: EmailStr
    criado_em: datetime

    model_config = {"from_attributes": True}
