"""Interpretação determinística (sem IA) do pedido do comprador.

É o plano B quando não há ANTHROPIC_API_KEY ou quando a IA falha, e também
o que roda nos testes. Entende os pedidos mais comuns em português:
orçamento (inclusive faixas), quartos por extenso, suítes, vagas, área,
tipo, compra ou aluguel, cidade, bairro, características, proximidade
("perto de escola") e alguns desejos livres ("sala com luz da manhã").
"""

import re
import unicodedata

from app.services.busca.criterios import Criterios
from app.services.vocabulario import (
    DESEJOS_CONHECIDOS,
    PADROES_PERTO_DE,
    SINONIMOS_CARACTERISTICA,
    SINONIMOS_TIPO,
    normalizar,
)

_NUMEROS_POR_EXTENSO = {
    "um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4, "cinco": 5, "seis": 6,
    "sete": 7, "oito": 8, "nove": 9, "dez": 10,
}
_NUMERO = r"(\d+|um|uma|dois|duas|tres|quatro|cinco|seis|sete|oito|nove|dez)"


def _sem_acento_mesmo_tamanho(texto: str) -> str:
    """Tira acentos sem mudar posições, para recortar o trecho original depois."""
    saida = []
    for ch in texto.lower():
        base = "".join(c for c in unicodedata.normalize("NFKD", ch) if not unicodedata.combining(c))
        saida.append(base if len(base) == 1 else " ")
    return "".join(saida)


def _inteiro(valor: str) -> int:
    return int(valor) if valor.isdigit() else _NUMEROS_POR_EXTENSO[valor]


# ---------- dinheiro ----------

_VALOR = r"(?:r\$\s*)?(\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:[.,]\d+)?)\s*(milhoes|milhao|mi\b|mil\b|k\b|reais)?"


def _valor_em_reais(numero: str, unidade: str | None) -> float | None:
    if re.fullmatch(r"\d{1,3}(\.\d{3})+(,\d+)?", numero):
        base = float(numero.replace(".", "").replace(",", "."))
    else:
        base = float(numero.replace(",", "."))
    if unidade in ("milhoes", "milhao", "mi"):
        return base * 1_000_000
    if unidade in ("mil", "k"):
        return base * 1_000
    return base


def _valores_monetarios(t: str) -> list[tuple[int, float]]:
    """(posição, valor) de cada menção a dinheiro. Ignora "3 quartos", "100 m2"."""
    achados = []
    for m in re.finditer(_VALOR, t):
        numero, unidade = m.group(1), m.group(2)
        depois = t[m.end():m.end() + 14]
        tem_cifrao = t[m.start():m.start() + 2] == "r$"
        if re.match(r"\s*(quarto|dorm|qto|suite|banheiro|vaga|m2|metro|andar|min|km|anos|pavimento)", depois):
            continue
        valor = _valor_em_reais(numero, unidade)
        if valor is None:
            continue
        if not (tem_cifrao or unidade or valor >= 1_000):
            continue
        achados.append((m.start(), valor))
    return achados


def extrair_orcamento(t: str) -> tuple[float | None, float | None]:
    """Retorna (mínimo, máximo)."""
    faixa = re.search(rf"(?:entre|de)\s+{_VALOR}\s+(?:e|a|ate)\s+{_VALOR}", t)
    if faixa:
        unidade_final = faixa.group(4)
        v1 = _valor_em_reais(faixa.group(1), faixa.group(2) or unidade_final)
        v2 = _valor_em_reais(faixa.group(3), unidade_final)
        if v1 and v2 and v2 >= 1_000:
            return (min(v1, v2), max(v1, v2))

    minimo = maximo = None
    for posicao, valor in _valores_monetarios(t):
        antes = t[max(0, posicao - 22):posicao]
        if re.search(r"(acima|a partir|mais) de\s*$|minimo( de)?\s*$|pelo menos\s*$|no minimo\s*$", antes):
            minimo = valor
        else:
            maximo = valor
    return (minimo, maximo)


