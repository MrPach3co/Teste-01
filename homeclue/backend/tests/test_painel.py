import io

from PIL import Image

from tests.conftest import IMOVEL_EXEMPLO, cadastrar, mudar_plano


def _png(largura=40, altura=30, cor=(200, 30, 30)) -> bytes:
    saida = io.BytesIO()
    Image.new("RGB", (largura, altura), cor).save(saida, format="PNG")
    return saida.getvalue()


def _jpeg_com_metadados() -> bytes:
    imagem = Image.new("RGB", (60, 40), (10, 120, 60))
    exif = Image.Exif()
    exif[0x010F] = "Celular X"  # Make
    exif[0x010E] = "Lat -22.28 Lon -42.53"  # ImageDescription
    saida = io.BytesIO()
    imagem.save(saida, format="JPEG", exif=exif)
    assert len(Image.open(io.BytesIO(saida.getvalue())).getexif()) == 2
    return saida.getvalue()


def test_cadastro_sessao_e_isolamento(client):
    headers_a = cadastrar(client, "a@a.com", "Imob A")
    headers_b = cadastrar(client, "b@b.com", "Imob B")
    sessao = client.get("/api/auth/sessao", headers=headers_a).json()
    assert sessao["usuario"]["papel"] == "dono" and sessao["plano"]["id"] == "gratis" and sessao["admin"] is False
    imovel = client.post("/api/imoveis", headers=headers_a, json=IMOVEL_EXEMPLO).json()
    assert imovel["caracteristicas"] == ["piscina", "academia"]
    assert client.get("/api/imoveis", headers=headers_b).json() == []
    assert client.put(f"/api/imoveis/{imovel['id']}", headers=headers_b, json=IMOVEL_EXEMPLO).status_code == 404


def test_campos_opcionais_ficam_vazios_e_nao_zero(client):
    headers = cadastrar(client)
    dados = {k: v for k, v in IMOVEL_EXEMPLO.items() if k not in ("vagas", "area_m2")}
    imovel = client.post("/api/imoveis", headers=headers, json=dados).json()
    assert imovel["vagas"] is None and imovel["area_m2"] is None


def test_limite_de_imoveis_e_de_usuarios(client):
    headers = cadastrar(client)
    for _ in range(30):
        assert client.post("/api/imoveis", headers=headers, json=IMOVEL_EXEMPLO).status_code == 201
    assert client.post("/api/imoveis", headers=headers, json=IMOVEL_EXEMPLO).status_code == 402
    assert client.post("/api/equipe", headers=headers, json={"nome": "Carlos", "email": "c@c.com"}).status_code == 402


def test_logo_tira_metadados_e_e_servida_com_seguranca(client):
    headers = cadastrar(client)
    resposta = client.post("/api/imobiliaria/logo", headers=headers, files={"arquivo": ("logo.jpg", _jpeg_com_metadados(), "image/jpeg")})
    assert resposta.status_code == 200, resposta.text
    url = resposta.json()["logo_url"]
    servida = client.get(url)
    assert servida.status_code == 200 and servida.headers["x-content-type-options"] == "nosniff"
    assert len(Image.open(io.BytesIO(servida.content)).getexif()) == 0  # metadados removidos
    falso = client.post("/api/imobiliaria/logo", headers=headers,
                        files={"arquivo": ("x.png", b"<svg onload=alert(1)>", "image/png")})
    assert falso.status_code == 400


def test_planta_so_no_premium_e_validada(client):
    headers = cadastrar(client)
    imovel = client.post("/api/imoveis", headers=headers, json=IMOVEL_EXEMPLO).json()
    planta = {"imagem": None, "comodos": [{"id": "s", "tipo": "sala", "x": 0.1, "y": 0.1, "w": 0.3, "h": 0.3}]}
    assert client.put(f"/api/imoveis/{imovel['id']}/planta", headers=headers, json=planta).status_code == 402
    mudar_plano("dono@imob.com", "premium")
    enviada = client.post(f"/api/imoveis/{imovel['id']}/planta/imagem", headers=headers,
                          files={"arquivo": ("planta.png", _png(400, 300), "image/png")}).json()
    planta["imagem"] = enviada["url"]
    salvo = client.put(f"/api/imoveis/{imovel['id']}/planta", headers=headers, json=planta)
    assert salvo.status_code == 200 and salvo.json()["planta"]["comodos"][0]["tipo"] == "sala"
    fora = {"imagem": enviada["url"], "comodos": [{"id": "s", "tipo": "sala", "x": 0.9, "y": 0.1, "w": 0.3, "h": 0.3}]}
    assert client.put(f"/api/imoveis/{imovel['id']}/planta", headers=headers, json=fora).status_code == 422


