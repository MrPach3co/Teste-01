"""Criação de leads (formulário e WhatsApp) e para onde eles vão."""

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import gerar_codigo_lead
from app.core.telefone import numero_whatsapp
from app.core.tempo import agora_utc
from app.models import Imobiliaria, Imovel, Lead, RegistroBusca, Unidade
from app.services import avisos, cobranca
from app.services.busca.criterios import Criterios
from app.services.tarefas import enfileirar


def destino_whatsapp(imobiliaria: Imobiliaria, imovel: Imovel | None) -> str | None:
    """WhatsApp do corretor responsável pelo imóvel; se não houver, o da imobiliária."""
    if imovel is not None and imovel.corretor is not None:
        numero = numero_whatsapp(imovel.corretor.whatsapp)
        if numero:
            return numero
    return numero_whatsapp(imobiliaria.whatsapp)


def _codigo_unico(db: Session, imobiliaria_id: int) -> str:
    for _ in range(20):
        codigo = gerar_codigo_lead()
        existe = db.scalar(select(Lead.id).where(Lead.imobiliaria_id == imobiliaria_id, Lead.codigo == codigo))
        if existe is None:
            return codigo
    raise RuntimeError("Não foi possível gerar um código de lead único")


def criar_lead(db: Session, imobiliaria: Imobiliaria, *, origem: str, imovel: Imovel | None = None,
               unidade: Unidade | None = None, busca: RegistroBusca | None = None, sessao: str | None = None,
               criterios: dict | None = None, match: int | None = None, **dados) -> Lead:
    """Cria o lead. Cliques repetidos no WhatsApp (mesma sessão, mesmo imóvel,
    em 30 minutos) reaproveitam o lead já criado — não contam em dobro."""
    if origem == "whatsapp" and sessao:
        anterior = db.scalar(select(Lead).where(
            Lead.imobiliaria_id == imobiliaria.id, Lead.origem == "whatsapp", Lead.sessao == sessao,
            Lead.imovel_id.is_(None) if imovel is None else Lead.imovel_id == imovel.id,
            Lead.unidade_id.is_(None) if unidade is None else Lead.unidade_id == unidade.id,
            Lead.criado_em >= agora_utc() - timedelta(minutes=30),
        ).limit(1))
        if anterior is not None:
            return anterior

    if criterios is None and busca is not None:
        criterios = busca.criterios
    resumo = None
    if criterios:
        c = Criterios.de_dict(criterios)
        resumo = None if c.vazio() else c.resumo()

    lead = Lead(
        imobiliaria_id=imobiliaria.id,
        imovel_id=imovel.id if imovel else None,
        unidade_id=unidade.id if unidade else None,
        busca_id=busca.id if busca else None,
        corretor_id=imovel.corretor_id if imovel else None,
        origem=origem,
        codigo=_codigo_unico(db, imobiliaria.id),
        sessao=sessao,
        criterios=criterios,
        resumo_busca=resumo,
        match=match,
        busca_texto=dados.pop("busca_texto", None) or (busca.texto if busca else None),
        **dados,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    if cobranca.cobranca_por_lead_ativa() and imobiliaria.stripe_customer_id:
        enfileirar(db, "cobrar_lead", imobiliaria_id=imobiliaria.id, referencia=str(lead.id))
    if origem == "formulario":
        avisos.avisar_novo_lead(db, lead)
    return lead
