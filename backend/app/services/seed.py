"""Popula o banco com os imóveis fictícios do protótipo (Rio de Janeiro).

Idempotente: pode rodar várias vezes sem duplicar dados.
Uso: python -m app.services.seed
"""

from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.imovel import Imovel, Tag

IMOVEIS_SEED = [
    {
        "nome": "Casa em condomínio na Barra",
        "bairro": "Barra da Tijuca, Rio de Janeiro",
        "preco": 1_850_000,
        "quartos": 4,
        "area_m2": 320,
        "cor_inicio": "#1F3B2C",
        "cor_fim": "#2E5741",
        "descricao_diferencial": "Melhor custo-benefício por m² entre as casas da Barra",
        "tags": ["moderna", "perto-do-mar", "escritorio", "piscina", "condominio-fechado", "pet-friendly"],
    },
    {
        "nome": "Casa nova frente ao mar",
        "bairro": "Recreio dos Bandeirantes, Rio de Janeiro",
        "preco": 2_450_000,
        "quartos": 4,
        "area_m2": 380,
        "cor_inicio": "#9C4A26",
        "cor_fim": "#C06A3F",
        "descricao_diferencial": "Maior valorização histórica da região nos últimos 5 anos",
        "tags": ["perto-do-mar", "vista-mar", "escritorio", "moderna", "investimento"],
    },
    {
        "nome": "Apartamento reformado com vista mar",
        "bairro": "Ipanema, Rio de Janeiro",
        "preco": 3_200_000,
        "quartos": 3,
        "area_m2": 140,
        "cor_inicio": "#1B1A17",
        "cor_fim": "#4A473F",
        "descricao_diferencial": "Localização mais valorizada do Rio de Janeiro",
        "tags": ["vista-mar", "reformado", "perto-do-mar", "investimento"],
    },
    {
        "nome": "Apartamento compacto reformado",
        "bairro": "Botafogo, Rio de Janeiro",
        "preco": 890_000,
        "quartos": 2,
        "area_m2": 78,
        "cor_inicio": "#2E5741",
        "cor_fim": "#4C7C63",
        "descricao_diferencial": "Melhor custo-benefício para quem busca praticidade",
        "tags": ["reformado", "escritorio", "investimento"],
    },
    {
        "nome": "Cobertura duplex com piscina",
        "bairro": "Leblon, Rio de Janeiro",
        "preco": 5_800_000,
        "quartos": 4,
        "area_m2": 310,
        "cor_inicio": "#1F3B2C",
        "cor_fim": "#9C4A26",
        "descricao_diferencial": "Padrão de acabamento mais alto entre as opções",
        "tags": ["cobertura", "piscina", "vista-mar", "escritorio", "perto-do-mar"],
    },
]


def obter_ou_criar_tag(db: Session, slug: str) -> Tag:
    tag = db.query(Tag).filter(Tag.slug == slug).first()
    if tag is None:
        tag = Tag(slug=slug)
        db.add(tag)
        db.flush()
    return tag


def semear(db: Session) -> None:
    for dados in IMOVEIS_SEED:
        existente = db.query(Imovel).filter(Imovel.nome == dados["nome"]).first()
        if existente:
            continue

        tags = [obter_ou_criar_tag(db, slug) for slug in dados["tags"]]
        imovel = Imovel(
            nome=dados["nome"],
            bairro=dados["bairro"],
            preco=dados["preco"],
            quartos=dados["quartos"],
            area_m2=dados["area_m2"],
            cor_inicio=dados["cor_inicio"],
            cor_fim=dados["cor_fim"],
            descricao_diferencial=dados["descricao_diferencial"],
            tags=tags,
        )
        db.add(imovel)

    db.commit()


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    sessao = SessionLocal()
    try:
        semear(sessao)
        print(f"Seed concluído: {sessao.query(Imovel).count()} imóveis no banco.")
    finally:
        sessao.close()