# ---------- números de cômodos e área ----------

def _quantidade(t: str, padrao: str) -> int | None:
    m = re.search(rf"{_NUMERO}\s*(?:ou mais\s*)?{padrao}", t)
    return _inteiro(m.group(1)) if m else None


def extrair_area(t: str) -> float | None:
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:m2|m 2|metros quadrados|metros|mts)\b", t)
    return float(m.group(1).replace(",", ".")) if m else None


# ---------- tipo, finalidade, lugares ----------

def extrair_tipos(t: str) -> list[str]:
    """Tipos pedidos. "Casa com terreno grande" pede casa, não terreno: um
    tipo logo depois de "com"/"de" é característica, não o que se procura."""
    tipos: list[str] = []
    for chave in sorted(SINONIMOS_TIPO, key=len, reverse=True):
        for m in re.finditer(rf"\b{re.escape(chave)}\b", t):
            anterior = t[:m.start()].split()[-1:] or [""]
            if anterior[0] in ("com", "de", "do", "da", "no", "na", "bom", "grande", "amplo"):
                continue
            tipo = SINONIMOS_TIPO[chave]
            if tipo not in tipos:
                tipos.append(tipo)
    return tipos


def extrair_finalidade(t: str) -> str | None:
    aluguel = bool(re.search(r"alug|locac|locar\b|por mes|/mes|mensal|temporada", t))
    venda = bool(re.search(r"compr|\bvenda\b|a venda|adquirir|investir|investimento|financ", t))
    if aluguel and not venda:
        return "aluguel"
    if venda and not aluguel:
        return "venda"
    return None


# Nomes de bairro que também são palavras comuns ("pé-direito alto", "perto do
# centro comercial"): só contam como bairro depois de "no", "em", "bairro"…
_BAIRROS_PALAVRA_COMUM = {
    "alto", "centro", "prado", "jardim", "vila", "parque", "lagoa", "fazenda", "bosque", "granja", "morro", "rio",
    "serra", "ponte", "campo", "vale", "estrada", "alameda", "varzea", "cascata", "paraiso", "esperanca",
}
_PREPOSICOES_DE_LUGAR = {"no", "na", "em", "bairro", "do", "da", "pro", "pra", "ao"}


def _nomes_presentes(t: str, conhecidos: list[str]) -> list[str]:
    presentes = []
    for nome in sorted(conhecidos, key=len, reverse=True):
        n = normalizar(nome)
        if not n or nome in presentes:
            continue
        for m in re.finditer(rf"\b{re.escape(n)}\b", t):
            if n in _BAIRROS_PALAVRA_COMUM:
                anterior = (t[:m.start()].split() or [""])[-1]
                if anterior not in _PREPOSICOES_DE_LUGAR:
                    continue
                if n == "centro" and re.match(r"\s*(comercial|esportivo|cultural|de saude|medico)", t[m.end():]):
                    continue
            presentes.append(nome)
            break
    return presentes


# ---------- características, proximidade e desejos ----------

_NEGACOES_COMPRADOR = {"sem", "nao", "nem", "dispenso", "dispensa"}
_PALAVRAS_DE_LIGACAO = {"de", "da", "do", "a", "o", "precisa", "precisar", "preciso", "ter", "tem", "quero",
                        "faco", "questao", "importa", "com", "um", "uma"}


def _negado(t: str, inicio: int) -> bool:
    """"sem piscina" e "não precisa de piscina" negam; em "sem piscina com
    lareira" o "sem" não alcança a lareira."""
    antes = t[max(0, inicio - 40):inicio].split()[-4:]
    for i in range(len(antes) - 1, -1, -1):
        if antes[i] in _NEGACOES_COMPRADOR:
            return all(p in _PALAVRAS_DE_LIGACAO for p in antes[i + 1:])
    return False


