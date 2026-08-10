def test_buscar_retorna_ate_tres_resultados_ordenados_por_match(client):
    resposta = client.post("/api/buscar", json={"texto": "casa perto do mar até 2 milhões, 4 quartos"})
    assert resposta.status_code == 200

    corpo = resposta.json()
    assert corpo["fonte"] == "regras"  # sem ANTHROPIC_API_KEY nos testes
    assert 1 <= len(corpo["resultados"]) <= 3

    matches = [item["match"] for item in corpo["resultados"]]
    assert matches == sorted(matches, reverse=True)


def test_buscar_texto_vazio_é_rejeitado(client):
    resposta = client.post("/api/buscar", json={"texto": ""})
    assert resposta.status_code == 422


def test_listar_imoveis(client):
    resposta = client.get("/api/imoveis")
    assert resposta.status_code == 200
    assert len(resposta.json()) == 5