def test_foto_de_outra_imobiliaria_nao_pode_ser_usada(client):
    headers_a = cadastrar(client, "a@a.com", "Imob A")
    headers_b = cadastrar(client, "b@b.com", "Imob B")
    imovel_a = client.post("/api/imoveis", headers=headers_a, json=IMOVEL_EXEMPLO).json()
    foto = client.post(f"/api/imoveis/{imovel_a['id']}/fotos", headers=headers_a,
                       files={"arquivo": ("f.png", _png(), "image/png")}).json()
    dados = {**IMOVEL_EXEMPLO, "fotos": [{"url": foto["url"]}]}
    assert client.post("/api/imoveis", headers=headers_b, json=dados).status_code == 400
    assert client.post("/api/imoveis", headers=headers_a, json=dados).status_code == 201


def test_metricas_mais_vistos_e_demanda(client):
    headers = cadastrar(client)
    imovel = client.post("/api/imoveis", headers=headers, json=IMOVEL_EXEMPLO).json()
    chave = client.get("/api/auth/sessao", headers=headers).json()["imobiliaria"]["chave_publica"]
    for i, texto in enumerate(["casa em Olaria com lareira até 300 mil", "apartamento com piscina no Centro",
                               "casa em Olaria com lareira até 300 mil"]):
        client.post(f"/api/publico/{chave}/buscar", json={"texto": texto, "sessao": f"s{i}"})
    client.get(f"/api/publico/{chave}/imoveis/{imovel['id']}")
    metricas = client.get("/api/painel/metricas", headers=headers).json()
    assert metricas["buscas_mes"] == 3 and metricas["conversas_mes"] == 3
    assert metricas["mais_vistos"][0]["imovel_id"] == imovel["id"] and metricas["mais_vistos"][0]["visualizacoes"] == 1

    demanda = client.get("/api/painel/demanda", headers=headers).json()
    assert demanda["conversas"] == 3
    assert {"nome": "Lareira", "buscas": 2} in demanda["itens"]
    assert {"nome": "Lareira", "buscas": 2} in demanda["pedidos_sem_oferta"]
    assert demanda["nao_encontrado"][0]["buscas"] == 2

    qualidade = client.get("/api/painel/qualidade", headers=headers).json()
    assert qualidade[0]["imovel_id"] == imovel["id"]
    assert any("Sem fotos" in p for p in qualidade[0]["problemas"])


def test_bairros_e_ranking_de_valorizacao(client):
    headers = cadastrar(client)
    client.post("/api/imoveis", headers=headers, json=IMOVEL_EXEMPLO)
    resposta = client.put("/api/bairros/Centro", headers=headers,
                          json={"descricao": "Tudo a pé.", "valorizacao": "alta", "valorizacao_justificativa": "obras do novo parque"})
    assert resposta.status_code == 200 and resposta.json()["imoveis"] == 1
    chave = client.get("/api/auth/sessao", headers=headers).json()["imobiliaria"]["chave_publica"]
    corpo = client.post(f"/api/publico/{chave}/buscar", json={"texto": "apartamento no Centro"}).json()
    valorizacao = next(r for r in corpo["rankings"] if r["id"] == "valorizacao")
    assert "Segundo a imobiliária" in valorizacao["itens"][0]["motivo"]


def test_admin_ve_custo_por_cliente(client):
    headers = cadastrar(client, "dono@homeclue.com.br", "Homeclue")
    resumo = client.get("/api/admin/resumo", headers=headers).json()
    assert resumo["totais"]["clientes"] >= 2
    outro = cadastrar(client, "x@x.com", "Outra")
    assert client.get("/api/admin/resumo", headers=outro).status_code == 403


def test_excluir_conta_do_dono_apaga_tudo(client):
    headers = cadastrar(client)
    client.post("/api/imoveis", headers=headers, json=IMOVEL_EXEMPLO)
    assert client.delete("/api/auth/minha-conta", headers=headers).status_code == 204
    assert client.get("/api/auth/sessao", headers=headers).status_code == 401


