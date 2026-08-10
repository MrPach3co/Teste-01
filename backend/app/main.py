from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from slowapi import Limiter

from app.core.config import obter_settings
from app.routers import auth, busca, buscas_salvas, imoveis, lista_espera

settings = obter_settings()

_CHAVE_JWT_PADRAO_INSEGURA = "troque-esta-chave-antes-de-ir-para-producao"
if settings.ambiente == "producao" and settings.jwt_secret_key == _CHAVE_JWT_PADRAO_INSEGURA:
    raise RuntimeError(
        "JWT_SECRET_KEY ainda está com o valor padrão de desenvolvimento. "
        "Defina uma chave forte antes de rodar em produção "
        '(gere uma com: python -c "import secrets; print(secrets.token_hex(32))").'
    )

app = FastAPI(
    title="Kaza IA — API",
    description="Backend da busca de imóveis por linguagem natural.",
    version="0.1.0",
)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.lista_cors_origens,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth.router)
app.include_router(busca.router)
app.include_router(buscas_salvas.router)
app.include_router(imoveis.router)
app.include_router(lista_espera.router)


@app.get("/api/saude")
def saude() -> dict:
    return {"status": "ok"}


_DIR_FRONTEND = Path(__file__).resolve().parent.parent.parent / "frontend"
if _DIR_FRONTEND.exists():
    app.mount("/", StaticFiles(directory=_DIR_FRONTEND, html=True), name="frontend")
