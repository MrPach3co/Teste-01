"""E-mail: "esqueci minha senha" (link de uso único), sessões que caem quando a
senha muda, aviso de lead novo e envio por SMTP."""

import re
from datetime import timedelta

import pytest

from app.core import security
from app.models import Tarefa
from app.services import email, tarefas
from tests.conftest import IMOVEL_EXEMPLO, cadastrar


@pytest.fixture
def caixa(monkeypatch):
    """Captura os e-mails em vez de enviar."""
    enviados: list[dict] = []

    def falso(para, assunto, texto, responder_para=None):
        enviados.append({"para": para, "assunto": assunto, "texto": texto, "responder_para": responder_para})
        return True

    monkeypatch.setattr(email, "enviar", falso)
    return enviados


def _processar_emails(db) -> None:
    """Roda só as tarefas de e-mail (as de contexto do bairro iriam à internet)."""
    db.query(Tarefa).filter(Tarefa.tipo.not_in(["email_redefinir_senha", "avisar_lead"])).delete()
    db.commit()
    tarefas.processar_pendentes(db)


def _link(texto: str) -> str:
    return re.search(r"#redefinir=(\S+)", texto).group(1)


def test_esqueci_senha_nao_revela_quem_tem_conta(client, db, caixa):
    cadastrar(client, "ana@imob.com")
    sem_conta = client.post("/api/auth/esqueci-senha", json={"email": "ninguem@imob.com"})
    com_conta = client.post("/api/auth/esqueci-senha", json={"email": "ANA@imob.com"})
    assert sem_conta.status_code == com_conta.status_code == 202 and sem_conta.json() == com_conta.json()
    client.post("/api/auth/esqueci-senha", json={"email": "ana@imob.com"})  # repetido em 2 minutos: não manda de novo
    assert db.query(Tarefa).filter(Tarefa.tipo == "email_redefinir_senha").count() == 1
    _processar_emails(db)
    assert len(caixa) == 1 and caixa[0]["para"] == "ana@imob.com" and "1 hora" in caixa[0]["texto"]


def test_link_de_redefinicao_e_de_uso_unico_e_derruba_sessoes(client, db, caixa):
    sessao_antiga = cadastrar(client, "ana@imob.com")
    client.post("/api/auth/esqueci-senha", json={"email": "ana@imob.com"})
    _processar_emails(db)
    token = _link(caixa[0]["texto"])

    # O link não serve como token de sessão.
    assert client.get("/api/auth/sessao", headers={"Authorization": f"Bearer {token}"}).status_code == 401

    nova = client.post("/api/auth/redefinir-senha", json={"token": token, "nova_senha": "outra-senha-123"})
    assert nova.status_code == 200
    assert client.get("/api/auth/sessao", headers={"Authorization": f"Bearer {nova.json()['access_token']}"}).status_code == 200
    assert client.get("/api/auth/sessao", headers=sessao_antiga).status_code == 401  # quem estava logado sai
    assert client.post("/api/auth/login", json={"email": "ana@imob.com", "senha": "outra-senha-123"}).status_code == 200

    de_novo = client.post("/api/auth/redefinir-senha", json={"token": token, "nova_senha": "mais-uma-123"})
    assert de_novo.status_code == 400  # uso único


def test_link_vencido_ou_falso_nao_vale(client, db, monkeypatch):
    from app.models import Usuario

    cadastrar(client, "ana@imob.com")
    usuario = db.query(Usuario).filter(Usuario.email == "ana@imob.com").one()
    monkeypatch.setattr(security, "VALIDADE_REDEFINICAO", timedelta(seconds=-1))
    vencido = security.criar_token_redefinicao(usuario)
    assert client.post("/api/auth/redefinir-senha", json={"token": vencido, "nova_senha": "outra-senha-123"}).status_code == 400
    sessao = security.token_de_sessao(usuario)  # token de sessão não serve como link
    assert client.post("/api/auth/redefinir-senha", json={"token": sessao, "nova_senha": "outra-senha-123"}).status_code == 400


