"""Catálogo de planos, limites e recursos.

Fica em código (e não no banco) de propósito: mudar limite ou recurso é uma
decisão de produto que deve passar por revisão. Os preços exibidos vêm de
variáveis de ambiente (ver core.config), porque ainda serão definidos depois
de medir o custo de IA por busca. None significa "sem limite".
"""

from dataclasses import dataclass

from app.core.config import obter_settings

# Recursos que variam por plano. O núcleo (busca com match explicado, trava
# contra invenção, feed XML, widget, leads no WhatsApp) existe em todos.
COMPARADOR = "comparador"
RANKINGS = "rankings"
CONTEXTO_BAIRRO = "contexto_bairro"
RELATORIO_DEMANDA = "relatorio_demanda"
MIDIA_DRONE = "midia_drone"
SEM_MARCA = "sem_marca"
PLANTA_INTERATIVA = "planta_interativa"
MAQUETE_3D = "maquete_3d"
LANCAMENTOS = "lancamentos"
BUSCA_POR_FOTO = "busca_por_foto"
ANALISE_FOTOS = "analise_fotos"

_FASE_2 = frozenset({COMPARADOR, RANKINGS, CONTEXTO_BAIRRO, RELATORIO_DEMANDA})
_PREMIUM = frozenset({PLANTA_INTERATIVA, MAQUETE_3D, LANCAMENTOS, BUSCA_POR_FOTO, ANALISE_FOTOS})

NOMES_RECURSOS = {
    COMPARADOR: "Comparador de imóveis",
    RANKINGS: "Rankings por perfil",
    CONTEXTO_BAIRRO: "Contexto do bairro",
    RELATORIO_DEMANDA: "Relatório de demanda",
    MIDIA_DRONE: "Vídeo e imagens de drone",
    SEM_MARCA: "Widget sem a marca Homeclue",
    PLANTA_INTERATIVA: "Planta interativa",
    MAQUETE_3D: "Maquete 3D",
    LANCAMENTOS: "Espelho 3D de lançamentos",
    BUSCA_POR_FOTO: "Busca por foto",
    ANALISE_FOTOS: "Análise das fotos dos anúncios",
}


@dataclass(frozen=True)
class Plano:
    id: str
    nome: str
    limite_imoveis: int | None
    limite_buscas_mes: int | None
    limite_usuarios: int
    recursos: frozenset[str]
    destaque: str

    @property
    def preco_mensal(self) -> int:
        s = obter_settings()
        return {
            "essencial": s.preco_plano_essencial,
            "profissional": s.preco_plano_profissional,
            "premium": s.preco_plano_premium,
        }.get(self.id, 0)


PLANOS: dict[str, Plano] = {
    "gratis": Plano(
        id="gratis", nome="Teste grátis", limite_imoveis=30, limite_buscas_mes=300, limite_usuarios=1,
        recursos=_FASE_2, destaque="Para conhecer no seu site",
    ),
    "essencial": Plano(
        id="essencial", nome="Essencial", limite_imoveis=150, limite_buscas_mes=3_000, limite_usuarios=3,
        recursos=_FASE_2 | {SEM_MARCA}, destaque="Para imobiliárias pequenas",
    ),
    "profissional": Plano(
        id="profissional", nome="Profissional", limite_imoveis=600, limite_buscas_mes=10_000, limite_usuarios=10,
        recursos=_FASE_2 | {SEM_MARCA, MIDIA_DRONE}, destaque="Para carteiras maiores",
    ),
    "premium": Plano(
        id="premium", nome="Premium", limite_imoveis=None, limite_buscas_mes=30_000, limite_usuarios=30,
        recursos=_FASE_2 | _PREMIUM | {SEM_MARCA, MIDIA_DRONE},
        destaque="Planta interativa, 3D, lançamentos e busca por foto",
    ),
}

# Planos da versão anterior (Kaza Pro) continuam funcionando.
_APELIDOS = {"pro": "profissional", "escala": "premium"}


def obter_plano(plano_id: str) -> Plano:
    return PLANOS.get(_APELIDOS.get(plano_id, plano_id), PLANOS["gratis"])


def tem_recurso(plano_id: str, recurso: str) -> bool:
    return recurso in obter_plano(plano_id).recursos
