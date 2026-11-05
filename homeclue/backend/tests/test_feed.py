from pathlib import Path

import pytest

from app.models import Imobiliaria, Imovel, Tarefa
from app.services.feed import baixar
from app.services.feed.parser import FormatoNaoReconhecido, ler
from app.services.feed.sincronizar import SincronizacaoFalhou, sincronizar
from tests.conftest import cadastrar, mudar_plano

DADOS = Path(__file__).parent / "dados"


def test_le_vrsync():
    leitura = ler((DADOS / "vrsync.xml").read_bytes())
    assert leitura.formato.startswith("VRSync")
    assert [i.codigo for i in leitura.imoveis] == ["AP-100", "CA-200"]
    assert leitura.erros == ["Imóvel SEM-PRECO: sem preço"]
    ap, casa = leitura.imoveis
    assert ap.tipo == "apartamento" and ap.finalidade == "venda" and ap.preco == 420_000
    assert ap.condominio == 550 and ap.iptu == 1200 and ap.quartos == 2 and ap.suites == 0 and ap.vagas == 1
    assert ap.fotos[0]["url"].endswith("ap100-1.jpg")  # a principal vem primeiro
    assert ap.video_url == "https://www.youtube.com/watch?v=abc123"
    assert ap.caracteristicas == ["elevador", "academia"] and ap.comodidades == ["Fogão a lenha"]
    assert ap.mostrar_endereco is False and ap.latitude == -22.2819
    assert casa.finalidade == "venda_aluguel" and casa.preco == 750_000 and casa.preco_aluguel == 3_500
    assert set(casa.caracteristicas) == {"piscina", "jardim", "lareira"}
    assert casa.vagas is None  # o feed não informou: fica "não informado", não zero


def test_le_formato_carga():
    leitura = ler((DADOS / "carga.xml").read_bytes())
    assert leitura.formato.startswith("Carga")
    sitio, apto = leitura.imoveis
    assert sitio.tipo == "rural" and sitio.area_terreno == 20_000 and sitio.caracteristicas == ["lareira"]
    assert sitio.fotos == [{"url": "https://fotos.exemplo.com/777-1.jpg", "legenda": ""}]
    assert apto.finalidade == "aluguel" and apto.preco == 1_800


def test_xml_invalido_e_entidades_externas():
    with pytest.raises(FormatoNaoReconhecido):
        ler(b"<isto nao e xml")
    with pytest.raises(FormatoNaoReconhecido):
        ler(b"<root><foo/></root>")
    ataque = b'<?xml version="1.0"?><!DOCTYPE r [<!ENTITY x SYSTEM "file:///etc/passwd">]><Listing>&x;</Listing>'
    with pytest.raises(FormatoNaoReconhecido):
        ler(ataque)


def test_endereco_interno_e_bloqueado():
    for url in ["http://127.0.0.1/feed.xml", "http://localhost/feed.xml", "http://169.254.169.254/latest",
                "ftp://exemplo.com/feed.xml"]:
        with pytest.raises(baixar.FeedInvalido):
            baixar.validar_endereco(url)


def test_sincroniza_atualiza_e_tira_do_ar(client, db):
    cadastrar(client)
    imob = db.query(Imobiliaria).filter(Imobiliaria.nome == "Imob Teste").one()
    resumo = sincronizar(db, imob, (DADOS / "vrsync.xml").read_bytes())
    assert "2 imóveis no ar" in resumo and "2 novos" in resumo and "1 com problema" in resumo
    assert db.query(Tarefa).filter(Tarefa.tipo == "contexto_bairro").count() == 2

    # O feed seguinte não tem mais a casa: ela sai das buscas (sem ser apagada).
    so_ap = (DADOS / "vrsync.xml").read_text().replace("<ListingID>CA-200</ListingID>", "<ListingID>XX</ListingID>")
    sincronizar(db, imob, so_ap.replace("Casa com piscina em Olaria", "Outra").encode())
    casa = db.query(Imovel).filter(Imovel.codigo_referencia == "CA-200").one()
    assert casa.removido_do_feed_em is not None
    # E volta quando reaparece.
    sincronizar(db, imob, (DADOS / "vrsync.xml").read_bytes())
    db.refresh(casa)
    assert casa.removido_do_feed_em is None