def test_trocar_senha_mantem_este_aparelho_e_derruba_os_outros(client):
    outro_aparelho = cadastrar(client, "ana@imob.com")
    este = client.post("/api/auth/login", json={"email": "ana@imob.com", "senha": "senha-forte-123"}).json()
    headers = {"Authorization": f"Bearer {este['access_token']}"}
    resposta = client.post("/api/auth/trocar-senha", headers=headers,
                           json={"senha_atual": "senha-forte-123", "nova_senha": "nova-senha-456"})
    assert resposta.status_code == 200
    novo = {"Authorization": f"Bearer {resposta.json()['access_token']}"}
    assert client.get("/api/auth/sessao", headers=novo).status_code == 200
    assert client.get("/api/auth/sessao", headers=outro_aparelho).status_code == 401


def test_lead_do_formulario_avisa_por_email(client, db, caixa):
    headers = cadastrar(client, "dono@imob.com")
    imovel = client.post("/api/imoveis", headers=headers, json=IMOVEL_EXEMPLO).json()
    chave = client.get("/api/auth/sessao", headers=headers).json()["imobiliaria"]["chave_publica"]
    busca = client.post(f"/api/publico/{chave}/buscar", json={"texto": "apartamento com piscina"}).json()
    resposta = client.post(f"/api/publico/{chave}/leads", json={
        "nome": "Maria", "telefone": "+55 22 99999-1111", "email": "maria@exemplo.com", "imovel_id": imovel["id"],
        "busca_id": busca["busca_id"], "mensagem": "Posso visitar sábado?", "aceitou_contato": True})
    codigo = resposta.json()["codigo"]
    _processar_emails(db)
    assert len(caixa) == 1
    aviso = caixa[0]
    assert aviso["para"] == ["dono@imob.com"] and aviso["responder_para"] == "maria@exemplo.com"
    assert codigo in aviso["assunto"] and "Apartamento com piscina" in aviso["assunto"]
    for trecho in ("Maria", "+55 22 99999-1111", "Posso visitar sábado?", "apartamento com piscina", "/app.html#leads"):
        assert trecho in aviso["texto"]


def test_whatsapp_nao_vira_email(client, db, caixa):
    client.get("/api/publico/pk_demo/whatsapp?sessao=s1", follow_redirects=False)
    _processar_emails(db)
    assert caixa == []


class _SMTPFalso:
    instancias: list["_SMTPFalso"] = []

    def __init__(self, host, porta, **kwargs):
        self.host, self.porta, self.passos = host, porta, []
        _SMTPFalso.instancias.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def starttls(self, context=None):
        self.passos.append("starttls")

    def login(self, usuario, senha):
        self.passos.append(f"login:{usuario}")

    def send_message(self, mensagem):
        self.passos.append(f"enviou:{mensagem['To']}")


def test_envio_smtp_com_starttls_e_tls_direto(monkeypatch):
    _SMTPFalso.instancias.clear()
    monkeypatch.setattr(email.smtplib, "SMTP", _SMTPFalso)
    monkeypatch.setattr(email.smtplib, "SMTP_SSL", _SMTPFalso)
    monkeypatch.setattr(email.settings, "smtp_host", "smtp.exemplo.com")
    monkeypatch.setattr(email.settings, "smtp_usuario", "usuario")
    monkeypatch.setattr(email.settings, "smtp_senha", "segredo")

    monkeypatch.setattr(email.settings, "smtp_porta", 587)
    assert email.enviar(["a@x.com", "b@x.com", "demo@homeclue.invalid"], "Oi", "Texto") is True
    assert _SMTPFalso.instancias[-1].passos == ["starttls", "login:usuario", "enviou:a@x.com, b@x.com"]

    monkeypatch.setattr(email.settings, "smtp_porta", 465)
    assert email.enviar("a@x.com", "Oi", "Texto") is True
    assert _SMTPFalso.instancias[-1].passos == ["login:usuario", "enviou:a@x.com"]

    assert email.enviar("demo@homeclue.invalid", "Oi", "Texto") is False  # conta de demonstração


def test_sem_smtp_o_email_so_vai_para_o_log(monkeypatch, caplog):
    monkeypatch.setattr(email.settings, "smtp_host", "")
    with caplog.at_level("INFO"):
        assert email.enviar("a@x.com", "Assunto", "Corpo do e-mail") is False
    assert "Corpo do e-mail" in caplog.text
