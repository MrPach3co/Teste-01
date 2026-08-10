"""Interpretação da busca em linguagem natural.

Se ANTHROPIC_API_KEY estiver configurada, usamos um modelo Claude de
verdade (via tool use) para extrair os filtros do pedido do usuário —
entende frases soltas, sinônimos e nuance muito melhor que regex.

Sem a chave, ou se a chamada falhar por qualquer motivo, caímos no motor
de regras determinístico (app.services.matcher) — a busca nunca quebra
por causa da IA, ela só fica mais simples.
"""

from dataclasses import dataclass, field

from anthropic import Anthropic, APIError

from app.core.config import obter_settings
from app.services import matcher

settings = obter_settings()

_cliente: Anthropic | None = Anthropic(api_key=settings.anthropic_api_key) if settings.anthropic_api_key else None

_MODELO = "claude-sonnet-5"

_TAGS_CONHECIDAS = sorted(set(matcher.DICIONARIO_TAGS.values()))

_FERRAMENTA_EXTRACAO = {
    "name": "registrar_filtros_busca",
    "description": (
        "Registra os filtros estruturados que puderam ser extraídos do pedido "
        "em linguagem natural do usuário sobre o imóvel que procura."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "orcamento_maximo": {
                "type": ["number", "null"],
                "description": "Valor máximo em reais que o usuário quer gastar, ou null se não foi mencionado.",
            },
            "quartos": {
                "type": ["integer", "null"],
                "description": "Número de quartos desejado, ou null se não foi mencionado.",
            },
            "tags": {
                "type": "array",
                "items": {"type": "string", "enum": _TAGS_CONHECIDAS},
                "description": "Características desejadas presentes no pedido, restritas a este vocabulário.",
            },
        },
        "required": ["orcamento_maximo", "quartos", "tags"],
    },
}


@dataclass
class ResultadoInterpretacao:
    orcamento: float | None
    quartos: int | None
    tags: set[str] = field(default_factory=set)
    fonte: str = "regras"  # "ia" ou "regras" — o front pode mostrar isso de forma transparente


def interpretar_busca(texto: str) -> ResultadoInterpretacao:
    if _cliente is not None:
        try:
            return _interpretar_com_ia(texto)
        except (APIError, KeyError, StopIteration):
            pass  # qualquer problema com a IA e caímos no plano B, sem quebrar a busca

    texto_normalizado = texto.lower()
    return ResultadoInterpretacao(
        orcamento=matcher.extrair_orcamento(texto_normalizado),
        quartos=matcher.extrair_quartos(texto_normalizado),
        tags=matcher.extrair_tags(texto_normalizado),
        fonte="regras",
    )


def _interpretar_com_ia(texto: str) -> ResultadoInterpretacao:
    assert _cliente is not None

    resposta = _cliente.messages.create(
        model=_MODELO,
        max_tokens=300,
        tools=[_FERRAMENTA_EXTRACAO],
        tool_choice={"type": "tool", "name": "registrar_filtros_busca"},
        messages=[{"role": "user", "content": texto}],
    )

    bloco = next(b for b in resposta.content if b.type == "tool_use")
    dados = bloco.input

    return ResultadoInterpretacao(
        orcamento=dados.get("orcamento_maximo"),
        quartos=dados.get("quartos"),
        tags=set(dados.get("tags") or []),
        fonte="ia",
    )
