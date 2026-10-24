"""Vocabulário controlado do produto.

Os imóveis são cadastrados com características deste dicionário, e tanto
a IA quanto o motor de regras traduzem o texto livre do visitante para
estes mesmos slugs — é isso que torna o match comparável.
"""

import unicodedata

TIPOS: dict[str, str] = {
    "apartamento": "Apartamento",
    "casa": "Casa",
    "cobertura": "Cobertura",
    "studio": "Studio / Kitnet",
    "terreno": "Terreno",
    "comercial": "Sala / Loja comercial",
}

SINONIMOS_TIPO: dict[str, str] = {
    "apartamento": "apartamento",
    "apto": "apartamento",
    "ap ": "apartamento",
    "flat": "apartamento",
    "casa": "casa",
    "sobrado": "casa",
    "cobertura": "cobertura",
    "studio": "studio",
    "estudio": "studio",
    "kitnet": "studio",
    "quitinete": "studio",
    "loft": "studio",
    "terreno": "terreno",
    "lote": "terreno",
    "sala comercial": "comercial",
    "loja": "comercial",
    "comercial": "comercial",
    "escritorio comercial": "comercial",
}

CARACTERISTICAS: dict[str, str] = {
    "piscina": "Piscina",
    "churrasqueira": "Churrasqueira",
    "varanda-gourmet": "Varanda gourmet",
    "varanda": "Varanda",
    "academia": "Academia",
    "elevador": "Elevador",
    "portaria-24h": "Portaria 24h",
    "condominio-fechado": "Condomínio fechado",
    "pet-friendly": "Aceita pets",
    "mobiliado": "Mobiliado",
    "vista-mar": "Vista para o mar",
    "perto-do-mar": "Perto da praia",
    "perto-metro": "Perto do metrô",
    "escritorio": "Escritório / home office",
    "suite": "Suíte",
    "jardim": "Jardim / quintal",
    "reformado": "Reformado",
    "novo": "Novo / na planta",
    "playground": "Playground",
    "aceita-financiamento": "Aceita financiamento",
}

SINONIMOS_CARACTERISTICA: dict[str, str] = {
    "piscina": "piscina",
    "churrasqueira": "churrasqueira",
    "churrasco": "churrasqueira",
    "varanda gourmet": "varanda-gourmet",
    "espaco gourmet": "varanda-gourmet",
    "varanda": "varanda",
    "sacada": "varanda",
    "academia": "academia",
    "elevador": "elevador",
    "portaria": "portaria-24h",
    "porteiro": "portaria-24h",
    "seguranca": "condominio-fechado",
    "condominio fechado": "condominio-fechado",
    "condominio": "condominio-fechado",
    "pet": "pet-friendly",
    "cachorro": "pet-friendly",
    "gato": "pet-friendly",
    "animais": "pet-friendly",
    "mobiliado": "mobiliado",
    "mobiliada": "mobiliado",
    "com moveis": "mobiliado",
    "vista mar": "vista-mar",
    "vista para o mar": "vista-mar",
    "vista pro mar": "vista-mar",
    "praia": "perto-do-mar",
    "beira mar": "perto-do-mar",
    "perto do mar": "perto-do-mar",
    "metro": "perto-metro",
    "escritorio": "escritorio",
    "home office": "escritorio",
    "trabalhar de casa": "escritorio",
    "suite": "suite",
    "jardim": "jardim",
    "quintal": "jardim",
    "reformado": "reformado",
    "reformada": "reformado",
    "novo": "novo",
    "nova": "novo",
    "na planta": "novo",
    "lancamento": "novo",
    "playground": "playground",
    "criancas": "playground",
    "financiamento": "aceita-financiamento",
    "financiar": "aceita-financiamento",
}


def normalizar(texto: str) -> str:
    """Minúsculas e sem acentos — "Condomínio" e "condominio" viram a mesma coisa."""
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return sem_acento.lower()


def caracteristicas_validas(slugs: list[str]) -> list[str]:
    """Descarta slugs desconhecidos e duplicados, preservando a ordem."""
    vistos: list[str] = []
    for slug in slugs:
        if slug in CARACTERISTICAS and slug not in vistos:
            vistos.append(slug)
    return vistos
