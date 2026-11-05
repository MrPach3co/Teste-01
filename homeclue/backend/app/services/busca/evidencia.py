"""Achar no texto do anúncio a prova de cada afirmação — a trava contra invenção.

Nenhuma característica é dada como "atende" sem um trecho do próprio
anúncio que comprove, e o trecho mostrado ao comprador é sempre o texto
original da imobiliária. Negações ("não aceita animais", "sem garagem")
viram "não atende", nunca "atende".
"""

import re
from dataclasses import dataclass

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


def _negado(palavras_norm: list[str], indice: int) -> bool:
    antes = palavras_norm[max(0, indice - 4):indice]
    for i in range(len(antes) - 1, -1, -1):
        if antes[i] in NEGACOES:
            return all(p in _PALAVRAS_DE_LIGACAO for p in antes[i + 1:])
    return False


def _recorte(palavras: list[str], inicio: int, fim: int) -> str:
    texto = " ".join(palavras)
    if len(texto) <= _TAMANHO_MAXIMO_TRECHO:
        return texto
    a, b = max(0, inicio - 14), min(len(palavras), fim + 14)
    return ("… " if a > 0 else "") + " ".join(palavras[a:b]) + (" …" if b < len(palavras) else "")


def _ocorrencias(termo_norm: str, palavras_norm: list[str]) -> list[tuple[int, int]]:
    """Posições (índice inicial e final de palavra) onde o termo aparece."""
    alvo = termo_norm.split()
    if not alvo:
        return []
    achados = []
    for i in range(len(palavras_norm) - len(alvo) + 1):
        janela = palavras_norm[i:i + len(alvo)]
        # compara palavra a palavra, tolerando pontuação grudada ("piscina," == "piscina")
        if all(re.sub(r"[^\w-]", "", j) == a for j, a in zip(janela, alvo)):
            achados.append((i, i + len(alvo)))
    return achados


def procurar(termos: list[str], textos: list[tuple[str, str]]) -> Achado | None:
    """Procura qualquer um dos termos nos textos (fonte, texto). Uma menção
    positiva vence; só menções negadas resultam em "nao_atende"."""
    termos_norm = sorted({normalizar(t) for t in termos if t.strip()}, key=len, reverse=True)
    negativo: Achado | None = None
    for fonte, texto in textos:
        for sentenca in sentencas(texto):
            palavras = sentenca.split()
            palavras_norm = [normalizar(p) for p in palavras]
            for termo in termos_norm:
                for inicio, fim in _ocorrencias(termo, palavras_norm):
                    if _negado(palavras_norm, inicio):
                        negativo = negativo or Achado("nao_atende", _recorte(palavras, inicio, fim), fonte)
                    else:
                        return Achado("atende", _recorte(palavras, inicio, fim), fonte)
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
        for sentenca in sentencas(texto):
            palavras = sentenca.split()
            palavras_norm = [re.sub(r"[^\w-]", "", normalizar(p)) for p in palavras]
            posicoes = [palavras_norm.index(p) for p in importantes if p in palavras_norm]
            if len(posicoes) == len(importantes):
                inicio, fim = min(posicoes), max(posicoes) + 1
                status = "nao_atende" if _negado(palavras_norm, inicio) else "atende"
                return Achado(status, _recorte(palavras, inicio, fim), fonte)
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
