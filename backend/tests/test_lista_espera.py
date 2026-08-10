def test_entrar_na_lista_exige_consentimento(client):
    resposta = client.post(
        "/api/lista-espera",
        json={"email": "semconsentimento@exemplo.com", "aceitou_termos": False},
    )
    assert resposta.status_code == 400


def test_entrar_na_lista_com_consentimento(client):
    resposta = client.post(
        "/api/lista-espera",
        json={"email": "comconsentimento@exemplo.com", "aceitou_termos": True},
    )
    assert resposta.status_code == 201
    assert resposta.json()["email"] == "comconsentimento@exemplo.com"


def test_entrar_na_lista_duas_vezes_nao_duplica(client):
    payload = {"email": "duplicado@exemplo.com", "aceitou_termos": True}
    primeira = client.post("/api/lista-espera", json=payload)
    segunda = client.post("/api/lista-espera", json=payload)
    assert primeira.status_code == 201
    assert segunda.status_code == 201  # idempotente: devolve a entrada existente
