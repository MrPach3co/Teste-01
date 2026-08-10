def test_cadastro_exige_aceite_de_termos(client):
    resposta = client.post(
        "/api/auth/cadastro",
        json={"email": "semaceite@exemplo.com", "senha": "senhaSegura123", "aceitou_termos": False},
    )
    assert resposta.status_code == 400


def test_fluxo_completo_cadastro_login_me_exclusao(client):
    cadastro = client.post(
        "/api/auth/cadastro",
        json={"email": "fluxo@exemplo.com", "senha": "senhaSegura123", "aceitou_termos": True},
    )
    assert cadastro.status_code == 201
    assert cadastro.json()["email"] == "fluxo@exemplo.com"

    login = client.post(
        "/api/auth/login",
        json={"email": "fluxo@exemplo.com", "senha": "senhaSegura123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    cabecalho = {"Authorization": f"Bearer {token}"}

    eu = client.get("/api/auth/me", headers=cabecalho)
    assert eu.status_code == 200
    assert eu.json()["email"] == "fluxo@exemplo.com"

    dados_exportados = client.get("/api/auth/me/dados", headers=cabecalho)
    assert dados_exportados.status_code == 200
    assert "consentimento_lgpd_texto" in dados_exportados.json()

    exclusao = client.delete("/api/auth/me", headers=cabecalho)
    assert exclusao.status_code == 204

    eu_depois = client.get("/api/auth/me", headers=cabecalho)
    assert eu_depois.status_code == 401


def test_login_com_senha_errada_falha(client):
    client.post(
        "/api/auth/cadastro",
        json={"email": "senhaerrada@exemplo.com", "senha": "senhaSegura123", "aceitou_termos": True},
    )
    login = client.post(
        "/api/auth/login",
        json={"email": "senhaerrada@exemplo.com", "senha": "errada"},
    )
    assert login.status_code == 401


def test_rota_protegida_sem_token_falha(client):
    resposta = client.get("/api/auth/me")
    assert resposta.status_code == 401
