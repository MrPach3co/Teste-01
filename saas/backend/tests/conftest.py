import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./teste.db")
os.environ.setdefault("JWT_SECRET_KEY", "chave-de-teste-nao-usar-em-producao")
os.environ["ANTHROPIC_API_KEY"] = ""  # testes nunca chamam a IA de verdade
os.environ["STRIPE_SECRET_KEY"] = ""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.limiter import limiter
from app.db.base import Base
from app.db.session import obter_db
from app.main import app
from app.services.seed import semear

# StaticPool mantém uma única conexão viva para o banco em memória.
_engine_teste = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
SessionTeste = sessionmaker(autocommit=False, autoflush=False, bind=_engine_teste)


def _obter_db_teste():
    db = SessionTeste()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[obter_db] = _obter_db_teste
limiter.enabled = False


@pytest.fixture(autouse=True)
def banco_limpo():
    Base.metadata.create_all(bind=_engine_teste)
    with SessionTeste() as db:
        semear(db)
    yield
    Base.metadata.drop_all(bind=_engine_teste)


@pytest.fixture
def client():
    return TestClient(app)


def cadastrar(client, email="dono@imob.com", nome_imobiliaria="Imob Teste") -> dict:
    resposta = client.post("/api/auth/cadastro", json={
        "nome_imobiliaria": nome_imobiliaria,
        "nome": "Fulano",
        "email": email,
        "senha": "senha-forte-123",
        "aceitou_termos": True,
    })
    assert resposta.status_code == 201, resposta.text
    return {"Authorization": f"Bearer {resposta.json()['access_token']}"}


IMOVEL_EXEMPLO = {
    "titulo": "Apartamento com piscina",
    "tipo": "apartamento",
    "finalidade": "venda",
    "bairro": "Centro",
    "cidade": "Florianópolis",
    "preco": 800000,
    "quartos": 3,
    "banheiros": 2,
    "vagas": 1,
    "area_m2": 90,
    "caracteristicas": ["piscina", "academia", "nao-existe"],
}
