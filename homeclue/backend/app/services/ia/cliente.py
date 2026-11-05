"""Cliente da Claude com medição de custo.

Toda chamada passa por aqui e soma tokens e custo em um UsoIA — é isso que
alimenta o "custo de IA por busca" (próximo passo do documento de produto:
medir o custo real antes de definir o preço da assinatura).

Sem ANTHROPIC_API_KEY, `disponivel()` é False e os chamadores usam o plano B
determinístico. Erros de rede, limites e recusas também caem no plano B.
"""

import json
import logging
from dataclasses import dataclass

from anthropic import Anthropic, APIConnectionError, APIStatusError

from app.core.config import obter_settings

logger = logging.getLogger(__name__)

settings = obter_settings()

_cliente: Anthropic | None = (
    Anthropic(api_key=settings.anthropic_api_key, timeout=45.0, max_retries=1)
    if settings.anthropic_api_key
    else None
)

# US$ por milhão de tokens (entrada, saída). Atualize se a tabela da Anthropic mudar.
PRECOS_USD_POR_MTOK: dict[str, tuple[float, float]] = {
    "claude-opus-5-5": (4.00, 20.00),
    "claude-opus-5": (5.00, 25.00),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-sonnet-5": (2.00, 10.00),
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-fable-5-1": (10.00, 50.00),
}


def modelo() -> str:
    return settings.anthropic_modelo


def disponivel() -> bool:
    return _cliente is not None


def custo_usd(modelo_id: str, tokens_entrada: int, tokens_saida: int) -> float:
    preco_entrada, preco_saida = PRECOS_USD_POR_MTOK.get(modelo_id, PRECOS_USD_POR_MTOK["claude-opus-5-5"])
    return (tokens_entrada * preco_entrada + tokens_saida * preco_saida) / 1_000_000


@dataclass
class UsoIA:
    modelo: str | None = None
    tokens_entrada: int = 0
    tokens_saida: int = 0
    custo_usd: float = 0.0
    chamadas: int = 0

    def registrar(self, resposta) -> None:
        uso = getattr(resposta, "usage", None)
        if uso is None:
            return
        entrada = (uso.input_tokens or 0) + (getattr(uso, "cache_read_input_tokens", 0) or 0) \
            + (getattr(uso, "cache_creation_input_tokens", 0) or 0)
        saida = uso.output_tokens or 0
        self.modelo = modelo()
        self.tokens_entrada += entrada
        self.tokens_saida += saida
        self.custo_usd += custo_usd(self.modelo, entrada, saida)
        self.chamadas += 1


def _texto(resposta) -> str | None:
    if resposta.stop_reason in ("refusal", "max_tokens"):
        logger.warning("IA terminou com stop_reason=%s", resposta.stop_reason)
        return None
    return next((b.text for b in resposta.content if b.type == "text"), None)


def _criar(uso: UsoIA, **parametros):
    assert _cliente is not None
    try:
        resposta = _cliente.messages.create(model=modelo(), **parametros)
    except (APIStatusError, APIConnectionError) as erro:
        logger.warning("Falha ao chamar a IA: %s", erro)
        return None
    uso.registrar(resposta)
    return resposta


def chamar_json(uso: UsoIA, *, system: str, conteudo, schema: dict, max_tokens: int = 4000,
                effort: str = "low") -> dict | None:
    """Chamada com saída estruturada (JSON Schema). None = use o plano B."""
    if _cliente is None:
        return None
    resposta = _criar(
        uso,
        max_tokens=max_tokens,
        system=system,
        output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}},
        messages=[{"role": "user", "content": conteudo}],
    )
    if resposta is None:
        return None
    texto = _texto(resposta)
    if texto is None:
        return None
    try:
        dados = json.loads(texto)
    except json.JSONDecodeError:
        logger.warning("IA devolveu JSON inválido")
        return None
    return dados if isinstance(dados, dict) else None


def chamar_texto(uso: UsoIA, *, system: str, conteudo, max_tokens: int = 4000, effort: str = "low") -> str | None:
    if _cliente is None:
        return None
    resposta = _criar(uso, max_tokens=max_tokens, system=system, output_config={"effort": effort},
                      messages=[{"role": "user", "content": conteudo}])
    return _texto(resposta) if resposta is not None else None


def anulavel(schema: dict) -> dict:
    return {"anyOf": [schema, {"type": "null"}]}
