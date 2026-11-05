from tests.conftest import IMOVEL_EXEMPLO, cadastrar


def test_crud_de_imovel(client):
    headers = cadastrar(client)
    criado = client.post("/api/imoveis", headers=headers, json=IMOVEL_EXEMPLO)
    assert criado.status_code == 201, criado.text
    imovel = criado.json()
    assert imovel["caracteristicas"] == ["piscina", "academia"]  # slug desconhecido descartado

    alterado = {**IMOVEL_EXEMPLO, "preco": 750000}
    assert client.put(f"/api/imoveis/{imovel['id']}", headers=headers, json=alterado).json()["preco"] == 750000
    assert len(client.get("/api/imoveis", headers=headers).json()) == 1
    assert client.delete(f"/api/imoveis/{imovel['id']}", headers=headers).status_code == 204
    assert client.get("/api/imoveis", headers=headers).json() == []


def test_tipo_invalido(client):
    headers = cadastrar(client)
    assert client.post("/api/imoveis", headers=headers, json={**IMOVEL_EXEMPLO, "tipo": "castelo"}).status_code == 422


def test_isolamento_entre_imobiliarias(client):
    headers_a = cadastrar(client, "a@a.com", "Imob A")
    headers_b = cadastrar(client, "b@b.com", "Imob B")
    imovel = client.post("/api/imoveis", headers=headers_a, json=IMOVEL_EXEMPLO).json()

    assert client.get("/api/imoveis", headers=headers_b).json() == []
    assert client.put(f"/api/imoveis/{imovel['id']}", headers=headers_b, json=IMOVEL_EXEMPLO).status_code == 404
    assert client.delete(f"/api/imoveis/{imovel['id']}", headers=headers_b).status_code == 404


def test_limite_de_imoveis_do_plano_gratis(client):
    headers = cadastrar(client)
    for _ in range(15):
        assert client.post("/api/imoveis", headers=headers, json=IMOVEL_EXEMPLO).status_code == 201
    assert client.post("/api/imoveis", headers=headers, json=IMOVEL_EXEMPLO).status_code == 402


def test_importar_csv_com_ponto_e_virgula(client):
    headers = cadastrar(client)
    csv = (
        "titulo;tipo;finalidade;bairro;cidade;preco;quartos;caracteristicas\n"
        "Casa boa;casa;venda;Lagoa;Florianópolis;1.200.000;3;piscina|jardim\n"
        "Sem tipo;;venda;Lagoa;Florianópolis;100;1;\n"
    )
    resposta = client.post(
        "/api/imoveis/importar", headers=headers,
        files={"arquivo": ("imoveis.csv", csv.encode("utf-8"), "text/csv")},
    )
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert corpo["importados"] == 1
    assert len(corpo["erros"]) == 1 and "Linha 3" in corpo["erros"][0]
    imovel = client.get("/api/imoveis", headers=headers).json()[0]
    assert imovel["preco"] == 1_200_000 and imovel["caracteristicas"] == ["piscina", "jardim"]


def test_gerar_descricao_sem_ia_usa_modelo(client):
    headers = cadastrar(client)
    resposta = client.post("/api/imoveis/gerar-descricao", headers=headers, json=IMOVEL_EXEMPLO)
    assert resposta.status_code == 200
    assert resposta.json()["fonte"] == "modelo"
    assert "Centro" in resposta.json()["descricao"]
