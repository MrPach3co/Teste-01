"""Integração com a Claude (Anthropic).

Dois usos no produto:
1. Interpretar a busca em linguagem natural do visitante do widget.
2. Escrever a descrição de anúncio de um imóvel para o corretor.

Ambos são opcionais: sem ANTHROPIC_API_KEY, ou se a chamada falhar por
qualquer motivo (rede, limite, recusa), caímos no plano B determinístico.
O produto nunca quebra por causa da IA — só fica mais simples.
"""

import json
import logging

from anthropic import Anthropic, APIConnectionError, APIStatusError

from app.core.config import obter_settings
from app.services import interpretador
from app.services.vocabulario import CARACTERISTICAS, TIPOS, caracteristicas_validas

logger = logging.getLogger(__name__)

settings = obter_settings()

_cliente: Anthropic | None = (
    Anthropic(api_key=settings.anthropic_api_key, timeout=20.0, max_retries=1)
    if settings.anthropic_api_key
    else None
)

_MODELO = "claude-opus-5-5"

_INSTRUCAO_BUSCA = (
    "Você converte o pedido de um visitante de site de imobiliária em filtros "
    "estruturados. Preencha apenas o que o pedido diz ou implica claramente; use "
    "null (ou lista vazia) para o resto. Valores em reais. 'Até 2 milhões' é "
    "orçamento máximo de 2000000. Para aluguel, o orçamento é o valor mensal. "
    "Bairros: use somente nomes da lista fornecida, exatamente como escritos."
)


def ia_disponivel() -> bool:
    return _cliente is not None


def _anulavel(schema: dict) -> dict:
    return {"anyOf": [schema, {"type": "null"}]}


def _schema_filtros(bairros_conhecidos: list[str]) -> dict:
    bairros_schema: dict = {"type": "string"}
    if bairros_conhecidos:
        bairros_schema = {"type": "string", "enum": bairros_conhecidos}
    return {
        "type": "object",
        "properties": {
            "orcamento_maximo": _anulavel({"type": "number"}),
            "quartos_minimos": _anulavel({"type": "integer"}),
            "tipo": _anulavel({"type": "string", "enum": list(TIPOS)}),
            "finalidade": _anulavel({"type": "string", "enum": ["venda", "aluguel"]}),
            "bairros": {"type": "array", "items": bairros_schema},
            "caracteristicas": {"type": "array", "items": {"type": "string", "enum": list(CARACTERISTICAS)}},
        },
        "required": ["orcamento_maximo", "quartos_minimos", "tipo", "finalidade", "bairros", "caracteristicas"],
        "additionalProperties": False,
    }


def _texto_da_resposta(resposta) -> str | None:
    if resposta.stop_reason in ("refusal", "max_tokens"):
        return None
    return next((b.text for b in resposta.content if b.type == "text"), None)


def interpretar_busca(texto: str, bairros_conhecidos: list[str]) -> tuple[interpretador.Filtros, str]:
    """Retorna (filtros, fonte) — fonte é "ia" ou "regras"."""
    if _cliente is not None:
        try:
            filtros = _interpretar_com_ia(texto, bairros_conhecidos)
            if filtros is not None:
                return filtros, "ia"
        except (APIStatusError, APIConnectionError, json.JSONDecodeError, KeyError, TypeError) as erro:
            logger.warning("IA indisponível na busca, usando regras: %s", erro)

    return interpretador.interpretar(texto, bairros_conhecidos), "regras"


