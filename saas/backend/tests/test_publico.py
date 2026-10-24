from tests.conftest import IMOVEL_EXEMPLO, cadastrar


def test_config_do_widget_demo(client):
    resposta = client.get("/api/publico/pk_demo/config")
    assert resposta.status_code == 200
    assert resposta.json()["nome"] == "Imobiliária Demonstração"
    assert len(resposta.json()["exemplos"]) == 3


def test_chave_inexistente(client):
    assert client.get("/api/publico/pk_nao_existe/config").status_code == 404


def test_busca_ranqueia_e_explica(client):
    resposta = client.post("/api/publico/pk_demo/buscar", json={"texto": "Casa com piscina perto da praia até 2 milhões, 4 quartos"})
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["fonte"] == "regras"
    melhor = corpo["resultados"][0]
    assert melhor["titulo"] == "Casa moderna a duas quadras da praia"
    assert "Piscina" in melhor["motivos"]
    assert "Casa" in corpo["entendido"]


def test_busca_de_aluguel_filtra_finalidade(client):
    corpo = client.post("/api/publico/pk_demo/buscar", json={"texto": "quero alugar um studio mobiliado"}).json()
    assert corpo["resultados"]
    assert all(r["finalidade"] == "aluguel" for r in corpo["resultados"])
    assert corpo["resultados"][0]["tipo"] == "studio"


def test_lead_pelo_widget_chega_no_painel(client):
    headers = cadastrar(client)
    imovel = client.post("/api/imoveis", headers=headers, json=IMOVEL_EXEMPLO).json()
    chave = client.get("/api/auth/sessao", headers=headers).json()["imobiliaria"]["chave_publica"]

    client.post(f"/api/publico/{chave}/buscar", json={"texto": "apartamento com piscina"})
    resposta = client.post(f"/api/publico/{chave}/leads", json={
        "nome": "Maria", "telefone": "+55 48 99999-1111", "imovel_id": imovel["id"],
        "busca_texto": "apartamento com piscina", "aceitou_contato": True,
    })
    assert resposta.status_code == 201, resposta.text

    leads = client.get("/api/leads", headers=headers).json()
    assert len(leads) == 1 and leads[0]["imovel_titulo"] == "Apartamento com piscina"

    lead_id = leads[0]["id"]
    atualizado = client.patch(f"/api/leads/{lead_id}", headers=headers, json={"status": "visita", "notas": "Sábado 10h"})
    assert atualizado.json()["status"] == "visita"
    assert client.patch(f"/api/leads/{lead_id}", headers=headers, json={"status": "inventado"}).status_code == 422

    csv = client.get("/api/leads/exportar.csv", headers=headers)
    assert csv.status_code == 200 and "Maria" in csv.text

    metricas = client.get("/api/painel/metricas", headers=headers).json()
    assert metricas["buscas_mes"] == 1 and metricas["leads_mes"] == 1 and metricas["conversao_mes"] == 100.0


def test_lead_exige_contato_e_consentimento(client):
    base = {"nome": "Maria", "aceitou_contato": True}
    assert client.post("/api/publico/pk_demo/leads", json=base).status_code == 422
    assert client.post("/api/publico/pk_demo/leads", json={**base, "email": "m@m.com", "aceitou_contato": False}).status_code == 400


def test_lead_nao_vincula_imovel_de_outra_imobiliaria(client):
    headers_a = cadastrar(client, "a@a.com", "Imob A")
    imovel_a = client.post("/api/imoveis", headers=headers_a, json=IMOVEL_EXEMPLO).json()
    client.post("/api/publico/pk_demo/leads", json={
        "nome": "Intruso", "email": "x@x.com", "imovel_id": imovel_a["id"], "aceitou_contato": True,
    })
    assert client.get("/api/leads", headers=headers_a).json() == []


def test_cota_de_buscas_esgotada(client, monkeypatch):
    from app.services import limites

    monkeypatch.setattr(limites, "contar_buscas_mes", lambda db, imobiliaria_id: 10**9)
    assert client.post("/api/publico/pk_demo/buscar", json={"texto": "casa"}).status_code == 429


def test_planos_e_checkout_sem_stripe(client):
    planos = client.get("/api/assinatura/planos").json()
    assert planos["pagamento_online"] is False
    assert [p["id"] for p in planos["planos"]] == ["gratis", "pro", "escala"]
    headers = cadastrar(client)
    assert client.post("/api/assinatura/checkout?plano=pro", headers=headers).status_code == 503
