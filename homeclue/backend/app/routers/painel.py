from collections import Counter
from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.dependencies import obter_imobiliaria_atual
from app.core.planos import obter_plano
from app.core.tempo import agora_utc
from app.db.session import obter_db
from app.models import Imobiliaria, Imovel, Lead, RegistroBusca
from app.services import limites
from app.services.vocabulario import normalizar

router = APIRouter(prefix="/api/painel", tags=["painel"])

_PALAVRAS_IGNORADAS = {
    "de", "da", "do", "das", "dos", "com", "em", "no", "na", "para", "pra", "um", "uma", "e", "o", "a",
    "ate", "que", "quero", "procuro", "busco", "perto", "mil", "milhoes", "milhao", "reais", "r$", "mais",
}


@router.get("/metricas")
def metricas(imobiliaria: Imobiliaria = Depends(obter_imobiliaria_atual), db: Session = Depends(obter_db)) -> dict:
    agora = agora_utc()
    inicio_mes = limites.inicio_do_mes(agora)
    trinta_dias = agora - timedelta(days=30)
    plano = obter_plano(imobiliaria.plano)

    buscas_mes = limites.contar_buscas_mes(db, imobiliaria.id)
    leads_mes = db.scalar(
        select(func.count(Lead.id)).where(Lead.imobiliaria_id == imobiliaria.id, Lead.criado_em >= inicio_mes)
    ) or 0
    leads_abertos = db.scalar(
        select(func.count(Lead.id)).where(Lead.imobiliaria_id == imobiliaria.id, Lead.status == "novo")
    ) or 0
    imoveis_ativos = db.scalar(
        select(func.count(Imovel.id)).where(Imovel.imobiliaria_id == imobiliaria.id, Imovel.ativo.is_(True))
    ) or 0

    # Séries diárias dos últimos 30 dias (agregadas em Python para funcionar
    # igual em SQLite e Postgres sem SQL específico de banco).
    datas_buscas = db.scalars(
        select(RegistroBusca.criado_em).where(
            RegistroBusca.imobiliaria_id == imobiliaria.id, RegistroBusca.criado_em >= trinta_dias
        )
    ).all()
    datas_leads = db.scalars(
        select(Lead.criado_em).where(Lead.imobiliaria_id == imobiliaria.id, Lead.criado_em >= trinta_dias)
    ).all()
    por_dia_buscas = Counter(d.date().isoformat() for d in datas_buscas)
    por_dia_leads = Counter(d.date().isoformat() for d in datas_leads)
    dias = [(agora - timedelta(days=i)).date().isoformat() for i in range(29, -1, -1)]

    textos = db.scalars(
        select(RegistroBusca.texto)
        .where(RegistroBusca.imobiliaria_id == imobiliaria.id, RegistroBusca.criado_em >= trinta_dias)
        .order_by(RegistroBusca.criado_em.desc())
        .limit(2000)
    ).all()
    termos = Counter(
        palavra
        for texto in textos
        for palavra in normalizar(texto).split()
        if len(palavra) > 2 and palavra not in _PALAVRAS_IGNORADAS and not palavra.isdigit()
    )

    return {
        "plano": {
            "id": plano.id,
            "nome": plano.nome,
            "limite_buscas_mes": plano.limite_buscas_mes,
            "limite_imoveis": plano.limite_imoveis,
            "limite_usuarios": plano.limite_usuarios,
        },
        "buscas_mes": buscas_mes,
        "leads_mes": leads_mes,
        "leads_novos": leads_abertos,
        "imoveis_ativos": imoveis_ativos,
        "imoveis_total": limites.contar_imoveis(db, imobiliaria.id),
        "usuarios_total": limites.contar_usuarios(db, imobiliaria.id),
        "conversao_mes": round(100 * leads_mes / buscas_mes, 1) if buscas_mes else 0,
        "serie": [{"dia": d, "buscas": por_dia_buscas.get(d, 0), "leads": por_dia_leads.get(d, 0)} for d in dias],
        "termos_populares": [{"termo": t, "total": n} for t, n in termos.most_common(12)],
        "buscas_recentes": list(textos[:8]),
    }
