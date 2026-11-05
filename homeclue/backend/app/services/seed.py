"""Garante a imobiliária de demonstração usada na landing page.

Idempotente: pode rodar a cada deploy. O dono da conta demo recebe uma
senha aleatória descartada, então ninguém consegue entrar no painel dela —
ela existe só para alimentar o widget de exemplo do site.
"""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import gerar_hash_senha, gerar_senha_temporaria
from app.core.textos_legais import TEXTO_CONSENTIMENTO_CONTA_V1
from app.db.session import SessionLocal
from app.models import Imobiliaria, Imovel, Usuario

CHAVE_DEMO = "pk_demo"

_IMOVEIS_DEMO = [
    dict(titulo="Casa moderna a duas quadras da praia", tipo="casa", finalidade="venda", bairro="Recreio",
         preco=1_850_000, quartos=4, banheiros=4, vagas=3, area_m2=320,
         caracteristicas=["piscina", "churrasqueira", "perto-do-mar", "suite", "escritorio", "jardim"]),
    dict(titulo="Cobertura duplex com vista definitiva para o mar", tipo="cobertura", finalidade="venda",
         bairro="Barra da Tijuca", preco=3_200_000, quartos=4, banheiros=5, vagas=3, area_m2=380,
         caracteristicas=["piscina", "vista-mar", "varanda-gourmet", "portaria-24h", "suite", "elevador"]),
    dict(titulo="Apartamento reformado perto do metrô", tipo="apartamento", finalidade="venda", bairro="Botafogo",
         preco=980_000, quartos=2, banheiros=2, vagas=1, area_m2=82,
         caracteristicas=["reformado", "perto-metro", "escritorio", "portaria-24h", "aceita-financiamento"]),
    dict(titulo="Três quartos com varanda em condomínio clube", tipo="apartamento", finalidade="venda",
         bairro="Barra da Tijuca", preco=1_250_000, quartos=3, banheiros=2, vagas=2, area_m2=110,
         caracteristicas=["condominio-fechado", "piscina", "academia", "playground", "varanda", "pet-friendly"]),
    dict(titulo="Studio mobiliado a uma quadra da praia", tipo="studio", finalidade="aluguel", bairro="Copacabana",
         preco=3_400, quartos=1, banheiros=1, vagas=0, area_m2=32,
         caracteristicas=["mobiliado", "perto-do-mar", "perto-metro", "portaria-24h"]),
    dict(titulo="Dois quartos com suíte e lazer completo", tipo="apartamento", finalidade="aluguel",
         bairro="Tijuca", preco=3_900, quartos=2, banheiros=2, vagas=1, area_m2=75,
         caracteristicas=["suite", "piscina", "academia", "pet-friendly", "elevador"]),
    dict(titulo="Casa em condomínio com quintal para os pets", tipo="casa", finalidade="aluguel", bairro="Recreio",
         preco=8_500, quartos=3, banheiros=3, vagas=2, area_m2=200,
         caracteristicas=["condominio-fechado", "jardim", "pet-friendly", "churrasqueira", "suite"]),
    dict(titulo="Clássico de frente para o mar", tipo="apartamento", finalidade="venda", bairro="Ipanema",
         preco=4_600_000, quartos=3, banheiros=3, vagas=2, area_m2=190,
         caracteristicas=["vista-mar", "perto-do-mar", "portaria-24h", "suite", "elevador"]),
    dict(titulo="Lançamento com varanda gourmet", tipo="apartamento", finalidade="venda", bairro="Flamengo",
         preco=1_390_000, quartos=3, banheiros=2, vagas=1, area_m2=96,
         caracteristicas=["novo", "varanda-gourmet", "academia", "perto-metro", "aceita-financiamento"]),
    dict(titulo="Sala comercial pronta para consultório", tipo="comercial", finalidade="aluguel", bairro="Botafogo",
         preco=4_200, quartos=0, banheiros=1, vagas=1, area_m2=40,
         caracteristicas=["perto-metro", "portaria-24h", "elevador"]),
]


def semear(db: Session) -> Imobiliaria:
    demo = db.scalar(select(Imobiliaria).where(Imobiliaria.chave_publica == CHAVE_DEMO))
    if demo is not None:
        return demo

    demo = Imobiliaria(
        nome="Imobiliária Demonstração",
        chave_publica=CHAVE_DEMO,
        cor_primaria="#1F3B2C",
        plano="escala",
    )
    db.add(demo)
    db.flush()

    db.add(Usuario(
        imobiliaria_id=demo.id,
        nome="Conta de demonstração",
        email="demo@kazapro.invalid",
        senha_hash=gerar_hash_senha(gerar_senha_temporaria()),
        papel="dono",
        consentimento_em=datetime.now(timezone.utc),
        consentimento_texto=TEXTO_CONSENTIMENTO_CONTA_V1,
    ))

    for dados in _IMOVEIS_DEMO:
        db.add(Imovel(imobiliaria_id=demo.id, cidade="Rio de Janeiro", descricao="", **dados))

    db.commit()
    return demo


if __name__ == "__main__":
    with SessionLocal() as sessao:
        semear(sessao)
        print("Imobiliária de demonstração pronta.")
