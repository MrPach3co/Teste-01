"""Painel do dono da Homeclue: clientes, uso e custo de IA por busca."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.dependencies import exigir_admin
from app.core.planos import obter_plano
from app.db.session import obter_db
from app.models import Imobiliaria, Imovel, Lead, RegistroBusca, Usuario
from app.services import limites
from app.services.ia import cliente as ia_cliente

router = APIRouter(prefix="/api/admin", tags=["admin"])

COTACAO_DOLAR_PADRAO = 5.6


@router.get("/resumo")
def resumo(cotacao: float = COTACAO_DOLAR_PADRAO, _: Usuario = Depends(exigir_admin),
           db: Session = Depends(obter_db)) -> dict:
    inicio = limites.inicio_do_mes()
    por_imobiliaria = {
        linha.imobiliaria_id: linha for linha in db.execute(
            select(RegistroBusca.imobiliaria_id, func.count(RegistroBusca.id).label("buscas"),
                   func.coalesce(func.sum(RegistroBusca.custo_usd), 0).label("custo"))
            .where(RegistroBusca.criado_em >= inicio).group_by(RegistroBusca.imobiliaria_id)
        ).all()
    }
    leads = dict(db.execute(select(Lead.imobiliaria_id, func.count(Lead.id))
                            .where(Lead.criado_em >= inicio).group_by(Lead.imobiliaria_id)).all())
    imoveis = dict(db.execute(select(Imovel.imobiliaria_id, func.count(Imovel.id))
                              .where(Imovel.removido_do_feed_em.is_(None)).group_by(Imovel.imobiliaria_id)).all())

    clientes = []
    for imobiliaria in db.scalars(select(Imobiliaria).order_by(Imobiliaria.criado_em.desc())).all():
        uso = por_imobiliaria.get(imobiliaria.id)
        buscas = uso.buscas if uso else 0
        custo = float(uso.custo) if uso else 0.0
        plano = obter_plano(imobiliaria.plano)
        clientes.append({
            "id": imobiliaria.id, "nome": imobiliaria.nome, "plano": plano.nome, "preco_mensal": plano.preco_mensal,
            "criado_em": imobiliaria.criado_em.isoformat(), "imoveis": imoveis.get(imobiliaria.id, 0),
            "feed": imobiliaria.feed_status, "buscas_mes": buscas, "leads_mes": leads.get(imobiliaria.id, 0),
            "custo_ia_mes_brl": round(custo * cotacao, 2),
            "custo_por_busca_brl": round(custo * cotacao / buscas, 4) if buscas else None,
        })

    # Custo médio real por busca, separado por modelo (só buscas que usaram IA).
    por_modelo = []
    for linha in db.execute(
        select(RegistroBusca.modelo, func.count(RegistroBusca.id), func.avg(RegistroBusca.custo_usd),
               func.avg(RegistroBusca.tokens_entrada), func.avg(RegistroBusca.tokens_saida))
        .where(RegistroBusca.modelo.is_not(None), RegistroBusca.criado_em >= inicio).group_by(RegistroBusca.modelo)
    ).all():
        modelo, total, custo_medio, entrada, saida = linha
        por_modelo.append({
            "modelo": modelo, "buscas": total, "custo_medio_usd": round(float(custo_medio or 0), 5),
            "custo_medio_brl": round(float(custo_medio or 0) * cotacao, 4),
            "tokens_entrada_medio": round(float(entrada or 0)), "tokens_saida_medio": round(float(saida or 0)),
        })

    receita = sum(c["preco_mensal"] for c in clientes)
    custo_total = sum(c["custo_ia_mes_brl"] for c in clientes)
    return {
        "cotacao_dolar": cotacao,
        "modelo_configurado": ia_cliente.modelo() if ia_cliente.disponivel() else None,
        "clientes": clientes,
        "custo_por_modelo": por_modelo,
        "totais": {"clientes": len(clientes), "receita_mensal_brl": receita, "custo_ia_mes_brl": round(custo_total, 2),
                   "usuarios": db.scalar(select(func.count(Usuario.id))) or 0},
    }