def _interpretar_com_ia(texto: str, bairros_conhecidos: list[str]) -> interpretador.Filtros | None:
    assert _cliente is not None

    lista_bairros = ", ".join(bairros_conhecidos) or "(nenhum cadastrado)"
    resposta = _cliente.messages.create(
        model=_MODELO,
        max_tokens=4000,
        system=_INSTRUCAO_BUSCA,
        output_config={
            "effort": "low",
            "format": {"type": "json_schema", "schema": _schema_filtros(bairros_conhecidos)},
        },
        messages=[{
            "role": "user",
            "content": f"Bairros disponíveis: {lista_bairros}\n\nPedido do visitante: {texto}",
        }],
    )

    bruto = _texto_da_resposta(resposta)
    if bruto is None:
        return None
    dados = json.loads(bruto)

    return interpretador.Filtros(
        orcamento_maximo=dados["orcamento_maximo"],
        quartos_minimos=dados["quartos_minimos"],
        tipo=dados["tipo"] if dados["tipo"] in TIPOS else None,
        finalidade=dados["finalidade"] if dados["finalidade"] in ("venda", "aluguel") else None,
        bairros=[b for b in dados["bairros"] if b in bairros_conhecidos],
        caracteristicas=caracteristicas_validas(dados["caracteristicas"]),
    )


# --- Descrição de anúncio ---------------------------------------------------

_INSTRUCAO_DESCRICAO = (
    "Você é redator de anúncios imobiliários no Brasil. Escreva uma descrição "
    "de anúncio em português do Brasil, em 2 ou 3 parágrafos curtos, tom "
    "profissional e caloroso, sem exageros nem promessas que os dados não "
    "sustentam. Não invente características que não foram informadas. Não use "
    "markdown, emojis nem título — só o texto corrido do anúncio."
)


def _resumo_imovel(dados: dict) -> str:
    caracteristicas = ", ".join(CARACTERISTICAS.get(c, c) for c in dados.get("caracteristicas", []))
    finalidade = "aluguel" if dados.get("finalidade") == "aluguel" else "venda"
    linhas = [
        f"Título: {dados.get('titulo', '')}",
        f"Tipo: {TIPOS.get(dados.get('tipo', ''), dados.get('tipo', ''))} para {finalidade}",
        f"Local: {dados.get('bairro', '')}, {dados.get('cidade', '')}",
        f"Preço: R$ {dados.get('preco', 0):,.0f}".replace(",", "."),
        f"Quartos: {dados.get('quartos', 0)} · Banheiros: {dados.get('banheiros', 0)} · Vagas: {dados.get('vagas', 0)}",
        f"Área: {dados.get('area_m2', 0):g} m²",
    ]
    if caracteristicas:
        linhas.append(f"Características: {caracteristicas}")
    if dados.get("observacoes"):
        linhas.append(f"Observações do corretor: {dados['observacoes']}")
    return "\n".join(linhas)


def gerar_descricao(dados: dict) -> tuple[str, str]:
    """Retorna (descricao, fonte)."""
    if _cliente is not None:
        try:
            resposta = _cliente.messages.create(
                model=_MODELO,
                max_tokens=4000,
                system=_INSTRUCAO_DESCRICAO,
                output_config={"effort": "low"},
                messages=[{"role": "user", "content": _resumo_imovel(dados)}],
            )
            texto = _texto_da_resposta(resposta)
            if texto:
                return texto.strip(), "ia"
        except (APIStatusError, APIConnectionError) as erro:
            logger.warning("IA indisponível na descrição, usando modelo pronto: %s", erro)

    return _descricao_modelo(dados), "modelo"


def _descricao_modelo(dados: dict) -> str:
    tipo = TIPOS.get(dados.get("tipo", ""), "Imóvel")
    finalidade = "para alugar" if dados.get("finalidade") == "aluguel" else "à venda"
    quartos = dados.get("quartos", 0)
    partes = [
        f"{tipo} {finalidade} em {dados.get('bairro', '')}, {dados.get('cidade', '')}, "
        f"com {dados.get('area_m2', 0):g} m²"
        + (f" e {quartos} quarto{'s' if quartos != 1 else ''}" if quartos else "")
        + "."
    ]
    caracteristicas = [CARACTERISTICAS[c].lower() for c in dados.get("caracteristicas", []) if c in CARACTERISTICAS]
    if caracteristicas:
        partes.append("Destaques: " + ", ".join(caracteristicas) + ".")
    if dados.get("vagas"):
        partes.append(f"Conta com {dados['vagas']} vaga{'s' if dados['vagas'] != 1 else ''} de garagem.")
    partes.append("Agende uma visita e conheça pessoalmente.")
    return " ".join(partes)
