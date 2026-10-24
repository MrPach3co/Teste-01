"""Motor de interpretação determinístico (sem IA).

Plano B usado quando não há ANTHROPIC_API_KEY ou quando a chamada à IA
falha. Entende os pedidos mais comuns em português: orçamento, quartos,
tipo, compra/aluguel, bairro e características.
"""

import re
from dataclasses import dataclass, field

from app.services.vocabulario import (
    SINONIMOS_CARACTERISTICA,
    SINONIMOS_TIPO,
    normalizar,
)

_NUMEROS_POR_EXTENSO = {
    "um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4, "cinco": 5, "seis": 6,
}


@dataclass
class Filtros:
    orcamento_maximo: float | None = None
    quartos_minimos: int | None = None
    tipo: str | None = None
    finalidade: str | None = None  # "venda" | "aluguel"
    bairros: list[str] = field(default_factory=list)
    caracteristicas: list[str] = field(default_factory=list)


def _numero(valor: str) -> float:
    # "1.200.000" -> 1200000 ; "1,5" -> 1.5 ; "2.5" -> 2.5
    if re.fullmatch(r"\d{1,3}(\.\d{3})+", valor):
        return float(valor.replace(".", ""))
    return float(valor.replace(",", "."))


def extrair_orcamento(texto: str) -> float | None:
    milhoes = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:milh|mi\b)", texto)
    if milhoes:
        return _numero(milhoes.group(1)) * 1_000_000

    mil = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:mil\b|k\b)", texto)
    if mil:
        return _numero(mil.group(1)) * 1_000

    valor_direto = re.search(r"r\$\s*([\d.,]+)", texto)
    if valor_direto:
        bruto = valor_direto.group(1).rstrip(".,")
        if "," in bruto:
            bruto = bruto.replace(".", "").replace(",", ".")
            return float(bruto)
        return _numero(bruto)

    return None


def extrair_quartos(texto: str) -> int | None:
    encontrado = re.search(r"(\d+|um|uma|dois|duas|tres|quatro|cinco|seis)\s*(?:quarto|dormit|qto)", texto)
    if not encontrado:
        return None
    valor = encontrado.group(1)
    return int(valor) if valor.isdigit() else _NUMEROS_POR_EXTENSO[valor]


def extrair_tipo(texto: str) -> str | None:
    for chave, tipo in SINONIMOS_TIPO.items():
        if chave in texto + " ":
            return tipo
    return None


def extrair_finalidade(texto: str) -> str | None:
    if re.search(r"alug|locac|locar|por mes|/mes|mensal", texto):
        return "aluguel"
    if re.search(r"compr|venda|vender|adquirir|investir|financ", texto):
        return "venda"
    return None


def extrair_caracteristicas(texto: str) -> list[str]:
    encontradas: list[str] = []
    for chave, slug in SINONIMOS_CARACTERISTICA.items():
        if re.search(rf"\b{re.escape(chave)}", texto) and slug not in encontradas:
            encontradas.append(slug)
    # "varanda gourmet" casa também com "varanda"; fica só a mais específica.
    if "varanda-gourmet" in encontradas and "varanda" in encontradas:
        encontradas.remove("varanda")
    # "vista para o mar" implica "mar", mas não "perto do mar" necessariamente.
    return encontradas


def extrair_bairros(texto: str, bairros_conhecidos: list[str]) -> list[str]:
    return [b for b in bairros_conhecidos if normalizar(b) in texto]


def interpretar(texto: str, bairros_conhecidos: list[str]) -> Filtros:
    t = normalizar(texto)
    return Filtros(
        orcamento_maximo=extrair_orcamento(t),
        quartos_minimos=extrair_quartos(t),
        tipo=extrair_tipo(t),
        finalidade=extrair_finalidade(t),
        bairros=extrair_bairros(t, bairros_conhecidos),
        caracteristicas=extrair_caracteristicas(t),
    )
