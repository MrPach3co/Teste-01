"""E-mails que a Homeclue manda: link para criar nova senha e aviso de lead.

Saem pela fila de tarefas (com novas tentativas se o provedor falhar).
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import obter_settings
from app.core.security import criar_token_redefinicao
from app.models import Lead, Tarefa, Usuario
from app.services import email
from app.services.tarefas import enfileirar, executor

settings = obter_settings()


@executor("email_redefinir_senha")
def _email_redefinir_senha(db: Session, tarefa: Tarefa) -> None:
    usuario = db.get(Usuario, int(tarefa.referencia or 0))
    if usuario is None:
        return
    link = f"{settings.url_publica}/entrar.html#redefinir={criar_token_redefinicao(usuario)}"
    email.enviar(usuario.email, "Crie uma nova senha na Homeclue", f"""Olá, {usuario.nome}.

Recebemos um pedido para criar uma nova senha para a conta {usuario.email} na Homeclue.
Para continuar, abra o link abaixo. Ele vale por 1 hora e funciona uma vez só:

{link}

Se não foi você, é só ignorar este e-mail: sua senha continua a mesma.

Homeclue
""")


def avisar_novo_lead(db: Session, lead: Lead) -> None:
    """Lead do formulário avisa por e-mail. (O de WhatsApp já chega no
    WhatsApp do corretor, então não vira e-mail.)"""
    enfileirar(db, "avisar_lead", imobiliaria_id=lead.imobiliaria_id, referencia=str(lead.id))


def _destinatarios(db: Session, lead: Lead) -> list[str]:
    """O corretor responsável pelo imóvel e o dono da imobiliária."""
    donos = db.scalars(select(Usuario.email).where(Usuario.imobiliaria_id == lead.imobiliaria_id,
                                                   Usuario.papel == "dono")).all()
    emails = ([lead.corretor.email] if lead.corretor else []) + list(donos)
    return list(dict.fromkeys(emails))


def _reais(valor: float | None) -> str:
    return f"R$ {valor:,.0f}".replace(",", ".") if valor else ""


@executor("avisar_lead")
def _avisar_lead(db: Session, tarefa: Tarefa) -> None:
    lead = db.get(Lead, int(tarefa.referencia or 0))
    if lead is None:
        return
    destinatarios = _destinatarios(db, lead)
    if not destinatarios:
        return

    linhas = [f"Novo lead pela busca do seu site — código {lead.codigo}.", ""]
    linhas += [f"Nome: {lead.nome or '(não informado)'}"]
    if lead.telefone:
        linhas.append(f"Telefone: {lead.telefone}")
    if lead.email:
        linhas.append(f"E-mail: {lead.email}")
    if lead.mensagem:
        linhas += ["", f"Mensagem: {lead.mensagem}"]
    if lead.imovel is not None:
        imovel = lead.imovel
        referencia = f" (cód. {imovel.codigo_referencia})" if imovel.codigo_referencia else ""
        linhas += ["", f"Imóvel: {imovel.titulo}{referencia}", f"{imovel.bairro}, {imovel.cidade}"
                   + (f" · {_reais(imovel.preco)}" if imovel.preco else "")]
    if lead.unidade is not None:
        unidade = lead.unidade
        linhas += ["", f"Lançamento: {unidade.empreendimento.nome} — unidade {unidade.codigo}"]
    if lead.resumo_busca or lead.busca_texto:
        linhas += ["", "O que a pessoa procurava:"]
        if lead.busca_texto:
            linhas.append(f"“{lead.busca_texto}”")
        if lead.resumo_busca:
            linhas.append(f"Entendido como: {lead.resumo_busca}")
        if lead.match is not None:
            linhas.append(f"Compatibilidade com o imóvel: {lead.match}%")
    linhas += ["", f"Acompanhe no painel: {settings.url_publica}/app.html#leads", "", "Homeclue"]

    assunto = f"Novo lead {lead.codigo}: {lead.nome or 'contato pelo site'}"
    if lead.imovel is not None:
        assunto += f" — {lead.imovel.titulo}"
    email.enviar(destinatarios, assunto[:150], "\n".join(linhas), responder_para=lead.email)
