"""IA que transforma a conversa do comprador em critérios de busca."""

import json

from app.services.busca.criterios import Criterios
from app.services.ia.cliente import UsoIA, anulavel, chamar_json
from app.services.vocabulario import CARACTERISTICAS, CATEGORIAS_CONTEXTO, TIPOS

_INSTRUCAO = """Você transforma o que uma pessoa procurando imóvel escreve em critérios de busca, numa conversa no site de uma imobiliária brasileira.

Regras:
- Use só o que a pessoa disse ou deixou claro. Nunca acrescente preferências que ela não expressou.
- "criterios_atuais" são os critérios da conversa até agora. Mantenha-os, a não ser que a nova mensagem mude ou retire algo. Se ela trocar de bairro, tipo ou cidade, substitua; se pedir para tirar algo ("não precisa de piscina"), retire; se refinar ("e com garagem?"), acrescente.
- Valores em reais. "até 600 mil" = preco_max 600000. Para aluguel, o valor é mensal.
- "caracteristicas" e "perto_de" só aceitam os códigos da lista. "quintal pra cachorro" = jardim + pet-friendly.
- Bairros e cidades: use os nomes das listas disponíveis, escritos exatamente como lá.
- "desejos" são pedidos que não cabem em nenhum outro campo nem na lista de características ("sala com luz da manhã", "rua tranquila", "pé de jabuticaba"). Escreva cada um em poucas palavras, na voz da pessoa. Não repita em desejos o que já entrou em outro campo.
- Se a mensagem não for sobre imóveis, devolva os critérios atuais sem mudança."""


def _schema(bairros: list[str], cidades: list[str]) -> dict:
    def lista_nomes(nomes: list[str]) -> dict:
        item = {"type": "string", "enum": nomes} if nomes else {"type": "string"}
        return {"type": "array", "items": item}

    return {
        "type": "object",
        "properties": {
            "finalidade": anulavel({"type": "string", "enum": ["venda", "aluguel"]}),
            "tipos": {"type": "array", "items": {"type": "string", "enum": list(TIPOS)}},
            "cidades": lista_nomes(cidades),
            "bairros": lista_nomes(bairros),
            "preco_max": anulavel({"type": "number"}),
            "preco_min": anulavel({"type": "number"}),
            "quartos_min": anulavel({"type": "integer"}),
            "suites_min": anulavel({"type": "integer"}),
            "banheiros_min": anulavel({"type": "integer"}),
            "vagas_min": anulavel({"type": "integer"}),
            "area_min": anulavel({"type": "number"}),
            "caracteristicas": {"type": "array", "items": {"type": "string", "enum": list(CARACTERISTICAS)}},
            "perto_de": {"type": "array", "items": {"type": "string", "enum": list(CATEGORIAS_CONTEXTO)}},
            "desejos": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "finalidade", "tipos", "cidades", "bairros", "preco_max", "preco_min", "quartos_min", "suites_min",
            "banheiros_min", "vagas_min", "area_min", "caracteristicas", "perto_de", "desejos",
        ],
        "additionalProperties": False,
    }


def interpretar(texto: str, anteriores: Criterios, historico: list[str], bairros: list[str], cidades: list[str],
                uso: UsoIA) -> Criterios | None:
    entrada = {
        "criterios_atuais": anteriores.para_dict(),
        "mensagens_anteriores": historico[-6:],
        "nova_mensagem": texto,
        "bairros_disponiveis": bairros,
        "cidades_disponiveis": cidades,
        "codigos_caracteristicas": CARACTERISTICAS,
        "codigos_perto_de": list(CATEGORIAS_CONTEXTO),
    }
    dados = chamar_json(uso, system=_INSTRUCAO, conteudo=json.dumps(entrada, ensure_ascii=False),
                        schema=_schema(bairros, cidades))
    if dados is None:
        return None
    criterios = Criterios.de_dict(dados)
    # A IA só pode citar bairros e cidades que existem na carteira.
    criterios.bairros = [b for b in criterios.bairros if b in bairros]
    criterios.cidades = [c for c in criterios.cidades if c in cidades]
    return criterios
