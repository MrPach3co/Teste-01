"""IA com cliente falso: confere que a integração usa saída estruturada e que
a trava contra invenção derruba citações que não estão no anúncio."""

import json
from types import SimpleNamespace

import pytest

from app.services.busca.avaliacao import ImovelBusca
from app.services.busca.criterios import Criterios
from app.services.ia import cliente, interpretacao, verificacao


class _ClienteFalso:
    def __init__(self, *respostas, stop_reason="end_turn"):
        self.chamadas: list[dict] = []
        self._respostas = list(respostas)
        self._stop = stop_reason
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.chamadas.append(kwargs)
        texto = self._respostas.pop(0)
        if callable(texto):
            texto = texto(kwargs)
        return SimpleNamespace(stop_reason=self._stop, content=[SimpleNamespace(type="text", text=texto)],
                               usage=SimpleNamespace(input_tokens=1000, output_tokens=200))


@pytest.fixture
def falso(monkeypatch):
    def instalar(*respostas, stop_reason="end_turn"):
        cliente_falso = _ClienteFalso(*respostas, stop_reason=stop_reason)
        monkeypatch.setattr(cliente, "_cliente", cliente_falso)
        return cliente_falso
    return instalar


def test_interpretacao_valida_o_que_a_ia_devolve(falso):
    c = falso(json.dumps({
        "finalidade": "venda", "tipos": ["casa"], "cidades": [], "bairros": ["Olaria", "Inventado"],
        "preco_max": 600000, "preco_min": None, "quartos_min": 3, "suites_min": None, "banheiros_min": None,
        "vagas_min": None, "area_min": None, "caracteristicas": ["jardim", "nao-existe"], "perto_de": ["escola"],
        "desejos": ["sala com luz da manhã"],
    }))
    uso = cliente.UsoIA()
    criterios = interpretacao.interpretar("casa...", Criterios(), [], ["Olaria", "Centro"], ["Nova Friburgo"], uso)
    assert criterios.bairros == ["Olaria"] and criterios.caracteristicas == ["jardim"]
    chamada = c.chamadas[0]
    assert chamada["model"] == "claude-opus-5-5"
    assert chamada["output_config"]["format"]["type"] == "json_schema" and chamada["output_config"]["effort"] == "low"
    assert "tool_choice" not in chamada
    assert uso.tokens_entrada == 1000 and uso.custo_usd == pytest.approx((1000 * 4 + 200 * 20) / 1_000_000)


def test_trava_descarta_citacao_inventada(falso):
    falso(json.dumps({"avaliacoes": [
        {"imovel_id": 1, "pedido": 0, "status": "atende", "trecho": "sala com janelas para o nascente"},
        {"imovel_id": 2, "pedido": 0, "status": "atende", "trecho": "sala ensolarada pela manhã"},  # não existe
        {"imovel_id": 99, "pedido": 0, "status": "atende", "trecho": "qualquer"},  # imóvel que não foi enviado
    ]}))
    imoveis = [
        ImovelBusca(id=1, titulo="A", tipo="casa", finalidade="venda", preco=1, preco_aluguel=None, bairro="X",
                    cidade="Y", descricao="Casa com sala com janelas para o nascente."),
        ImovelBusca(id=2, titulo="B", tipo="casa", finalidade="venda", preco=1, preco_aluguel=None, bairro="X",
                    cidade="Y", descricao="Casa com sala ampla."),
    ]
    conferidas = verificacao.verificar_desejos(["sala com luz da manhã"], imoveis, cliente.UsoIA())
    assert conferidas == {(1, 0): ("atende", "sala com janelas para o nascente", "descricao")}


def test_recusa_ou_json_quebrado_caem_nas_regras(falso, client):
    falso("isto não é json")
    corpo = client.post("/api/publico/pk_demo/buscar", json={"texto": "casa com lareira"}).json()
    assert corpo["fonte"] == "regras" and "Lareira" in corpo["entendido"]
    falso("{}", stop_reason="refusal")
    corpo = client.post("/api/publico/pk_demo/buscar", json={"texto": "casa com piscina"}).json()
    assert corpo["fonte"] == "regras"


