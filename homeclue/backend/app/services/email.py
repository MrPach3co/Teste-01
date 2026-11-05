"""Envio de e-mail por SMTP — funciona com Resend, Brevo, Amazon SES, Gmail…

Sem SMTP_HOST configurado, nada é enviado: o e-mail vai para o log (com o
texto completo só fora de produção, porque pode conter link de senha).
Os envios passam pela fila de tarefas, então uma falha do provedor é
repetida e nunca atrasa a resposta para o comprador.
"""

import logging
import smtplib
import ssl
from email.message import EmailMessage

from app.core.config import obter_settings

logger = logging.getLogger(__name__)

settings = obter_settings()


class FalhaNoEnvio(Exception):
    pass


def configurado() -> bool:
    return bool(settings.smtp_host)


def enviar(para: str | list[str], assunto: str, texto: str, responder_para: str | None = None) -> bool:
    """Envia uma mensagem só para todos os destinatários (True), ou só registra
    no log se o SMTP não estiver configurado (False). Lança FalhaNoEnvio se o
    provedor recusar — a fila tenta de novo."""
    # Domínio reservado (.invalid) é o da conta de demonstração: nunca recebe nada.
    destinos = [p for p in ([para] if isinstance(para, str) else para) if not p.lower().endswith(".invalid")]
    if not destinos:
        return False
    para = ", ".join(destinos)
    mensagem = EmailMessage()
    mensagem["From"] = settings.email_remetente
    mensagem["To"] = para
    mensagem["Subject"] = assunto
    if responder_para:
        mensagem["Reply-To"] = responder_para
    mensagem.set_content(texto)

    if not configurado():
        if settings.ambiente == "producao":
            logger.warning("SMTP não configurado: e-mail para %s não enviado (%s)", para, assunto)
        else:
            logger.info("E-mail (SMTP não configurado) para %s — %s\n%s", para, assunto, texto)
        return False

    contexto = ssl.create_default_context()
    try:
        if settings.smtp_porta == 465:
            servidor = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_porta, context=contexto, timeout=20)
        else:
            servidor = smtplib.SMTP(settings.smtp_host, settings.smtp_porta, timeout=20)
        with servidor:
            if settings.smtp_porta != 465:
                servidor.starttls(context=contexto)
            if settings.smtp_usuario:
                servidor.login(settings.smtp_usuario, settings.smtp_senha)
            servidor.send_message(mensagem)
    except (smtplib.SMTPException, OSError) as erro:
        raise FalhaNoEnvio(f"Falha ao enviar e-mail para {para}: {erro}") from erro
    return True

