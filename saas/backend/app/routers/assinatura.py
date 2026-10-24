import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from stripe import SignatureVerificationError

from app.core.dependencies import exigir_dono
from app.core.planos import PLANOS
from app.db.session import obter_db
from app.models import Imobiliaria, Usuario
from app.services import cobranca

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/assinatura", tags=["assinatura"])


@router.get("/planos")
def listar_planos() -> dict:
    return {
        "pagamento_online": cobranca.cobranca_ativa(),
        "planos": [
            {
                "id": p.id,
                "nome": p.nome,
                "preco_mensal": p.preco_mensal,
                "limite_imoveis": p.limite_imoveis,
                "limite_buscas_mes": p.limite_buscas_mes,
                "limite_usuarios": p.limite_usuarios,
                "marca_kaza_no_widget": p.marca_kaza_no_widget,
                "destaque": p.destaque,
            }
            for p in PLANOS.values()
        ],
    }


@router.post("/checkout")
def checkout(plano: str, dono: Usuario = Depends(exigir_dono)) -> dict:
    try:
        return {"url": cobranca.criar_checkout(dono.imobiliaria, dono.email, plano)}
    except cobranca.CobrancaIndisponivel as erro:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(erro))


@router.post("/portal")
def portal(dono: Usuario = Depends(exigir_dono)) -> dict:
    try:
        return {"url": cobranca.criar_portal(dono.imobiliaria)}
    except cobranca.CobrancaIndisponivel as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro))


@router.post("/webhook", include_in_schema=False)
async def webhook(request: Request, db: Session = Depends(obter_db)) -> dict:
    corpo = await request.body()
    try:
        cobranca.validar_webhook(corpo, request.headers.get("stripe-signature", ""))
    except (cobranca.CobrancaIndisponivel, SignatureVerificationError, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Webhook inválido.")

    # Assinatura conferida: daqui em diante lemos o JSON cru, que é estável
    # entre versões do SDK do Stripe.
    evento = json.loads(corpo)
    objeto = evento["data"]["object"]
    tipo = evento["type"]

    if tipo == "checkout.session.completed":
        imobiliaria = db.get(Imobiliaria, int(objeto.get("client_reference_id") or 0))
        plano = (objeto.get("metadata") or {}).get("plano")
        if imobiliaria is not None and plano in PLANOS:
            imobiliaria.plano = plano
            imobiliaria.stripe_customer_id = objeto.get("customer")
            imobiliaria.stripe_subscription_id = objeto.get("subscription")
            db.commit()

    elif tipo in ("customer.subscription.updated", "customer.subscription.deleted"):
        imobiliaria = db.scalar(select(Imobiliaria).where(Imobiliaria.stripe_customer_id == objeto.get("customer")))
        if imobiliaria is not None:
            ativa = tipo == "customer.subscription.updated" and objeto.get("status") in ("active", "trialing", "past_due")
            if ativa:
                itens = (objeto.get("items") or {}).get("data") or []
                preco = itens[0]["price"]["id"] if itens else None
                imobiliaria.plano = cobranca.plano_do_preco(preco) or imobiliaria.plano
                imobiliaria.stripe_subscription_id = objeto.get("id")
            else:
                # Cancelou ou parou de pagar: volta ao Grátis. Os dados ficam;
                # só os limites voltam a valer.
                imobiliaria.plano = "gratis"
                imobiliaria.stripe_subscription_id = None
            db.commit()

    else:
        logger.info("Evento Stripe ignorado: %s", tipo)

    return {"recebido": True}
