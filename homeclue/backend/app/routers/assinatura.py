import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from stripe import SignatureVerificationError

from app.core.dependencies import exigir_dono
from app.core.planos import NOMES_RECURSOS, PLANOS
from app.db.session import obter_db
from app.models import Imobiliaria, Imovel, Usuario
from app.services import cobranca

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/assinatura", tags=["assinatura"])


@router.get("/planos")
def listar_planos() -> dict:
    return {
        "pagamento_online": cobranca.cobranca_ativa(),
        "cobranca_por_lead": cobranca.cobranca_por_lead_ativa(),
        "maquete_avulsa": cobranca.maquete_avulsa_ativa(),
        "nomes_recursos": NOMES_RECURSOS,
        "planos": [
            {"id": p.id, "nome": p.nome, "preco_mensal": p.preco_mensal, "limite_imoveis": p.limite_imoveis,
             "limite_buscas_mes": p.limite_buscas_mes, "limite_usuarios": p.limite_usuarios,
             "recursos": sorted(p.recursos), "destaque": p.destaque}
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


def _id_do_metadado(metadados: dict, chave: str) -> int | None:
    valor = (metadados or {}).get(chave)
    return int(valor) if isinstance(valor, str) and valor.isdigit() else None


@router.post("/webhook", include_in_schema=False)
async def webhook(request: Request, db: Session = Depends(obter_db)) -> dict:
    corpo = await request.body()
    try:
        cobranca.validar_webhook(corpo, request.headers.get("stripe-signature", ""))
    except (cobranca.CobrancaIndisponivel, SignatureVerificationError, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Webhook inválido.")

    # Assinatura conferida: daqui em diante lemos o JSON cru, estável entre versões do SDK.
    evento = json.loads(corpo)
    objeto = evento["data"]["object"]
    tipo = evento["type"]
    metadados = objeto.get("metadata") or {}

    if tipo == "checkout.session.completed":
        imobiliaria = db.get(Imobiliaria, int(objeto.get("client_reference_id") or 0))
        if imobiliaria is None:
            return {"recebido": True}
        if metadados.get("tipo") == "maquete":
            imovel = db.get(Imovel, _id_do_metadado(metadados, "imovel_id") or 0)
            if imovel is not None and imovel.imobiliaria_id == imobiliaria.id and objeto.get("payment_status") == "paid":
                imovel.maquete_liberada = True
        elif metadados.get("plano") in PLANOS:
            imobiliaria.plano = metadados["plano"]
            imobiliaria.stripe_subscription_id = objeto.get("subscription")
        if objeto.get("customer"):
            imobiliaria.stripe_customer_id = objeto["customer"]
        db.commit()

    elif tipo in ("customer.subscription.updated", "customer.subscription.deleted"):
        imobiliaria = db.scalar(select(Imobiliaria).where(Imobiliaria.stripe_customer_id == objeto.get("customer")))
        if imobiliaria is not None:
            ativa = tipo == "customer.subscription.updated" and objeto.get("status") in ("active", "trialing", "past_due")
            if ativa:
                precos = [item["price"]["id"] for item in (objeto.get("items") or {}).get("data") or []]
                plano = next((p for p in map(cobranca.plano_do_preco, precos) if p), None)
                imobiliaria.plano = plano or imobiliaria.plano
                imobiliaria.stripe_subscription_id = objeto.get("id")
            else:
                # Cancelou ou parou de pagar: volta ao teste grátis. Os dados ficam;
                # só os limites voltam a valer.
                imobiliaria.plano = "gratis"
                imobiliaria.stripe_subscription_id = None
            db.commit()
    else:
        logger.info("Evento Stripe ignorado: %s", tipo)
    return {"recebido": True}
