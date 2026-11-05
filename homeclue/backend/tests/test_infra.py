import json
from datetime import timedelta

import httpx
import pytest

from app.core.tempo import agora_utc
from app.models import Imobiliaria, Imovel, Tarefa
from app.services import contexto, tarefas
from tests.conftest import IMOVEL_EXEMPLO, cadastrar


def test_fila_executa_repete_e_desiste(db, monkeypatch):
    chamadas = []

    @tarefas.executor("teste_ok")
    def _ok(db_, tarefa):
        chamadas.append(tarefa.id)

    @tarefas.executor("teste_falha")
    def _falha(db_, tarefa):
        raise RuntimeError("deu ruim")

    tarefas.enfileirar(db, "teste_ok")
    tarefas.enfileirar(db, "teste_ok")  # igual e pendente: não duplica
    tarefas.enfileirar(db, "teste_falha")
    assert db.query(Tarefa).count() == 2
    tarefas.processar_pendentes(db)
    assert len(chamadas) == 1
    falha = db.query(Tarefa).filter(Tarefa.tipo == "teste_falha").one()
    assert falha.status == "pendente" and falha.tentativas == 1 and "deu ruim" in falha.erro
    for _ in range(3):
        falha.executar_em = agora_utc() - timedelta(seconds=1)
        db.commit()
        tarefas.processar_pendentes(db)
        db.refresh(falha)
    assert falha.status == "erro" and falha.tentativas == 3


def test_agenda_feeds_vencidos_uma_vez(client, db):
    cadastrar(client)
    imob = db.query(Imobiliaria).filter(Imobiliaria.nome == "Imob Teste").one()
    imob.feed_url = "https://exemplo.com/feed.xml"
    db.commit()
    tarefas.agendar_feeds(db)
    tarefas.agendar_feeds(db)
    assert db.query(Tarefa).filter(Tarefa.tipo == "sincronizar_feed").count() == 1
    db.refresh(imob)
    assert imob.feed_proxima_sincronizacao > agora_utc()


def test_contexto_com_overpass_fora_usa_nominatim(client, db, monkeypatch):
    headers = cadastrar(client)
    imovel = client.post("/api/imoveis", headers=headers, json={**IMOVEL_EXEMPLO, "latitude": -22.28, "longitude": -42.53}).json()

    def overpass_fora(lat, lon):
        raise RuntimeError("Overpass indisponível: teste")

    respostas = {
        "school": [{"lat": "-22.2810", "lon": "-42.5300", "category": "amenity", "type": "school", "name": "Escola Municipal A"}],
        "hospital": [{"lat": "-22.2900", "lon": "-42.5300", "category": "amenity", "type": "hospital", "name": "Hospital B"}],
    }
    monkeypatch.setattr(contexto, "_elementos_overpass", overpass_fora)
    monkeypatch.setattr(contexto, "_nominatim", lambda params: respostas.get(params.get("q"), []))
    tarefas.processar_pendentes(db)
    salvo = db.get(Imovel, imovel["id"])
    escolas = salvo.contexto["categorias"]["escola"]
    assert escolas["total"] == 1 and escolas["mais_proximos"][0]["nome"] == "Escola Municipal A"
    assert 100 < escolas["mais_proximos"][0]["distancia_m"] < 200
    assert salvo.contexto["categorias"]["saude"]["mais_proximos"][0]["nome"] == "Hospital B"


def test_contexto_geocodifica_o_bairro_quando_falta_coordenada(client, db, monkeypatch):
    headers = cadastrar(client)
    client.post("/api/imoveis", headers=headers, json=IMOVEL_EXEMPLO)
    consultas = []

    def nominatim_falso(params):
        consultas.append(params)
        if "viewbox" not in params:
            return [{"lat": "-22.2819", "lon": "-42.5311"}]
        return []

    monkeypatch.setattr(contexto, "_elementos_overpass", lambda lat, lon: [])
    monkeypatch.setattr(contexto, "_nominatim", nominatim_falso)
    tarefas.processar_pendentes(db)
    imovel = db.query(Imovel).filter(Imovel.titulo == IMOVEL_EXEMPLO["titulo"]).one()
    assert imovel.latitude == -22.2819 and imovel.coordenadas_aproximadas
    assert consultas[0]["q"].startswith("Centro, Nova Friburgo")