def test_busca_com_ia_registra_custo_e_usa_cache(falso, client, db):
    resposta_ia = json.dumps({
        "finalidade": None, "tipos": ["casa"], "cidades": [], "bairros": [], "preco_max": None, "preco_min": None,
        "quartos_min": None, "suites_min": None, "banheiros_min": None, "vagas_min": None, "area_min": None,
        "caracteristicas": ["lareira"], "perto_de": [], "desejos": [],
    })
    c = falso(resposta_ia)
    primeira = client.post("/api/publico/pk_demo/buscar", json={"texto": "uma casa com lareira"}).json()
    assert primeira["fonte"] == "ia"
    segunda = client.post("/api/publico/pk_demo/buscar", json={"texto": "Uma casa com lareira"}).json()
    assert segunda["fonte"] == "ia" and len(c.chamadas) == 1  # a segunda veio do cache, sem custo
    from app.models import RegistroBusca
    custos = [r.custo_usd for r in db.query(RegistroBusca).order_by(RegistroBusca.id)]
    assert custos[0] > 0 and custos[1] == 0


def _tudo_nao_informado(chamada: dict) -> str:
    """Resposta falsa da conferência: responde todos os pares que recebeu."""
    entrada = json.loads(chamada["messages"][0]["content"])
    return json.dumps({"avaliacoes": [
        {"imovel_id": a["id"], "pedido": p["indice"], "status": "nao_informado", "trecho": ""}
        for a in entrada["anuncios"] for p in entrada["pedidos"]
    ]})


def test_conferencia_ja_feita_nao_e_paga_de_novo(falso, db):
    c = falso(_tudo_nao_informado, _tudo_nao_informado)
    imoveis = [ImovelBusca(id=n, titulo=f"Casa {n}", tipo="casa", finalidade="venda", preco=1, preco_aluguel=None,
                           bairro="X", cidade="Y", descricao=f"Casa número {n}, sala ampla.") for n in (1, 2, 3)]
    verificacao.verificar_desejos(["sala com luz da manhã"], imoveis[:2], cliente.UsoIA(), db)
    verificacao.verificar_desejos(["sala com luz da manhã"], imoveis, cliente.UsoIA(), db)
    assert len(c.chamadas) == 2
    assert [a["id"] for a in json.loads(c.chamadas[1]["messages"][0]["content"])["anuncios"]] == [3]
    verificacao.verificar_desejos(["Sala com luz da manhã"], imoveis, cliente.UsoIA(), db)
    assert len(c.chamadas) == 2  # tudo já conferido: custo zero

    imoveis[0].descricao = "Casa número 1, sala com janelas para o nascente."  # anúncio editado: confere de novo
    c = falso(json.dumps({"avaliacoes": [
        {"imovel_id": 1, "pedido": 0, "status": "atende", "trecho": "sala com janelas para o nascente"}]}))
    conferidas = verificacao.verificar_desejos(["sala com luz da manhã"], imoveis, cliente.UsoIA(), db)
    assert conferidas == {(1, 0): ("atende", "sala com janelas para o nascente", "descricao")}
    assert [a["id"] for a in json.loads(c.chamadas[0]["messages"][0]["content"])["anuncios"]] == [1]


def test_falha_da_ia_nao_entra_no_cache(falso, db):
    imoveis = [ImovelBusca(id=1, titulo="Casa", tipo="casa", finalidade="venda", preco=1, preco_aluguel=None,
                           bairro="X", cidade="Y", descricao="Casa com sala ampla.")]
    falso("isto não é json")
    assert verificacao.verificar_desejos(["rua tranquila"], imoveis, cliente.UsoIA(), db) == {}
    c = falso(_tudo_nao_informado)
    verificacao.verificar_desejos(["rua tranquila"], imoveis, cliente.UsoIA(), db)
    assert len(c.chamadas) == 1  # perguntou de novo: a falha anterior não foi guardada


def test_busca_repetida_com_pedido_livre_sai_do_cache(falso, client):
    resposta_ia = json.dumps({
        "finalidade": None, "tipos": ["casa"], "cidades": [], "bairros": [], "preco_max": None, "preco_min": None,
        "quartos_min": None, "suites_min": None, "banheiros_min": None, "vagas_min": None, "area_min": None,
        "caracteristicas": [], "perto_de": [], "desejos": ["sala com luz da manhã"],
    })
    c = falso(resposta_ia, _tudo_nao_informado)
    client.post("/api/publico/pk_demo/buscar", json={"texto": "casa com sala com luz da manhã"})
    assert len(c.chamadas) == 2  # interpretação + conferência dos pedidos livres
    client.post("/api/publico/pk_demo/buscar", json={"texto": "Casa com sala com luz da manhã"})
    assert len(c.chamadas) == 2  # as duas vieram do cache