def extrair_caracteristicas(t: str) -> tuple[list[str], list[str]]:
    """Retorna (pedidas, recusadas). "Sem piscina" e "não precisa de piscina"
    vão para recusadas — no turno seguinte de uma conversa, isso tira o item."""
    pedidas: list[str] = []
    recusadas: list[str] = []
    for chave in sorted(SINONIMOS_CARACTERISTICA, key=len, reverse=True):
        for m in re.finditer(rf"\b{re.escape(chave)}\b", t):
            slug = SINONIMOS_CARACTERISTICA[chave]
            destino = recusadas if (_negado(t, m.start()) and not chave.startswith("sem ")) else pedidas
            if slug not in destino:
                destino.append(slug)
    if "varanda-gourmet" in pedidas and "varanda" in pedidas:
        pedidas.remove("varanda")
    pedidas = [p for p in pedidas if p not in recusadas]
    return pedidas, recusadas


def extrair_perto_de(t: str, lugares: list[str] | tuple[str, ...] = ()) -> list[str]:
    # Nome de lugar não é pedido de proximidade: "perto da praia em Rio das
    # Ostras" não pede rio, e "no Parque São Clemente" não pede parque.
    for nome in sorted(lugares, key=len, reverse=True):
        nome_norm = normalizar(nome)
        if nome_norm:
            t = re.sub(rf"\b{re.escape(nome_norm)}\b", " ", t)
    categorias: list[str] = []
    for m in re.finditer(r"perto|proxim\w*|ao lado|a pe\b|caminhando|andando|vizinho", t):
        janela = t[m.end():m.end() + 60]
        for categoria, padrao in PADROES_PERTO_DE.items():
            if re.search(padrao, janela) and categoria not in categorias:
                categorias.append(categoria)
    return categorias


_PALAVRAS_VAZIAS = {
    "um", "uma", "uns", "umas", "o", "a", "os", "as", "de", "da", "do", "das", "dos", "e", "bom", "boa", "bons",
    "boas", "muito", "muita", "bastante", "algum", "alguma", "lugar", "espaco", "coisa", "imovel", "casa",
    "sala", "cozinha", "que", "tenha", "tenham",
}


def extrair_desejos(original: str, t: str) -> list[str]:
    desejos: list[str] = []
    for canonico, (padrao, _termos) in DESEJOS_CONHECIDOS.items():
        if re.search(padrao, t):
            desejos.append(canonico)

    # Frases livres depois de "com"/"que tenha": "com fogão de pedra", "com pé de jabuticaba e terraço".
    # Antes, tudo que já virou característica, tipo ou desejo conhecido é apagado do texto,
    # para "com vista para a serra" não sobrar um desejo "vista".
    sem_acento = _sem_acento_mesmo_tamanho(original)
    mascarado = sem_acento
    padroes_entendidos = [rf"\b{re.escape(k)}\b" for k in SINONIMOS_CARACTERISTICA]
    padroes_entendidos += [p for p, _ in DESEJOS_CONHECIDOS.values()]
    for padrao in padroes_entendidos:
        mascarado = re.sub(padrao, lambda m: "#" * len(m.group(0)), mascarado)

    fim = r"(?=$|[.;!?]| perto| proxim| ate | em | no | na | para | pra | que | com | mas | por )"
    for m in re.finditer(rf"\b(?:com|que tenha|que tenham|tenha|precisa ter)\s+([a-z#][a-z#\s,-]{{2,80}}?){fim}", mascarado):
        inicio_trecho = m.start(1)
        for item in re.finditer(r"[^,]+", m.group(1)):
            for parte in re.finditer(r"(?:(?<= e )|^)[^#]*?(?= e |$)", item.group(0)):
                frase_m = parte.group(0)
                frase_n = re.sub(r"^\s*(e |que tenham? |tenham? |que )", "", " ".join(frase_m.split()))
                frase_n = frase_n.strip(" -")
                palavras = [p for p in frase_n.split() if p not in _PALAVRAS_VAZIAS]
                if not palavras or len(palavras) > 5 or "#" in frase_n or frase_n in SINONIMOS_TIPO:
                    continue
                if re.search(r"quarto|dorm|suite|banheiro|vaga|garagem|metro|reais|mil\b|orcamento|\d", frase_n):
                    continue
                a = inicio_trecho + item.start() + parte.start()
                trecho = " ".join(original[a:a + len(frase_m)].lower().split())
                trecho = re.sub(r"^(e |que tenham? |tenham? |que )", "", trecho).strip(" -,")
                if trecho and trecho not in desejos:
                    desejos.append(trecho)
    return desejos


