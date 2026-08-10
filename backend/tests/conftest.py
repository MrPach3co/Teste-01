import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./teste.db")
os.environ.setdefault("JWT_SECRET_KEY", "chave-de-teste-nao-usar-em-producao")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import obter_db
from app.main import app
from app.services.seed import semear

# StaticPool mantém uma única conexão viva para o banco em memória — sem
# isso, cada sessão abriria uma conexão nova (e um banco :memory: vazio).
_engine_teste = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_SessionTeste = sessionmaker(autocommit=False, autoflush=False, bind=_engine_teste)


def _obter_db_teste():
    db = _SessionTeste()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[obter_db] = _obter_db_teste


@pytest.fixture(scope="session", autouse=True)
def preparar_banco():
    Base.metadata.create_all(bind=_engine_teste)
    db = _SessionTeste()
    try:
        semear(db)
    finally:
        db.close()
    yield
    Base.metadata.drop_all(bind=_engine_teste)


@pytest.fixture
def client():
    return TestClient(app)