def test_lancamento_premium_grade_e_status(client):
    headers = cadastrar(client)
    dados = {"nome": "Residencial X", "bairro": "Centro", "cidade": "Nova Friburgo",
             "torres": [{"nome": "A", "andares": 3, "unidades_por_andar": 2}]}
    assert client.post("/api/lancamentos", headers=headers, json=dados).status_code == 402
    mudar_plano("dono@imob.com", "premium")
    emp = client.post("/api/lancamentos", headers=headers, json=dados).json()
    assert len(emp["unidades"]) == 6 and {u["codigo"] for u in emp["unidades"]} == {"101", "102", "201", "202", "301", "302"}
    alvo = emp["unidades"][0]["id"]
    emp = client.put(f"/api/lancamentos/{emp['id']}/unidades", headers=headers,
                     json=[{"id": alvo, "status": "vendida", "preco": 350000}]).json()
    assert next(u for u in emp["unidades"] if u["id"] == alvo)["status"] == "vendida"
    # Diminuir a torre mantém o que já foi preenchido nas unidades que continuam.
    menor = {**dados, "torres": [{"nome": "A", "andares": 2, "unidades_por_andar": 2}]}
    emp = client.put(f"/api/lancamentos/{emp['id']}", headers=headers, json=menor).json()
    assert len(emp["unidades"]) == 4 and next(u for u in emp["unidades"] if u["id"] == alvo)["preco"] == 350000
    csv = "torre;unidade;status;preco;area_m2\nA;201;reservada;410.000,00;95,5\n"
    emp = client.post(f"/api/lancamentos/{emp['id']}/unidades/importar", headers=headers,
                      files={"arquivo": ("u.csv", csv.encode(), "text/csv")}).json()
    u201 = next(u for u in emp["unidades"] if u["codigo"] == "201")
    assert u201["status"] == "reservada" and u201["preco"] == 410000 and u201["area_m2"] == 95.5


def test_email_nao_diferencia_maiusculas(client):
    cadastrar(client, "Ana.Souza@Imob.com.br")
    login = client.post("/api/auth/login", json={"email": " ana.souza@imob.com.br", "senha": "senha-forte-123"})
    assert login.status_code == 200
    repetido = client.post("/api/auth/cadastro", json={
        "nome_imobiliaria": "Outra", "nome": "Ana", "email": "ANA.SOUZA@imob.com.br", "senha": "senha-forte-123",
        "aceitou_termos": True,
    })
    assert repetido.status_code == 409


def _stripe_falso(monkeypatch, erro=None):
    from types import SimpleNamespace

    from app.services import cobranca

    canceladas = []

    def cancelar(assinatura_id):
        if erro is not None:
            raise erro
        canceladas.append(assinatura_id)

    cliente = SimpleNamespace(v1=SimpleNamespace(subscriptions=SimpleNamespace(cancel=cancelar)))
    monkeypatch.setattr(cobranca, "_cliente", lambda: cliente)
    return canceladas


def _com_assinatura(db, assinatura_id="sub_123"):
    from app.models import Usuario

    dono = db.query(Usuario).filter(Usuario.email == "dono@imob.com").one()
    dono.imobiliaria.stripe_subscription_id = assinatura_id
    db.commit()


def test_excluir_conta_cancela_a_assinatura(client, db, monkeypatch):
    import stripe

    headers = cadastrar(client)
    _com_assinatura(db)
    _stripe_falso(monkeypatch, stripe.APIConnectionError("sem rede"))
    falhou = client.delete("/api/auth/minha-conta", headers=headers)
    assert falhou.status_code == 502  # sem cancelar a cobrança, a conta não some
    assert client.get("/api/auth/sessao", headers=headers).status_code == 200

    canceladas = _stripe_falso(monkeypatch)
    assert client.delete("/api/auth/minha-conta", headers=headers).status_code == 204
    assert canceladas == ["sub_123"]


def test_excluir_conta_com_assinatura_ja_cancelada(client, db, monkeypatch):
    import stripe

    headers = cadastrar(client)
    _com_assinatura(db)
    _stripe_falso(monkeypatch, stripe.InvalidRequestError("No such subscription: 'sub_123'", "id"))
    assert client.delete("/api/auth/minha-conta", headers=headers).status_code == 204
