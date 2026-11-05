"""IA que confere os pedidos livres ("sala com luz da manhã") nos anúncios.

A trava contra invenção fica no código, não na boa vontade do modelo: a IA
precisa citar o trecho do anúncio que prova o que diz, e o trecho é
conferido palavra por palavra contra o texto real. Trecho que não existe no
anúncio vira "não informado".
"""

import json
import logging
from datetime import timedelta

from sqlalchemy.orm import Session

from app.services import cache
from app.services.busca import evidencia
from app.services.busca.avaliacao import ImovelBusca
from app.services.ia import cliente
from app.services.ia.cliente import UsoIA, chamar_json
from app.services.vocabulario import normalizar

logger = logging.getLogger(__name__)

_INSTRUCAO = """Você confere anúncios de imóveis para uma pessoa que está procurando imóvel.

Para cada pedido e cada anúncio, responda:
- "atende": o texto do anúncio comprova que atende ao pedido;
- "nao_atende": o texto do anúncio comprova que NÃO atende;
- "nao_informado": o anúncio não fala sobre isso.

Regras obrigatórias:
1. Use somente o texto do anúncio. Não deduza, não use conhecimento geral sobre o bairro ou a cidade, não suponha.
2. Em "atende" e "nao_atende", copie em "trecho" as palavras EXATAS do anúncio que provam a resposta (até 30 palavras, sem alterar nada).
3. Se não houver um trecho que prove, a resposta é "nao_informado" com trecho vazio."""

_SCHEMA = {
    "type": "object",
    "properties": {
        "avaliacoes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "imovel_id": {"type": "integer"},
                    "pedido": {"type": "integer"},
                    "status": {"type": "string", "enum": ["atende", "nao_atende", "nao_informado"]},
                    "trecho": {"type": "string"},
                },
                "required": ["imovel_id", "pedido", "status", "trecho"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["avaliacoes"],
    "additionalProperties": False,
}

_MAX_CARACTERES_ANUNCIO = 2500
_VERSAO_CACHE = 1
_VALIDADE_CACHE = timedelta(days=30)

Par = tuple[int, int]  # (imovel_id, índice do pedido)
Veredito = tuple[str, str, str]  # (status, trecho, fonte)


def verificar_desejos(desejos: list[str], imoveis: list[ImovelBusca], uso: UsoIA,
                      db: Session | None = None) -> dict[Par, Veredito]:
    """Retorna {(imovel_id, indice_do_desejo): (status, trecho, fonte)} só com
    respostas cuja prova foi conferida no anúncio.

    Com `db`, cada par (pedido, anúncio) já conferido vem do cache: a conversa
    continua, e o mesmo pedido não é pago de novo nos mesmos anúncios. A chave
    inclui o texto do anúncio, então anúncio editado é conferido de novo."""
    if not desejos or not imoveis:
        return {}

    chaves: dict[Par, str] = {}
    if db is not None:
        for imovel in imoveis:
            textos = imovel.textos()
            for indice, desejo in enumerate(desejos):
                chaves[(imovel.id, indice)] = cache.chave_de("verificacao", _VERSAO_CACHE, cliente.modelo(),
                                                             normalizar(desejo), textos)
    guardadas = cache.obter_varios(db, list(chaves.values())) if db is not None else {}
    vereditos: dict[Par, Veredito] = {}
    for par, chave in chaves.items():
        if chave in guardadas:
            v = guardadas[chave]
            vereditos[par] = (v.get("status", "nao_informado"), v.get("trecho", ""), v.get("fonte", ""))

    pendentes = [(i.id, d) for i in imoveis for d in range(len(desejos)) if (i.id, d) not in vereditos]
    if pendentes:
        ids = {imovel_id for imovel_id, _ in pendentes}
        indices = sorted({d for _, d in pendentes})
        respondidas = _perguntar(desejos, indices, [i for i in imoveis if i.id in ids], uso)
        if respondidas:
            vereditos.update(respondidas)
            if db is not None:
                cache.guardar_varios(db, {chaves[par]: {"status": s, "trecho": t, "fonte": f}
                                          for par, (s, t, f) in respondidas.items()}, _VALIDADE_CACHE)
    return {par: v for par, v in vereditos.items() if v[0] in ("atende", "nao_atende")}


def _perguntar(desejos: list[str], indices: list[int], imoveis: list[ImovelBusca],
               uso: UsoIA) -> dict[Par, Veredito] | None:
    """Uma chamada à IA. Devolve todos os pares que ela respondeu — o que não
    tem prova conferida vira "nao_informado" — ou None se a chamada falhou."""
    anuncios = []
    for imovel in imoveis:
        partes = [f"{fonte}: {texto}" for fonte, texto in imovel.textos() if texto]
        anuncios.append({"id": imovel.id, "texto": "\n".join(partes)[:_MAX_CARACTERES_ANUNCIO]})
    entrada = {
        "pedidos": [{"indice": i, "pedido": desejos[i]} for i in indices],
        "anuncios": anuncios,
    }
    dados = chamar_json(uso, system=_INSTRUCAO, conteudo=json.dumps(entrada, ensure_ascii=False), schema=_SCHEMA,
                        max_tokens=8000)
    if dados is None:
        return None

    por_id = {i.id: i for i in imoveis}
    respondidas: dict[Par, Veredito] = {}
    descartadas = 0
    for item in dados.get("avaliacoes", []):
        imovel = por_id.get(item.get("imovel_id"))
        indice = item.get("pedido")
        if imovel is None or indice not in indices:
            continue
        par = (imovel.id, indice)
        status, trecho = item.get("status"), (item.get("trecho") or "").strip()
        fonte = None
        if status in ("atende", "nao_atende"):
            fonte = next((f for f, t in imovel.textos() if evidencia.trecho_presente(trecho, [(f, t)])), None)
            if fonte is None:
                descartadas += 1  # trava: a IA citou algo que não está no anúncio
        if fonte is not None:
            respondidas[par] = (status, trecho, fonte)
        else:
            respondidas.setdefault(par, ("nao_informado", "", ""))
    if descartadas:
        logger.info("Trava contra invenção descartou %d afirmação(ões) sem prova no anúncio", descartadas)
    return respondidas
