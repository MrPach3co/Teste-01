"""Ranqueamento dos imóveis de uma imobiliária contra os filtros extraídos.

Finalidade (venda/aluguel) é filtro duro — ninguém que quer alugar quer ver
imóvel à venda. O resto é pontuação: o imóvel que mais combina sobe, e cada
ponto ganho vira um "motivo" legível que o widget mostra ao visitante.
"""

from dataclasses import dataclass, field

from app.models import Imovel
from app.services.interpretador import Filtros
from app.services.vocabulario import CARACTERISTICAS, TIPOS, normalizar

MAXIMO_RESULTADOS = 6


@dataclass
class ResultadoMatch:
    imovel: Imovel
    match: int
    motivos: list[str] = field(default_factory=list)


def _formatar_reais(valor: float) -> str:
    if valor >= 1_000_000:
        return f"R$ {valor / 1_000_000:.1f} mi".replace(".", ",").replace(",0 ", " ")
    return f"R$ {valor:,.0f}".replace(",", ".")


def pontuar(imovel: Imovel, filtros: Filtros) -> ResultadoMatch:
    pontos = 40
    motivos: list[str] = []

    if filtros.tipo:
        if imovel.tipo == filtros.tipo:
            pontos += 14
            motivos.append(TIPOS[imovel.tipo])
        else:
            pontos -= 12

    if filtros.bairros:
        if normalizar(imovel.bairro) in {normalizar(b) for b in filtros.bairros}:
            pontos += 16
            motivos.append(f"Em {imovel.bairro}")
        else:
            pontos -= 8

    if filtros.orcamento_maximo:
        if imovel.preco <= filtros.orcamento_maximo:
            pontos += 18
            if imovel.preco <= filtros.orcamento_maximo * 0.85:
                pontos += 5
            motivos.append(f"Dentro do orçamento ({_formatar_reais(imovel.preco)})")
        elif imovel.preco <= filtros.orcamento_maximo * 1.1:
            pontos -= 6
        else:
            pontos -= 22

    if filtros.quartos_minimos:
        if imovel.quartos >= filtros.quartos_minimos:
            pontos += 12 if imovel.quartos == filtros.quartos_minimos else 7
            motivos.append(f"{imovel.quartos} quarto{'s' if imovel.quartos != 1 else ''}")
        else:
            pontos -= 14

    tem = set(imovel.caracteristicas or [])
    for slug in filtros.caracteristicas:
        if slug in tem:
            pontos += 9
            motivos.append(CARACTERISTICAS[slug])
        else:
            pontos -= 3

    return ResultadoMatch(imovel=imovel, match=max(5, min(99, round(pontos))), motivos=motivos)


def ranquear(imoveis: list[Imovel], filtros: Filtros) -> list[ResultadoMatch]:
    candidatos = [i for i in imoveis if i.ativo]
    if filtros.finalidade:
        candidatos = [i for i in candidatos if i.finalidade == filtros.finalidade]

    pontuados = [pontuar(i, filtros) for i in candidatos]
    pontuados.sort(key=lambda r: (r.match, -r.imovel.preco), reverse=True)
    return pontuados[:MAXIMO_RESULTADOS]


def resumir_filtros(filtros: Filtros) -> list[str]:
    """Chips do que foi entendido — transparência para o visitante."""
    chips: list[str] = []
    if filtros.finalidade:
        chips.append("Alugar" if filtros.finalidade == "aluguel" else "Comprar")
    if filtros.tipo:
        chips.append(TIPOS[filtros.tipo])
    chips.extend(filtros.bairros)
    if filtros.orcamento_maximo:
        chips.append(f"Até {_formatar_reais(filtros.orcamento_maximo)}")
    if filtros.quartos_minimos:
        chips.append(f"{filtros.quartos_minimos}+ quartos")
    chips.extend(CARACTERISTICAS[c] for c in filtros.caracteristicas)
    return chips