# ---------- turno completo ----------

def interpretar(texto: str, bairros_conhecidos: list[str], cidades_conhecidas: list[str]) -> tuple[Criterios, dict]:
    """Retorna (critérios deste turno, ajustes sobre os turnos anteriores)."""
    t = normalizar(texto)
    preco_min, preco_max = extrair_orcamento(t)
    pedidas, recusadas = extrair_caracteristicas(t)
    finalidade = extrair_finalidade(t)
    referencia = preco_max or preco_min
    if finalidade is None and referencia:
        # Ninguém compra imóvel por 3 mil, nem aluga por 700 mil.
        if referencia <= 30_000:
            finalidade = "aluguel"
        elif referencia >= 100_000:
            finalidade = "venda"

    vagas = _quantidade(t, r"vagas?")
    if vagas is None and re.search(r"\b(garagem|vaga|estacionamento)\b", t) and not _negado(t, t.find("garagem")):
        vagas = 1

    suites = _quantidade(t, r"suites?")
    if suites and "suite" in pedidas:
        pedidas.remove("suite")

    criterios = Criterios(
        finalidade=finalidade,
        tipos=extrair_tipos(t),
        cidades=_nomes_presentes(t, cidades_conhecidas),
        bairros=_nomes_presentes(t, bairros_conhecidos),
        preco_max=preco_max,
        preco_min=preco_min,
        quartos_min=_quantidade(t, r"(?:quartos?|dormitorios?|dorms?|qtos?)\b"),
        suites_min=suites,
        banheiros_min=_quantidade(t, r"banheiros?"),
        vagas_min=vagas,
        area_min=extrair_area(t),
        caracteristicas=pedidas,
        perto_de=extrair_perto_de(t, [*cidades_conhecidas, *bairros_conhecidos]),
        desejos=extrair_desejos(texto, t),
    )
    # Bairro com o mesmo nome de cidade (raro) fica só como bairro.
    criterios.cidades = [c for c in criterios.cidades if c not in criterios.bairros]

    ajustes = {
        "remover_caracteristicas": recusadas,
        "limpar_bairros": bool(re.search(r"qualquer bairro|tanto faz o bairro|outros bairros|outro bairro", t)),
        "limpar_preco": bool(re.search(r"qualquer (preco|valor)|sem limite de (preco|valor)", t)),
        "mais_barato": bool(re.search(r"mais barat|mais em conta|menor (preco|valor)", t)),
    }
    return criterios, ajustes


def aplicar_turno(anteriores: Criterios, texto: str, bairros: list[str], cidades: list[str]) -> Criterios:
    novo, ajustes = interpretar(texto, bairros, cidades)
    resultado = anteriores.mesclar(novo)
    resultado.caracteristicas = [c for c in resultado.caracteristicas if c not in ajustes["remover_caracteristicas"]]
    if ajustes["limpar_bairros"] and not novo.bairros:
        resultado.bairros = []
    if ajustes["limpar_preco"] and not novo.preco_max:
        resultado.preco_max = resultado.preco_min = None
    if ajustes["mais_barato"] and resultado.preco_max and not novo.preco_max:
        resultado.preco_max = round(resultado.preco_max * 0.85, -3)
    return resultado
