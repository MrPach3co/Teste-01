from tests.conftest import cadastrar


def test_cadastro_cria_imobiliaria_e_dono(client):
    headers = cadastrar(client)
    sessao = client.get("/api/auth/sessao", headers=headers).json()
    assert sessao["usuario"]["papel"] == "dono"
    assert sessao["imobiliaria"]["nome"] == "Imob Teste"
    assert sessao["imobiliaria"]["plano"] == "gratis"
    assert sessao["imobiliaria"]["chave_publica"].startswith("pk_")


def test_cadastro_exige_termos(client):
    resposta = client.post("/api/auth/cadastro", json={
        "nome_imobiliaria": "X", "nome": "Y Z", "email": "a@b.com", "senha": "12345678", "aceitou_termos": False,
    })
    assert resposta.status_code in (400, 422)


def test_email_duplicado(client):
    cadastrar(client)
    resposta = client.post("/api/auth/cadastro", json={
        "nome_imobiliaria": "Outra", "nome": "Outro", "email": "dono@imob.com",
        "senha": "senha-forte-123", "aceitou_termos": True,
    })
    assert resposta.status_code == 409


def test_login_e_senha_errada(client):
    cadastrar(client)
    assert client.post("/api/auth/login", json={"email": "dono@imob.com", "senha": "senha-forte-123"}).status_code == 200
    assert client.post("/api/auth/login", json={"email": "dono@imob.com", "senha": "errada"}).status_code == 401


def test_rotas_do_painel_exigem_login(client):
    assert client.get("/api/imoveis").status_code == 401
    assert client.get("/api/leads").status_code == 401


def test_equipe_respeita_limite_do_plano(client):
    headers = cadastrar(client)
    # Plano Grátis permite 1 usuário (o próprio dono).
    resposta = client.post("/api/equipe", headers=headers, json={"nome": "Corretor", "email": "c@imob.com"})
    assert resposta.status_code == 402


def test_corretor_nao_altera_imobiliaria(client):
    from app.models import Imobiliaria
    from tests.conftest import SessionTeste

    headers = cadastrar(client)
    with SessionTeste() as db:
        imob = db.query(Imobiliaria).filter(Imobiliaria.nome == "Imob Teste").one()
        imob.plano = "pro"
        db.commit()

    criado = client.post("/api/equipe", headers=headers, json={"nome": "Corretor", "email": "c@imob.com"}).json()
    token = client.post("/api/auth/login", json={"email": "c@imob.com", "senha": criado["senha_temporaria"]}).json()
    headers_corretor = {"Authorization": f"Bearer {token['access_token']}"}

    assert client.patch("/api/imobiliaria", headers=headers_corretor, json={"nome": "Hackeada"}).status_code == 403
    assert client.get("/api/imoveis", headers=headers_corretor).status_code == 200


def test_atualizar_imobiliaria(client):
    headers = cadastrar(client)
    resposta = client.patch("/api/imobiliaria", headers=headers, json={"cor_primaria": "#123456", "whatsapp": "+55 48 99999-0000"})
    assert resposta.status_code == 200
    assert resposta.json()["cor_primaria"] == "#123456"
    assert client.patch("/api/imobiliaria", headers=headers, json={"cor_primaria": "vermelho"}).status_code == 422


def test_excluir_conta_do_dono_apaga_imobiliaria(client):
    headers = cadastrar(client)
    assert client.delete("/api/auth/minha-conta", headers=headers).status_code == 204
    assert client.get("/api/auth/sessao", headers=headers).status_code == 401
