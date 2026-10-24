"""Catálogo de planos e seus limites.

Fica em código (e não no banco) de propósito: mudar preço ou limite é uma
decisão de produto que deve passar por revisão, não um clique no painel.
None significa "sem limite".
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Plano:
    id: str
    nome: str
    preco_mensal: int  # em reais
    limite_imoveis: int | None
    limite_buscas_mes: int | None
    limite_usuarios: int
    marca_kaza_no_widget: bool
    destaque: str


PLANOS: dict[str, Plano] = {
    "gratis": Plano(
        id="gratis",
        nome="Grátis",
        preco_mensal=0,
        limite_imoveis=15,
        limite_buscas_mes=300,
        limite_usuarios=1,
        marca_kaza_no_widget=True,
        destaque="Para testar no seu site",
    ),
    "pro": Plano(
        id="pro",
        nome="Pro",
        preco_mensal=197,
        limite_imoveis=300,
        limite_buscas_mes=5_000,
        limite_usuarios=5,
        marca_kaza_no_widget=False,
        destaque="Para imobiliárias em crescimento",
    ),
    "escala": Plano(
        id="escala",
        nome="Escala",
        preco_mensal=497,
        limite_imoveis=None,
        limite_buscas_mes=30_000,
        limite_usuarios=25,
        marca_kaza_no_widget=False,
        destaque="Para redes e grandes carteiras",
    ),
}


def obter_plano(plano_id: str) -> Plano:
    return PLANOS.get(plano_id, PLANOS["gratis"])
