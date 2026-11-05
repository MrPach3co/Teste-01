"""Assinaturas via Stripe (Checkout + Portal do cliente + webhook).

O Stripe é a fonte da verdade sobre o pagamento: o plano da imobiliária
só muda quando chega um webhook assinado — nunca porque o navegador voltou
da página de sucesso (isso seria trivial de forjar).
"""

import logging

import stripe

from app.core.config import obter_settings
from app.models import Imobiliaria

logger = logging.getLogger(__name__)

settings = obter_settings()


class CobrancaIndisponivel(Exception):
    pass


def _precos() -> dict[str, str]:
    return {
        plano: preco
        for plano, preco in (("pro", settings.stripe_preco_pro), ("escala", settings.stripe_preco_escala))
        if preco
    }


def cobranca_ativa() -> bool:
    return bool(settings.stripe_secret_key and _precos())


def _cliente() -> stripe.StripeClient:
    if not cobranca_ativa():
        raise CobrancaIndisponivel("Pagamentos ainda não configurados (STRIPE_SECRET_KEY / preços).")
    return stripe.StripeClient(settings.stripe_secret_key)


def criar_checkout(imobiliaria: Imobiliaria, email: str, plano: str) -> str:
    preco = _precos().get(plano)
    if preco is None:
        raise CobrancaIndisponivel(f"Plano '{plano}' não está à venda.")

    parametros: dict = {
        "mode": "subscription",
        "line_items": [{"price": preco, "quantity": 1}],
        "client_reference_id": str(imobiliaria.id),
        "metadata": {"imobiliaria_id": str(imobiliaria.id), "plano": plano},
        "subscription_data": {"metadata": {"imobiliaria_id": str(imobiliaria.id), "plano": plano}},
        "success_url": f"{settings.url_publica}/app.html#plano?pagamento=ok",
        "cancel_url": f"{settings.url_publica}/app.html#plano",
        "allow_promotion_codes": True,
    }
    if imobiliaria.stripe_customer_id:
        parametros["customer"] = imobiliaria.stripe_customer_id
    else:
        parametros["customer_email"] = email

    sessao = _cliente().v1.checkout.sessions.create(params=parametros)
    return sessao.url


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
