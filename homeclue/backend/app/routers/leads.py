import csv
import io

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.dependencies import obter_imobiliaria_atual
from app.core.tempo import agora_utc
from app.db.session import obter_db
from app.models import Imobiliaria, Lead
from app.schemas.lead import STATUS_LEAD, LeadAtualizacao, LeadSaida

router = APIRouter(prefix="/api/leads", tags=["leads"])

_ORIGENS = {"formulario": "Formulário", "whatsapp": "WhatsApp"}


def _saida(lead: Lead) -> LeadSaida:
    unidade = None
    if lead.unidade is not None:
        unidade = f"{lead.unidade.empreendimento.nome} — {lead.unidade.torre}, unidade {lead.unidade.codigo}"
    return LeadSaida.model_validate(lead).model_copy(update={
        "imovel_titulo": lead.imovel.titulo if lead.imovel else None,
        "unidade_descricao": unidade,
        "corretor_nome": lead.corretor.nome if lead.corretor else None,
    })


def _do_tenant(db: Session, imobiliaria: Imobiliaria, lead_id: int) -> Lead:
    lead = db.get(Lead, lead_id)
    if lead is None or lead.imobiliaria_id != imobiliaria.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead não encontrado.")
    return lead


@router.get("", response_model=list[LeadSaida])
def listar(status_lead: str | None = None, origem: str | None = None, q: str | None = None,
           imobiliaria: Imobiliaria = Depends(obter_imobiliaria_atual), db: Session = Depends(obter_db)):
    consulta = select(Lead).where(Lead.imobiliaria_id == imobiliaria.id)
    if status_lead in STATUS_LEAD:
        consulta = consulta.where(Lead.status == status_lead)
    if origem in _ORIGENS:
        consulta = consulta.where(Lead.origem == origem)
    if q and q.strip():
        termo = q.strip().lstrip("#").upper()
        busca = f"%{q.strip()}%"
        consulta = consulta.where(or_(Lead.codigo == termo, Lead.nome.ilike(busca), Lead.telefone.ilike(busca),
                                      Lead.email.ilike(busca)))
    return [_saida(lead) for lead in db.scalars(consulta.order_by(Lead.criado_em.desc()).limit(500)).all()]


@router.patch("/{lead_id}", response_model=LeadSaida)
def atualizar(lead_id: int, dados: LeadAtualizacao, imobiliaria: Imobiliaria = Depends(obter_imobiliaria_atual),
              db: Session = Depends(obter_db)) -> LeadSaida:
    lead = _do_tenant(db, imobiliaria, lead_id)
    campos = dados.model_dump(exclude_unset=True)
    if "status" in campos and campos["status"] is not None:
        if campos["status"] == "fechado" and lead.status != "fechado":
            lead.fechado_em = agora_utc()
        elif campos["status"] != "fechado":
            lead.fechado_em = None
        lead.status = campos["status"]
    for campo in ("notas", "valor_negocio", "nome", "telefone", "email"):
        if campo in campos:
            setattr(lead, campo, campos[campo] if campos[campo] != "" else None)
    if lead.notas is None:
        lead.notas = ""
    db.commit()
    db.refresh(lead)
    return _saida(lead)


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(lead_id: int, imobiliaria: Imobiliaria = Depends(obter_imobiliaria_atual),
            db: Session = Depends(obter_db)) -> None:
    """Atende pedido de exclusão do titular (LGPD) — a imobiliária é a controladora."""
    db.delete(_do_tenant(db, imobiliaria, lead_id))
    db.commit()


@router.get("/exportar.csv")
def exportar_csv(imobiliaria: Imobiliaria = Depends(obter_imobiliaria_atual), db: Session = Depends(obter_db)):
    leads = db.scalars(select(Lead).where(Lead.imobiliaria_id == imobiliaria.id).order_by(Lead.criado_em.desc())).all()
    saida = io.StringIO()
    escritor = csv.writer(saida, delimiter=";")
    escritor.writerow(["data", "codigo", "origem", "nome", "email", "telefone", "status", "valor_negocio", "imovel",
                       "o_que_procura", "compatibilidade", "mensagem", "notas"])
    for lead in leads:
        escritor.writerow([
            lead.criado_em.strftime("%d/%m/%Y %H:%M"), lead.codigo or "", _ORIGENS.get(lead.origem, lead.origem),
            lead.nome or "", lead.email or "", lead.telefone or "", lead.status,
            f"{lead.valor_negocio:.2f}".replace(".", ",") if lead.valor_negocio else "",
            lead.imovel.titulo if lead.imovel else "", lead.resumo_busca or lead.busca_texto or "",
            f"{lead.match}%" if lead.match is not None else "", lead.mensagem, lead.notas,
        ])
    nome_arquivo = f"leads-{agora_utc():%Y-%m-%d}.csv"
    return StreamingResponse(
        iter(["﻿" + saida.getvalue()]),  # BOM para o Excel abrir com acentos certos
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nome_arquivo}"'},
    )
