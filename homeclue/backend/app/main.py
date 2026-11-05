import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
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

# Respostas comprimidas: a lista de imóveis e os scripts ficam ~5x menores.
app.add_middleware(GZipMiddleware, minimum_size=1024)

# Política de segurança das páginas. Scripts só do próprio domínio (nenhum
# script embutido no HTML); fotos de qualquer https (vêm do feed de cada
# imobiliária); vídeos só do YouTube e do Vimeo.
_CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com; img-src 'self' data: blob: https:; media-src 'self' https:; "
    "connect-src 'self'; frame-src 'self' https://www.youtube-nocookie.com https://player.vimeo.com; "
    "object-src 'none'; base-uri 'self'; form-action 'self'"
)
# Só a busca (embed.html) pode ser embutida em outro site — é o widget no site
# da imobiliária. Painel, login e o resto não (proteção contra clickjacking).
_EMBUTIVEIS = {"/embed.html"}


@app.middleware("http")
async def cabecalhos_de_seguranca(request: Request, call_next):
    resposta = await call_next(request)
    cabecalhos = resposta.headers
    cabecalhos.setdefault("X-Content-Type-Options", "nosniff")
    cabecalhos.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    if settings.ambiente == "producao":
        cabecalhos.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    if cabecalhos.get("content-type", "").startswith("text/html"):
        if request.url.path in _EMBUTIVEIS:
            cabecalhos.setdefault("Content-Security-Policy", _CSP)
        else:
            cabecalhos.setdefault("Content-Security-Policy", _CSP + "; frame-ancestors 'none'")
            cabecalhos.setdefault("X-Frame-Options", "DENY")
    return resposta


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
