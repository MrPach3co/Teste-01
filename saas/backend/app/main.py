from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import obter_settings
from app.core.limiter import limiter
from app.routers import assinatura, auth, conta, imoveis, leads, painel, publico
from app.services import cobranca, ia

settings = obter_settings()

_CHAVE_JWT_PADRAO_INSEGURA = "troque-esta-chave-antes-de-ir-para-producao"
if settings.ambiente == "producao" and settings.jwt_secret_key == _CHAVE_JWT_PADRAO_INSEGURA:
    raise RuntimeError(
        "JWT_SECRET_KEY ainda está com o valor padrão de desenvolvimento. "
        "Defina uma chave forte antes de rodar em produção "
        '(gere uma com: python -c "import secrets; print(secrets.token_hex(32))").'
    )

app = FastAPI(
    title="Kaza Pro — API",
    description="Busca de imóveis com IA para o site da sua imobiliária, com captura e gestão de leads.",
    version="1.0.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# O widget roda no site de cada cliente (qualquer domínio), então a API
# aceita qualquer origem. É seguro porque a autenticação do painel é por
# header Bearer, não por cookie — outro site não consegue "pegar carona"
# na sessão de ninguém.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth.router)
app.include_router(conta.router)
app.include_router(imoveis.router)
app.include_router(leads.router)
app.include_router(painel.router)
app.include_router(assinatura.router)
app.include_router(publico.router)


@app.get("/api/saude")
def saude() -> dict:
    return {"status": "ok", "ia": ia.ia_disponivel(), "pagamentos": cobranca.cobranca_ativa()}


_DIR_FRONTEND = Path(__file__).resolve().parent.parent.parent / "frontend"
if _DIR_FRONTEND.exists():
    app.mount("/", StaticFiles(directory=_DIR_FRONTEND, html=True), name="frontend")
