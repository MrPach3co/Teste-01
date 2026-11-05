import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import obter_settings
from app.core.limiter import limiter
from app.db.session import SessionLocal
from app.routers import (
    admin,
    arquivos,
    assinatura,
    auth,
    bairros,
    conta,
    feed,
    imoveis,
    lancamentos,
    leads,
    painel,
    publico,
)
from app.services import cobranca, tarefas
from app.services.ia import cliente as ia_cliente

settings = obter_settings()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

_CHAVE_JWT_PADRAO_INSEGURA = "troque-esta-chave-antes-de-ir-para-producao"
if settings.ambiente == "producao" and settings.jwt_secret_key == _CHAVE_JWT_PADRAO_INSEGURA:
    raise RuntimeError(
        "JWT_SECRET_KEY ainda está com o valor padrão de desenvolvimento. "
        "Defina uma chave forte antes de rodar em produção "
        '(gere uma com: python -c "import secrets; print(secrets.token_hex(32))").'
    )


@asynccontextmanager
async def ciclo_de_vida(_app: FastAPI):
    executor = None
    if settings.tarefas_em_segundo_plano:
        executor = tarefas.Executor(SessionLocal)
        executor.iniciar()
    yield
    if executor is not None:
        executor.parar()


app = FastAPI(
    title="Homeclue — API",
    description="Busca com IA no site da imobiliária: match explicado, leads no WhatsApp e dados de demanda.",
    version="2.0.0",
    lifespan=ciclo_de_vida,
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

for modulo in (auth, conta, imoveis, feed, leads, painel, bairros, lancamentos, assinatura, publico, arquivos, admin):
    app.include_router(modulo.router)


@app.get("/api/saude")
def saude() -> dict:
    return {
        "status": "ok",
        "ia": ia_cliente.disponivel(),
        "modelo": ia_cliente.modelo() if ia_cliente.disponivel() else None,
        "pagamentos": cobranca.cobranca_ativa(),
    }


_DIR_FRONTEND = Path(__file__).resolve().parent.parent.parent / "frontend"
if _DIR_FRONTEND.exists():
    app.mount("/", StaticFiles(directory=_DIR_FRONTEND, html=True), name="frontend")
