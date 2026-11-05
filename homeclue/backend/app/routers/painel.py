from collections import Counter
from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.dependencies import obter_imobiliaria_atual
from app.core.planos import RELATORIO_DEMANDA, obter_plano
from app.core.tempo import agora_utc
from app.db.session import obter_db
from app.models import Evento, Imobiliaria, Imovel, Lead, RegistroBusca
from app.services import demanda, limites
from app.services.vocabulario import normalizar

router = APIRouter(prefix="/api/painel", tags=["painel"])

_PALAVRAS_IGNORADAS = {
    "de", "da", "do", "das", "dos", "com", "em", "no", "na", "para", "pra", "um", "uma", "e", "o", "a", "os", "as",
    "ate", "que", "quero", "procuro", "busco", "perto", "mil", "milhoes", "milhao", "reais", "mais", "por", "mes",
    "tem", "ter", "tenha", "sem", "ou", "me", "eu", "minha", "meu",
}


@router.get("/metricas")
def metricas(imobiliaria: Imobiliaria = Depends(obter_imobiliaria_atual), db: Session = Depends(obter_db)) -> dict:
    agora = agora_utc()
    inicio_mes = limites.inicio_do_mes(agora)
    trinta_dias = agora - timedelta(days=30)
    plano = obter_plano(imobiliaria.plano)

    buscas_mes = limites.contar_buscas_mes(db, imobiliaria.id)
    conversas_mes = db.scalar(select(func.count(func.distinct(RegistroBusca.sessao))).where(
        RegistroBusca.imobiliaria_id == imobiliaria.id, RegistroBusca.criado_em >= inicio_mes,
        RegistroBusca.sessao.is_not(None))) or 0
    leads_mes = dict(db.execute(select(Lead.origem, func.count(Lead.id)).where(
        Lead.imobiliaria_id == imobiliaria.id, Lead.criado_em >= inicio_mes).group_by(Lead.origem)).all())
    total_leads_mes = sum(leads_mes.values())
    leads_novos = db.scalar(select(func.count(Lead.id)).where(
        Lead.imobiliaria_id == imobiliaria.id, Lead.status == "novo")) or 0
    fechados = db.execute(select(func.count(Lead.id), func.coalesce(func.sum(Lead.valor_negocio), 0)).where(
        Lead.imobiliaria_id == imobiliaria.id, Lead.status == "fechado", Lead.fechado_em >= inicio_mes)).one()
    imoveis_no_ar = db.scalar(select(func.count(Imovel.id)).where(
        Imovel.imobiliaria_id == imobiliaria.id, Imovel.ativo.is_(True), Imovel.removido_do_feed_em.is_(None))) or 0

    # Séries diárias (agregadas em Python: funciona igual em SQLite e Postgres).
    datas_buscas = db.scalars(select(RegistroBusca.criado_em).where(
        RegistroBusca.imobiliaria_id == imobiliaria.id, RegistroBusca.criado_em >= trinta_dias)).all()
    datas_leads = db.scalars(select(Lead.criado_em).where(
        Lead.imobiliaria_id == imobiliaria.id, Lead.criado_em >= trinta_dias)).all()
    por_dia_buscas = Counter(d.date().isoformat() for d in datas_buscas)
    por_dia_leads = Counter(d.date().isoformat() for d in datas_leads)
    dias = [(agora - timedelta(days=i)).date().isoformat() for i in range(29, -1, -1)]

    # Imóveis mais vistos: aberturas do detalhe, aparições nos resultados e leads.
    visualizacoes = Counter(dict(db.execute(select(Evento.imovel_id, func.count(Evento.id)).where(
        Evento.imobiliaria_id == imobiliaria.id, Evento.tipo == "visualizacao", Evento.criado_em >= trinta_dias,
        Evento.imovel_id.is_not(None)).group_by(Evento.imovel_id)).all()))
    aparicoes: Counter = Counter()
    for ids in db.scalars(select(RegistroBusca.resultados_ids).where(
            RegistroBusca.imobiliaria_id == imobiliaria.id, RegistroBusca.criado_em >= trinta_dias)).all():
        aparicoes.update(ids or [])
    leads_imovel = Counter(dict(db.execute(select(Lead.imovel_id, func.count(Lead.id)).where(
        Lead.imobiliaria_id == imobiliaria.id, Lead.criado_em >= trinta_dias, Lead.imovel_id.is_not(None))
        .group_by(Lead.imovel_id)).all()))
    ids_top = [i for i, _ in (visualizacoes + aparicoes + leads_imovel).most_common(10)]
    titulos = dict(db.execute(select(Imovel.id, Imovel.titulo).where(Imovel.id.in_(ids_top))).all()) if ids_top else {}
    mais_vistos = [{"imovel_id": i, "titulo": titulos.get(i, "(removido)"), "visualizacoes": visualizacoes[i],
                    "aparicoes": aparicoes[i], "leads": leads_imovel[i]} for i in ids_top]

    textos = db.scalars(select(RegistroBusca.texto).where(
        RegistroBusca.imobiliaria_id == imobiliaria.id, RegistroBusca.criado_em >= trinta_dias)
        .order_by(RegistroBusca.criado_em.desc()).limit(2000)).all()
    termos = Counter(
        palavra for texto in textos for palavra in normalizar(texto).split()
        if len(palavra) > 2 and palavra not in _PALAVRAS_IGNORADAS and not any(ch.isdigit() for ch in palavra)
    )

    return {
        "plano": {"id": plano.id, "nome": plano.nome, "limite_buscas_mes": plano.limite_buscas_mes,
                  "limite_imoveis": plano.limite_imoveis, "limite_usuarios": plano.limite_usuarios},
        "buscas_mes": buscas_mes,
        "conversas_mes": conversas_mes,
        "leads_mes": total_leads_mes,
        "leads_whatsapp_mes": leads_mes.get("whatsapp", 0),
        "leads_formulario_mes": leads_mes.get("formulario", 0),
        "leads_novos": leads_novos,
        "negocios_fechados_mes": fechados[0],
        "valor_fechado_mes": float(fechados[1] or 0),
        "imoveis_ativos": imoveis_no_ar,
        "imoveis_total": limites.contar_imoveis(db, imobiliaria.id),
        "usuarios_total": limites.contar_usuarios(db, imobiliaria.id),
        "conversao_mes": round(100 * total_leads_mes / conversas_mes, 1) if conversas_mes else 0,
        "serie": [{"dia": d, "buscas": por_dia_buscas.get(d, 0), "leads": por_dia_leads.get(d, 0)} for d in dias],
        "mais_vistos": mais_vistos,
        "termos_populares": [{"termo": t, "total": n} for t, n in termos.most_common(12)],
        "buscas_recentes": list(textos[:8]),
        "relatorio_demanda": RELATORIO_DEMANDA in plano.recursos,
    }


@router.get("/demanda")
def relatorio_demanda(dias: int = 30, imobiliaria: Imobiliaria = Depends(obter_imobiliaria_atual),
                      db: Session = Depends(obter_db)) -> dict:
    limites.garantir_recurso(imobiliaria, RELATORIO_DEMANDA)
    return demanda.relatorio(db, imobiliaria.id, max(7, min(dias, 365)))


@router.get("/qualidade")
def qualidade_anuncios(imobiliaria: Imobiliaria = Depends(obter_imobiliaria_atual),
                       db: Session = Depends(obter_db)) -> list[dict]:
    return demanda.qualidade(db, imobiliaria.id)
