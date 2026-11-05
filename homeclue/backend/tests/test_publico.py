from urllib.parse import parse_qs, urlparse

from app.models import Lead, RegistroBusca
from tests.conftest import IMOVEL_EXEMPLO, cadastrar


def _buscar(client, texto, criterios=None, sessao="s1", turno=1, chave="pk_demo"):
    resposta = client.post(f"/api/publico/{chave}/buscar", json={
        "texto": texto, "sessao": sessao, "turno": turno, "criterios": criterios, "historico": []})
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def test_config_do_widget_demo(client):
    config = client.get("/api/publico/pk_demo/config").json()
    assert config["nome"].startswith("Imobiliária Demonstração")
    assert config["recursos"]["comparador"] and config["recursos"]["rankings"]
    assert config["recursos"]["busca_por_foto"] is False  # sem IA configurada
    assert config["lancamentos"] == 1 and len(config["exemplos"]) >= 3


def test_busca_do_documento_com_match_explicado(client):
    corpo = _buscar(client, "Casa com quintal pra cachorro em Olaria até 700 mil, sala com luz da manhã")
    melhor = corpo["resultados"][0]
    assert melhor["titulo"] == "Casa térrea com quintal e lareira em Olaria"
    pontos = {p["chave"]: p for p in melhor["pontos"]}
    assert pontos["car:pet-friendly"]["status"] == "atende"
    assert pontos["desejo:0"]["status"] == "atende" and "sol da manhã" in pontos["desejo:0"]["evidencia"]
    assert melhor["tem_planta"] and melhor["tem_maquete"]
    assert corpo["resumo"].startswith("Comprar casa em Olaria")
    assert any(r["id"] == "melhor" for r in corpo["rankings"])


def test_conversa_em_turnos(client):
    turno1 = _buscar(client, "quero comprar uma casa em Olaria")
    turno2 = _buscar(client, "e no Cônego? com piscina", criterios=turno1["criterios"], turno=2)
    assert turno2["criterios"]["bairros"] == ["Cônego"] and turno2["criterios"]["tipos"] == ["casa"]
    assert "Piscina" in turno2["entendido"]
    assert turno2["resultados"][0]["bairro"] == "Cônego"


def test_trava_aluguel_que_nao_aceita_animais(client):
    corpo = _buscar(client, "alugar apartamento que aceite cachorro em Braunes")
    braunes = next(r for r in corpo["resultados"] if r["bairro"] == "Braunes")
    pet = next(p for p in braunes["pontos"] if p["chave"] == "car:pet-friendly")
    assert pet["status"] == "nao_atende" and "Não aceita animais" in pet["evidencia"]
    assert all(r["finalidade"] in ("aluguel", "venda_aluguel") for r in corpo["resultados"])


def test_avisa_quando_ninguem_informa(client):
    corpo = _buscar(client, "casa com fogão de pedra sabão")
    assert any("pedra sabão" in aviso for aviso in corpo["avisos"])


def test_praia_pelo_texto_do_anuncio(client):
    corpo = _buscar(client, "casa perto da praia em Rio das Ostras")
    melhor = corpo["resultados"][0]
    assert melhor["titulo"] == "Casa a 300 metros da praia em Costazul"
    praia = next(p for p in melhor["pontos"] if p["chave"] == "car:perto-da-praia")
    assert praia["status"] == "atende" and "300 metros da praia" in praia["evidencia"]


def test_sugestoes_de_continuacao(client):
    assert _buscar(client, "uma casa em Olaria")["sugestoes"] == ["Quero comprar", "Quero alugar"]


def test_whatsapp_da_demo_mostra_previa_e_cria_lead(client, db):
    corpo = _buscar(client, "Casa com quintal pra cachorro em Olaria até 700 mil")
    imovel = corpo["resultados"][0]
    resposta = client.get(f"/api/publico/pk_demo/whatsapp?imovel={imovel['id']}&busca={corpo['busca_id']}&sessao=s1",
                          follow_redirects=False)
    assert resposta.status_code == 200 and "Código Homeclue" in resposta.text
    lead = db.query(Lead).one()
    assert lead.origem == "whatsapp" and lead.nome is None and lead.codigo in resposta.text
    assert lead.resumo_busca.startswith("Comprar casa em Olaria") and lead.match is not None
    # Clicar de novo na mesma sessão não cria outro lead.
    client.get(f"/api/publico/pk_demo/whatsapp?imovel={imovel['id']}&busca={corpo['busca_id']}&sessao=s1",
               follow_redirects=False)
    assert db.query(Lead).count() == 1


