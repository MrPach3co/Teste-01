"""Achar no texto do anúncio a prova de cada afirmação — a trava contra invenção.

Nenhuma característica é dada como "atende" sem um trecho do próprio
anúncio que comprove, e o trecho mostrado ao comprador é sempre o texto
original da imobiliária. Negações ("não aceita animais", "sem garagem")
viram "não atende", nunca "atende".
"""

import re
from dataclasses import dataclass
from functools import lru_cache

from app.services.vocabulario import NEGACOES, normalizar

_PALAVRAS_DE_LIGACAO = {
    "aceita", "aceitam", "aceitamos", "permite", "permitem", "permitido", "permitida", "permitidos", "possui",
    "possuimos", "tem", "temos", "ha", "de", "da", "do", "das", "dos", "com", "e", "o", "a", "os", "as", "se",
    "dispoe", "dispomos", "conta", "contem", "inclui", "incluso", "inclusa", "um", "uma", "nenhum", "nenhuma",
}
_TAMANHO_MAXIMO_TRECHO = 220


@dataclass
class Achado:
    status: str  # "atende" | "nao_atende"
    trecho: str  # texto original do anúncio
    fonte: str  # "titulo" | "descricao" | "comodidades" | "planta"


def sentencas(texto: str) -> list[str]:
    partes = re.split(r"(?<=[.!?;])\s+|\n+|\s+[•·]\s+|\s+-\s+(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇ])", texto or "")
    return [p.strip(" -•·\t") for p in partes if p and p.strip(" -•·\t")]


@dataclass(frozen=True)
class _Sentenca:
    palavras: tuple[str, ...]  # como estão no anúncio (é o que o comprador vê no trecho)
    normalizadas: tuple[str, ...]  # minúsculas e sem acento, com a pontuação
    limpas: tuple[str, ...]  # normalizadas e sem pontuação grudada ("piscina," == "piscina")
    conjunto: frozenset[str]  # as limpas, para descartar a frase sem varrer


_PONTUACAO = re.compile(r"[^\w-]")


@lru_cache(maxsize=512)
def _preparar(texto: str) -> tuple[_Sentenca, ...]:
    """Quebra e normaliza o texto uma vez só. A busca avalia cada imóvel por
    inteiro antes de passar ao próximo, então este cache pequeno evita refazer
    o trabalho para cada característica pedida (com 1.000+ imóveis, era o que
    deixava a busca lenta)."""
    preparadas = []
    for sentenca in sentencas(texto):
        palavras = tuple(sentenca.split())
        # Atalhos com o mesmo resultado: palavra sem acento só precisa de lower();
        # palavra só de letras e números não tem pontuação para tirar.
        normalizadas = tuple(p.lower() if p.isascii() else normalizar(p) for p in palavras)
        limpas = tuple(p if p.isalnum() else _PONTUACAO.sub("", p) for p in normalizadas)
        preparadas.append(_Sentenca(palavras, normalizadas, limpas, frozenset(limpas)))
    return tuple(preparadas)


def _negado(palavras_norm: tuple[str, ...], indice: int) -> bool:
    antes = palavras_norm[max(0, indice - 4):indice]
    for i in range(len(antes) - 1, -1, -1):
        if antes[i] in NEGACOES:
            return all(p in _PALAVRAS_DE_LIGACAO for p in antes[i + 1:])
    return False


def _recorte(palavras: tuple[str, ...], inicio: int, fim: int) -> str:
    texto = " ".join(palavras)
    if len(texto) <= _TAMANHO_MAXIMO_TRECHO:
        return texto
    a, b = max(0, inicio - 14), min(len(palavras), fim + 14)
    return ("… " if a > 0 else "") + " ".join(palavras[a:b]) + (" …" if b < len(palavras) else "")


def _ocorrencias(alvo: tuple[str, ...], sentenca: _Sentenca) -> list[tuple[int, int]]:
    """Posições (índice inicial e final de palavra) onde o termo aparece,
    comparando palavra a palavra sem a pontuação grudada."""
    if not alvo or alvo[0] not in sentenca.conjunto:
        return []
    limpas, tamanho = sentenca.limpas, len(alvo)
    return [(i, i + tamanho) for i in range(len(limpas) - tamanho + 1)
            if limpas[i] == alvo[0] and limpas[i:i + tamanho] == alvo]


def procurar(termos: list[str], textos: list[tuple[str, str]]) -> Achado | None:
    """Procura qualquer um dos termos nos textos (fonte, texto). Uma menção
    positiva vence; só menções negadas resultam em "nao_atende"."""
    termos_norm = sorted({normalizar(t) for t in termos if t.strip()}, key=len, reverse=True)
    alvos = [tuple(t.split()) for t in termos_norm]
    negativo: Achado | None = None
    for fonte, texto in textos:
        for sentenca in _preparar(texto or ""):
            for alvo in alvos:
                for inicio, fim in _ocorrencias(alvo, sentenca):
                    if _negado(sentenca.normalizadas, inicio):
                        negativo = negativo or Achado("nao_atende", _recorte(sentenca.palavras, inicio, fim), fonte)
                    else:
                        return Achado("atende", _recorte(sentenca.palavras, inicio, fim), fonte)
    return negativo


_VAZIAS = {"com", "de", "da", "do", "das", "dos", "para", "pra", "uma", "um", "que", "tenha", "bem", "bom", "boa",
           "muito", "muita", "mais", "e", "o", "a", "os", "as", "no", "na", "em"}


def procurar_frase_livre(frase: str, textos: list[tuple[str, str]]) -> Achado | None:
    """Para desejos livres ("pé de jabuticaba"): a frase inteira, ou todas as
    palavras importantes dela na mesma frase do anúncio."""
    exato = procurar([frase], textos)
    if exato:
        return exato
    importantes = [p for p in normalizar(frase).split() if len(p) >= 4 and p not in _VAZIAS]
    if len(importantes) < 2:
        return None
    for fonte, texto in textos:
        for sentenca in _preparar(texto or ""):
            if not all(p in sentenca.conjunto for p in importantes):
                continue
            posicoes = [sentenca.limpas.index(p) for p in importantes]
            inicio, fim = min(posicoes), max(posicoes) + 1
            status = "nao_atende" if _negado(sentenca.limpas, inicio) else "atende"
            return Achado(status, _recorte(sentenca.palavras, inicio, fim), fonte)
    return None


def trecho_presente(trecho: str, textos: list[tuple[str, str]]) -> bool:
    """Confere se um trecho citado (pela IA) existe de verdade no anúncio."""
    alvo = normalizar(re.sub(r"[“”\"'…]|\.\.\.", " ", trecho or ""))
    alvo = re.sub(r"[^\w\s-]", " ", alvo)
    alvo = " ".join(alvo.split())
    if len(alvo) < 6:
        return False
    for _fonte, texto in textos:
        corpo = " ".join(re.sub(r"[^\w\s-]", " ", normalizar(texto)).split())
        if alvo in corpo:
            return True
    return False
