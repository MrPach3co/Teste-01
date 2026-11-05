"""IA que confere os pedidos livres ("sala com luz da manhã") nos anúncios.

A trava contra invenção fica no código, não na boa vontade do modelo: a IA
precisa citar o trecho do anúncio que prova o que diz, e o trecho é
conferido palavra por palavra contra o texto real. Trecho que não existe no
anúncio vira "não informado".
"""

import json
import logging

from app.services.busca import evidencia
from app.services.busca.avaliacao import ImovelBusca
from app.services.ia.cliente import UsoIA, chamar_json

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


def verificar_desejos(desejos: list[str], imoveis: list[ImovelBusca],
                      uso: UsoIA) -> dict[tuple[int, int], tuple[str, str, str]]:
    """Retorna {(imovel_id, indice_do_desejo): (status, trecho, fonte)} só com
    respostas cuja prova foi conferida no anúncio."""
    if not desejos or not imoveis:
        return {}

    anuncios = []
    for imovel in imoveis:
        partes = [f"{fonte}: {texto}" for fonte, texto in imovel.textos() if texto]
        anuncios.append({"id": imovel.id, "texto": "\n".join(partes)[:_MAX_CARACTERES_ANUNCIO]})
    entrada = {
        "pedidos": [{"indice": i, "pedido": d} for i, d in enumerate(desejos)],
        "anuncios": anuncios,
    }
    dados = chamar_json(uso, system=_INSTRUCAO, conteudo=json.dumps(entrada, ensure_ascii=False), schema=_SCHEMA,
                        max_tokens=8000)
    if not dados:
        return {}

    por_id = {i.id: i for i in imoveis}
    conferidas: dict[tuple[int, int], tuple[str, str, str]] = {}
    descartadas = 0
    for item in dados.get("avaliacoes", []):
        imovel = por_id.get(item.get("imovel_id"))
        indice = item.get("pedido")
        if imovel is None or not isinstance(indice, int) or not (0 <= indice < len(desejos)):
            continue
        status, trecho = item.get("status"), (item.get("trecho") or "").strip()
        if status not in ("atende", "nao_atende"):
            continue
        fonte = next((f for f, t in imovel.textos() if evidencia.trecho_presente(trecho, [(f, t)])), None)
        if fonte is None:
            descartadas += 1  # trava: a IA citou algo que não está no anúncio
            continue
        conferidas[(imovel.id, indice)] = (status, trecho, fonte)
    if descartadas:
        logger.info("Trava contra invenção descartou %d afirmação(ões) sem prova no anúncio", descartadas)
    return conferidas
