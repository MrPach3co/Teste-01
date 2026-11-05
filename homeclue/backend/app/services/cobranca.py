"""Cobrança via Stripe: assinatura mensal, valor por lead e maquete avulsa.

O Stripe é a fonte da verdade sobre pagamento: plano e maquete só mudam
quando chega um webhook assinado — nunca porque o navegador voltou da
página de sucesso (isso seria fácil de forjar).

Modelo de negócio do documento de produto:
- Assinatura mensal por faixa de estoque (Essencial, Profissional, Premium).
- Valor por resultado: cada lead entregue vira um evento num "Meter" do
  Stripe, cobrado por uso junto da assinatura (se STRIPE_PRECO_POR_LEAD
  estiver configurado).
- Premium por imóvel: maquete 3D avulsa, pagamento único por imóvel.
"""

import logging

import stripe
from sqlalchemy.orm import Session

from app.core.config import obter_settings
from app.models import Imobiliaria, Imovel, Lead, Tarefa
from app.services.tarefas import executor

logger = logging.getLogger(__name__)

settings = obter_settings()


class CobrancaIndisponivel(Exception):
    pass


def _precos() -> dict[str, str]:
    return {
        plano: preco
        for plano, preco in (
            ("essencial", settings.stripe_preco_essencial),
            ("profissional", settings.stripe_preco_profissional),
            ("premium", settings.stripe_preco_premium),
        )
        if preco
    }


def cobranca_ativa() -> bool:
    return bool(settings.stripe_secret_key and _precos())


def cobranca_por_lead_ativa() -> bool:
    return bool(settings.stripe_secret_key and settings.stripe_preco_por_lead)


def maquete_avulsa_ativa() -> bool:
    return bool(settings.stripe_secret_key and settings.stripe_preco_maquete)


def _cliente() -> stripe.StripeClient:
    if not settings.stripe_secret_key:
        raise CobrancaIndisponivel("Pagamentos ainda não configurados (STRIPE_SECRET_KEY).")
    return stripe.StripeClient(settings.stripe_secret_key)


def _cliente_do_checkout(parametros: dict, imobiliaria: Imobiliaria, email: str) -> dict:
    if imobiliaria.stripe_customer_id:
        parametros["customer"] = imobiliaria.stripe_customer_id
    else:
        parametros["customer_email"] = email
    return parametros


def criar_checkout(imobiliaria: Imobiliaria, email: str, plano: str) -> str:
    preco = _precos().get(plano)
    if preco is None:
        raise CobrancaIndisponivel(f"Plano '{plano}' não está à venda.")
    itens = [{"price": preco, "quantity": 1}]
    if cobranca_por_lead_ativa():
        itens.append({"price": settings.stripe_preco_por_lead})  # cobrança por uso: sem quantidade
    metadados = {"imobiliaria_id": str(imobiliaria.id), "plano": plano, "tipo": "assinatura"}
    parametros = _cliente_do_checkout({
        "mode": "subscription",
        "line_items": itens,
        "client_reference_id": str(imobiliaria.id),
        "metadata": metadados,
        "subscription_data": {"metadata": metadados},
        "success_url": f"{settings.url_publica}/app.html#plano?pagamento=ok",
        "cancel_url": f"{settings.url_publica}/app.html#plano",
        "allow_promotion_codes": True,
    }, imobiliaria, email)
    return _cliente().v1.checkout.sessions.create(params=parametros).url


def criar_checkout_maquete(imobiliaria: Imobiliaria, email: str, imovel: Imovel) -> str:
    if not maquete_avulsa_ativa():
        raise CobrancaIndisponivel("Venda de maquete avulsa não configurada (STRIPE_PRECO_MAQUETE).")
    metadados = {"imobiliaria_id": str(imobiliaria.id), "imovel_id": str(imovel.id), "tipo": "maquete"}
    parametros = _cliente_do_checkout({
        "mode": "payment",
        "line_items": [{"price": settings.stripe_preco_maquete, "quantity": 1}],
        "client_reference_id": str(imobiliaria.id),
        "metadata": metadados,
        "success_url": f"{settings.url_publica}/app.html#imoveis?pagamento=ok",
        "cancel_url": f"{settings.url_publica}/app.html#imoveis",
    }, imobiliaria, email)
    return _cliente().v1.checkout.sessions.create(params=parametros).url


def criar_portal(imobiliaria: Imobiliaria) -> str:
    if not imobiliaria.stripe_customer_id:
        raise CobrancaIndisponivel("Esta conta ainda não tem assinatura paga.")
    sessao = _cliente().v1.billing_portal.sessions.create(
        params={"customer": imobiliaria.stripe_customer_id, "return_url": f"{settings.url_publica}/app.html#plano"}
    )
    return sessao.url


def validar_webhook(corpo: bytes, assinatura: str) -> None:
    """Lança SignatureVerificationError se o corpo não veio do Stripe."""
    if not settings.stripe_webhook_secret:
        raise CobrancaIndisponivel("STRIPE_WEBHOOK_SECRET não configurado.")
    stripe.Webhook.construct_event(corpo, assinatura, settings.stripe_webhook_secret)


def plano_do_preco(preco_id: str | None) -> str | None:
    for plano, preco in _precos().items():
        if preco == preco_id:
            return plano
    return None


@executor("cobrar_lead")
def _registrar_lead_no_stripe(db: Session, tarefa: Tarefa) -> None:
    """Envia 1 lead para o Meter do Stripe. O "identifier" torna o envio
    idempotente: se a tarefa repetir, o Stripe não cobra duas vezes."""
    lead = db.get(Lead, int(tarefa.referencia)) if tarefa.referencia else None
    if lead is None or not cobranca_por_lead_ativa():
        return
    imobiliaria = db.get(Imobiliaria, lead.imobiliaria_id)
    if not imobiliaria or not imobiliaria.stripe_customer_id:
        return
    _cliente().v1.billing.meter_events.create(params={
        "event_name": settings.stripe_evento_lead,
        "identifier": f"lead-{lead.id}",
        "payload": {"stripe_customer_id": imobiliaria.stripe_customer_id, "value": "1"},
    })