def test_feed_vazio_nunca_apaga_o_estoque(client, db):
    cadastrar(client)
    imob = db.query(Imobiliaria).filter(Imobiliaria.nome == "Imob Teste").one()
    sincronizar(db, imob, (DADOS / "vrsync.xml").read_bytes())
    with pytest.raises(SincronizacaoFalhou):
        sincronizar(db, imob, b'<ListingDataFeed><Listings></Listings></ListingDataFeed>')
    assert db.query(Imovel).filter(Imovel.imobiliaria_id == imob.id, Imovel.removido_do_feed_em.is_(None)).count() == 2


def test_limite_do_plano_no_feed(client, db):
    cadastrar(client)
    imob = db.query(Imobiliaria).filter(Imobiliaria.nome == "Imob Teste").one()
    linhas = "".join(
        f"<Imovel><CodigoImovel>{n}</CodigoImovel><TipoImovel>Casa</TipoImovel><Cidade>Nova Friburgo</Cidade>"
        f"<Bairro>Centro</Bairro><PrecoVenda>100000</PrecoVenda></Imovel>" for n in range(40))
    resumo = sincronizar(db, imob, f"<Carga><Imoveis>{linhas}</Imoveis></Carga>".encode())
    assert "30 imóveis no ar" in resumo and "10 ficaram de fora" in resumo


def test_api_do_feed_por_arquivo_e_edicao_restrita(client):
    headers = cadastrar(client)
    resposta = client.post("/api/feed/arquivo", headers=headers,
                           files={"arquivo": ("feed.xml", (DADOS / "vrsync.xml").read_bytes(), "text/xml")})
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["status"] == "ok" and resposta.json()["total"] == 2

    imoveis = client.get("/api/imoveis", headers=headers).json()
    ap = next(i for i in imoveis if i["codigo_referencia"] == "AP-100")
    assert ap["origem"] == "feed"
    # Do feed, o painel só muda o que é da Homeclue (ex.: desativar); o preço continua o do feed.
    dados = {**{k: ap[k] for k in ("titulo", "tipo", "finalidade", "bairro", "cidade")}, "preco": 1, "ativo": False}
    alterado = client.put(f"/api/imoveis/{ap['id']}", headers=headers, json=dados).json()
    assert alterado["preco"] == 420_000 and alterado["ativo"] is False
    assert client.delete(f"/api/imoveis/{ap['id']}", headers=headers).status_code == 400

    ruim = client.post("/api/feed/arquivo", headers=headers, files={"arquivo": ("f.xml", b"<x/>", "text/xml")})
    assert ruim.status_code == 422 and "formato" in ruim.json()["detail"]


def test_configurar_feed_rejeita_rede_interna(client):
    headers = cadastrar(client)
    resposta = client.put("/api/feed", headers=headers, json={"url": "http://127.0.0.1:8000/feed.xml"})
    assert resposta.status_code == 400


def test_corretor_nao_configura_feed(client):
    headers = cadastrar(client)
    mudar_plano("dono@imob.com", "profissional")
    criado = client.post("/api/equipe", headers=headers, json={"nome": "Corretor", "email": "c@imob.com"}).json()
    token = client.post("/api/auth/login", json={"email": "c@imob.com", "senha": criado["senha_temporaria"]}).json()
    headers_corretor = {"Authorization": f"Bearer {token['access_token']}"}
    assert client.put("/api/feed", headers=headers_corretor, json={"url": "https://exemplo.com/feed.xml"}).status_code == 403
