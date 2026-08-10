"""Motor de match determinístico (sem IA).

É o plano B usado quando não há ANTHROPIC_API_KEY configurada — mesma
lógica que existia no protótipo em JavaScript puro, portada para Python.
"""

import re

DICIONARIO_TAGS = {
    "moderna": "moderna",
    "moderno": "moderna",
    "perto do mar": "perto-do-mar",
    "beira mar": "perto-do-mar",
    "beira-mar": "perto-do-mar",
    "frente ao mar": "perto-do-mar",
    "praia": "perto-do-mar",
    "vista mar": "vista-mar",
    "vista para o mar": "vista-mar",
    "vista": "vista-mar",
    "escritório": "escritorio",
    "escritorio": "escritorio",
    "home office": "escritorio",
    "cobertura": "cobertura",
    "piscina": "piscina",
    "reformado": "reformado",
    "reformada": "reformado",
    "condomínio": "condominio-fechado",
    "condominio": "condominio-fechado",
    "segurança": "condominio-fechado",
    "seguranca": "condominio-fechado",
    "pet": "pet-friendly",
    "animais": "pet-friendly",
    "investimento": "investimento",
    "valorização": "investimento",
    "valorizacao": "investimento",
}


def extrair_orcamento(texto: str) -> float | None:
    milhoes = re.search(r"(\d+(?:[.,]\d+)?)\s*milh", texto)
    if milhoes:
        return float(milhoes.group(1).replace(",", ".")) * 1_000_000

    mil = re.search(r"(\d+(?:[.,]\d+)?)\s*mil\b", texto)
    if mil:
        return float(mil.group(1).replace(",", ".")) * 1_000

    valor_direto = re.search(r"r\$\s*([\d.,]+)", texto)
    if valor_direto:
        return float(valor_direto.group(1).replace(".", "").replace(",", "."))

    return None


def extrair_quartos(texto: str) -> int | None:
    encontrado = re.search(r"(\d+)\s*(quarto|dormit)", texto)
    return int(encontrado.group(1)) if encontrado else None


def extrair_tags(texto: str) -> set[str]:
    encontradas = set()
    for chave, slug in DICIONARIO_TAGS.items():
        if chave in texto:
            encontradas.add(slug)
    return encontradas


def calcular_match(
    *,
    tags_imovel: set[str],
    preco: float,
    quartos: int,
    tags_pedidas: set[str],
    orcamento: float | None,
    quartos_pedidos: int | None,
) -> int:
    pontos = 45  # toda busca começa com uma base, para nunca ficar em 0%

    for tag in tags_pedidas:
        if tag in tags_imovel:
            pontos += 12

    if orcamento:
        if preco <= orcamento:
            pontos += 20
            if preco <= orcamento * 0.85:
                pontos += 6
        else:
            pontos -= 18

    if quartos_pedidos:
        if quartos == quartos_pedidos:
            pontos += 15
        elif quartos > quartos_pedidos:
            pontos += 6
        else:
            pontos -= 10

    return max(30, min(99, round(pontos)))