def test_webhook_stripe_libera_maquete_e_plano(client, db, monkeypatch):
    from app.services import cobranca

    monkeypatch.setattr(cobranca, "validar_webhook", lambda corpo, assinatura: None)
    headers = cadastrar(client)
    imovel = client.post("/api/imoveis", headers=headers, json=IMOVEL_EXEMPLO).json()
    imob = db.query(Imobiliaria).filter(Imobiliaria.nome == "Imob Teste").one()

    def evento(tipo, objeto):
        return client.post("/api/assinatura/webhook", content=json.dumps({"type": tipo, "data": {"object": objeto}}),
                           headers={"stripe-signature": "x"})

    evento("checkout.session.completed", {"client_reference_id": str(imob.id), "customer": "cus_1", "payment_status": "paid",
                                          "metadata": {"tipo": "maquete", "imovel_id": str(imovel["id"])}})
    evento("checkout.session.completed", {"client_reference_id": str(imob.id), "customer": "cus_1", "subscription": "sub_1",
                                          "metadata": {"tipo": "assinatura", "plano": "essencial"}})
    db.refresh(imob)
    assert imob.plano == "essencial" and imob.stripe_customer_id == "cus_1"
    assert db.get(Imovel, imovel["id"]).maquete_liberada
    evento("customer.subscription.deleted", {"customer": "cus_1", "id": "sub_1"})
    db.refresh(imob)
    assert imob.plano == "gratis"


def test_baixar_feed_respeita_limite_e_redirecionamento(monkeypatch):
    from app.services.feed import baixar

    monkeypatch.setattr(baixar.settings, "permitir_feed_rede_privada", True)

    def transporte(request):
        if request.url.path == "/feed":
            return httpx.Response(302, headers={"location": "/feed2.xml"})
        return httpx.Response(200, content=b"<Carga/>")

    cliente_original = httpx.Client

    def cliente_com_transporte(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(transporte)
        return cliente_original(*args, **kwargs)

    monkeypatch.setattr(baixar.httpx, "Client", cliente_com_transporte)
    assert baixar.baixar("https://exemplo.com/feed") == b"<Carga/>"
    monkeypatch.setattr(baixar, "TAMANHO_MAXIMO", 3)
    with pytest.raises(baixar.FeedInvalido):
        baixar.baixar("https://exemplo.com/feed")


def test_cache_atualiza_a_mesma_chave_e_limpa_os_vencidos(db):
    from datetime import timedelta

    from app.models import Cache
    from app.services import cache

    cache.guardar(db, "k", {"a": 1}, timedelta(days=1))
    cache.guardar(db, "k", {"a": 2}, timedelta(days=1))  # upsert: sem erro de chave duplicada
    assert cache.obter(db, "k") == {"a": 2}
    cache.guardar_varios(db, {"velho": {"a": 3}, "outro": {"a": 4}}, timedelta(seconds=-1))
    assert cache.obter(db, "velho") is None and cache.obter_varios(db, ["k", "velho", "outro"]) == {"k": {"a": 2}}
    cache.limpar_expirados(db)
    assert db.get(Cache, "velho") is None and db.get(Cache, "k") is not None


@pytest.mark.parametrize("url, esperada", [
    ("postgres://u:s@h:5432/db", "postgresql+psycopg2://u:s@h:5432/db"),
    ("postgresql://u:s@h:5432/db", "postgresql+psycopg2://u:s@h:5432/db"),  # formato do Railway
    ("postgresql+psycopg2://u:s@h/db", "postgresql+psycopg2://u:s@h/db"),
    ("sqlite:///./homeclue.db", "sqlite:///./homeclue.db"),
])
def test_url_do_banco_usa_o_driver_instalado(url, esperada):
    from app.core.config import Settings

    assert Settings(database_url=url).database_url_normalizada == esperada