def test_whatsapp_de_verdade_vai_para_o_corretor_responsavel(client, db):
    headers = cadastrar(client)
    client.patch("/api/imobiliaria", headers=headers, json={"whatsapp": "(22) 99999-1111"})
    from tests.conftest import mudar_plano
    mudar_plano("dono@imob.com", "profissional")
    corretor = client.post("/api/equipe", headers=headers,
                           json={"nome": "Ana", "email": "ana@imob.com", "whatsapp": "22 98888-2222"}).json()
    imovel = client.post("/api/imoveis", headers=headers,
                         json={**IMOVEL_EXEMPLO, "corretor_id": corretor["usuario"]["id"]}).json()
    chave = client.get("/api/auth/sessao", headers=headers).json()["imobiliaria"]["chave_publica"]
    corpo = _buscar(client, "apartamento com piscina no Centro", chave=chave)
    resposta = client.get(f"/api/publico/{chave}/whatsapp?imovel={imovel['id']}&busca={corpo['busca_id']}",
                          follow_redirects=False)
    assert resposta.status_code == 302
    destino = urlparse(resposta.headers["location"])
    assert destino.netloc == "wa.me" and destino.path == "/5522988882222"
    texto = parse_qs(destino.query)["text"][0]
    assert "Apartamento com piscina" in texto and "O que eu procuro:" in texto and "Código Homeclue:" in texto
    lead = client.get("/api/leads", headers=headers).json()[0]
    assert lead["origem"] == "whatsapp" and lead["corretor_nome"] == "Ana" and lead["codigo"] in texto


def test_lead_pelo_formulario_e_funil_ate_fechar(client):
    headers = cadastrar(client)
    imovel = client.post("/api/imoveis", headers=headers, json=IMOVEL_EXEMPLO).json()
    chave = client.get("/api/auth/sessao", headers=headers).json()["imobiliaria"]["chave_publica"]
    corpo = _buscar(client, "apartamento com piscina", chave=chave)
    resposta = client.post(f"/api/publico/{chave}/leads", json={
        "nome": "Maria", "telefone": "+55 22 99999-1111", "imovel_id": imovel["id"], "busca_id": corpo["busca_id"],
        "aceitou_contato": True})
    assert resposta.status_code == 201, resposta.text
    codigo = resposta.json()["codigo"]

    achado = client.get(f"/api/leads?q=%23{codigo}", headers=headers).json()
    assert len(achado) == 1 and achado[0]["resumo_busca"] and achado[0]["imovel_titulo"] == "Apartamento com piscina"
    lead_id = achado[0]["id"]
    fechado = client.patch(f"/api/leads/{lead_id}", headers=headers, json={"status": "fechado", "valor_negocio": 395000}).json()
    assert fechado["fechado_em"] and fechado["valor_negocio"] == 395000
    metricas = client.get("/api/painel/metricas", headers=headers).json()
    assert metricas["negocios_fechados_mes"] == 1 and metricas["valor_fechado_mes"] == 395000
    assert "Maria" in client.get("/api/leads/exportar.csv", headers=headers).text


def test_lead_exige_contato_e_consentimento(client):
    base = {"nome": "Maria", "aceitou_contato": True}
    assert client.post("/api/publico/pk_demo/leads", json=base).status_code == 422
    assert client.post("/api/publico/pk_demo/leads", json={**base, "email": "m@m.com", "aceitou_contato": False}).status_code == 400


def test_detalhe_registra_visualizacao_e_esconde_endereco(client, db):
    corpo = _buscar(client, "casa em Olaria")
    imovel_id = next(r["id"] for r in corpo["resultados"] if r["tem_planta"])
    detalhe = client.get(f"/api/publico/pk_demo/imoveis/{imovel_id}?sessao=s1").json()
    assert detalhe["endereco"] is None and detalhe["planta"]["comodos"]
    assert detalhe["bairro_info"]["valorizacao"] == "media"
    from app.models import Evento
    assert db.query(Evento).filter(Evento.tipo == "visualizacao").count() == 1


def test_nao_vaza_imovel_de_outra_imobiliaria(client):
    headers = cadastrar(client)
    imovel = client.post("/api/imoveis", headers=headers, json=IMOVEL_EXEMPLO).json()
    assert client.get(f"/api/publico/pk_demo/imoveis/{imovel['id']}").status_code == 404


def test_lancamentos_e_espelho(client):
    lista = client.get("/api/publico/pk_demo/lancamentos").json()
    assert len(lista) == 1 and lista[0]["disponivel"] > 0
    espelho = client.get(f"/api/publico/pk_demo/lancamentos/{lista[0]['id']}").json()
    assert len(espelho["unidades"]) == 32
    vendida = next(u for u in espelho["unidades"] if u["status"] == "vendida")
    assert vendida["preco"] is None  # preço de unidade vendida não é exposto


def test_cota_de_buscas_esgotada(client, monkeypatch):
    from app.services import limites

    monkeypatch.setattr(limites, "contar_buscas_mes", lambda db, imobiliaria_id: 10**9)
    assert client.post("/api/publico/pk_demo/buscar", json={"texto": "casa"}).status_code == 429


def test_registro_guarda_lacunas_para_o_relatorio(client, db):
    _buscar(client, "casa em Olaria com fogão a lenha")
    registro = db.query(RegistroBusca).one()
    assert registro.lacunas and any("Fogão a lenha" in v for v in registro.lacunas.values())
