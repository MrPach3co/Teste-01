"""Testa a integração com a Claude usando um cliente falso — sem rede."""

import json
from types import SimpleNamespace

from app.services import ia


class _ClienteFalso:
    def __init__(self, texto: str, stop_reason: str = "end_turn"):
        self.chamadas: list[dict] = []
        self._resposta = SimpleNamespace(
            stop_reason=stop_reason,
            content=[SimpleNamespace(type="text", text=texto)],
        )
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.chamadas.append(kwargs)
        return self._resposta


def test_busca_com_ia_usa_saida_estruturada(monkeypatch):
    falso = _ClienteFalso(json.dumps({
        "orcamento_maximo": 900000, "quartos_minimos": 2, "tipo": "apartamento", "finalidade": "venda",
        "bairros": ["Botafogo", "Inventado"], "caracteristicas": ["perto-metro", "nao-existe"],
    }))
    monkeypatch.setattr(ia, "_cliente", falso)

    filtros, fonte = ia.interpretar_busca("apê 2 quartos perto do metrô em Botafogo até 900 mil", ["Botafogo", "Tijuca"])

    assert fonte == "ia"
    assert filtros.bairros == ["Botafogo"]  # bairro fora da lista descartado
    assert filtros.caracteristicas == ["perto-metro"]  # slug desconhecido descartado
    chamada = falso.chamadas[0]
    assert chamada["model"] == "claude-opus-5-5"
    assert chamada["output_config"]["format"]["type"] == "json_schema"
    assert "tool_choice" not in chamada


def test_recusa_da_ia_cai_nas_regras(monkeypatch):
    monkeypatch.setattr(ia, "_cliente", _ClienteFalso("", stop_reason="refusal"))
    filtros, fonte = ia.interpretar_busca("casa com piscina", [])
    assert fonte == "regras"
    assert filtros.tipo == "casa" and filtros.caracteristicas == ["piscina"]


def test_json_invalido_cai_nas_regras(monkeypatch):
    monkeypatch.setattr(ia, "_cliente", _ClienteFalso("isso não é json"))
    assert ia.interpretar_busca("casa", [])[1] == "regras"


def test_descricao_com_ia(monkeypatch):
    monkeypatch.setattr(ia, "_cliente", _ClienteFalso("  Lindo apartamento.  "))
    assert ia.gerar_descricao({"tipo": "apartamento", "bairro": "Centro"}) == ("Lindo apartamento.", "ia")
