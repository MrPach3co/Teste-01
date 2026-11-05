"""Relatório de demanda e qualidade dos anúncios.

Responde às três perguntas do documento de produto: o que as pessoas
procuram, o que acham, e o que falta no estoque — e mostra quais anúncios
precisam melhorar para a busca conseguir comprovar o match.
"""

from collections import Counter, defaultdict
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.tempo import agora_utc
from app.models import Imovel, RegistroBusca
from app.services.busca.avaliacao import ImovelBusca, _ponto_caracteristica
from app.services.busca.criterios import Criterios, formatar_reais
from app.services.vocabulario import CARACTERISTICAS, NOMES_PERTO_DE, TIPOS

_FAIXAS_VENDA = [200_000, 400_000, 600_000, 800_000, 1_000_000, 1_500_000, 2_000_000]
_FAIXAS_ALUGUEL = [1_000, 1_500, 2_000, 3_000, 4_000, 6_000]


def _faixa(valor: float, finalidade: str | None) -> str:
    faixas = _FAIXAS_ALUGUEL if finalidade == "aluguel" else _FAIXAS_VENDA
    sufixo = "/mês" if finalidade == "aluguel" else ""
    for limite in faixas:
        if valor <= limite:
            return f"Até {formatar_reais(limite)}{sufixo}"
    return f"Acima de {formatar_reais(faixas[-1])}{sufixo}"


def _top(contador: Counter, n: int = 10) -> list[dict]:
    return [{"nome": nome, "buscas": total} for nome, total in contador.most_common(n)]


def relatorio(db: Session, imobiliaria_id: int, dias: int = 30) -> dict:
    desde = agora_utc() - timedelta(days=dias)
    buscas = db.scalars(select(RegistroBusca).where(
        RegistroBusca.imobiliaria_id == imobiliaria_id, RegistroBusca.criado_em >= desde,
    ).order_by(RegistroBusca.criado_em)).all()

    # Uma conversa tem vários turnos; para a demanda vale o último critério de cada sessão.
    por_sessao: dict[str, RegistroBusca] = {}
    for busca in buscas:
        if busca.criterios:
            por_sessao[busca.sessao or f"busca-{busca.id}"] = busca
    finais = list(por_sessao.values())

    tipos, bairros, faixas, quartos, itens, perto, desejos = (Counter() for _ in range(7))
    nao_encontrado: dict[str, dict] = {}
    encontraram = 0
    for busca in finais:
        c = Criterios.de_dict(busca.criterios)
        tipos.update(TIPOS[t] for t in c.tipos)
        bairros.update(c.bairros)
        if c.preco_max:
            faixas[_faixa(c.preco_max, c.finalidade)] += 1
        if c.quartos_min:
            quartos[f"{c.quartos_min}+ quartos"] += 1
        itens.update(CARACTERISTICAS[x] for x in c.caracteristicas)
        perto.update(f"Perto de {NOMES_PERTO_DE[p]}" for p in c.perto_de)
        desejos.update(d.lower() for d in c.desejos)
        if busca.bons_resultados > 0:
            encontraram += 1
        elif not c.vazio():
            grupo = nao_encontrado.setdefault(c.assinatura(), {"descricao": c.resumo(), "buscas": 0, "melhor_match": []})
            grupo["buscas"] += 1
            if busca.melhor_match is not None:
                grupo["melhor_match"].append(busca.melhor_match)

    faltas = sorted(nao_encontrado.values(), key=lambda g: g["buscas"], reverse=True)[:15]
    for grupo in faltas:
        valores = grupo.pop("melhor_match")
        grupo["melhor_match_medio"] = round(sum(valores) / len(valores)) if valores else None

    # Itens pedidos que NENHUM imóvel da carteira comprova ter.
    carteira = [ImovelBusca.de_imovel(i) for i in db.scalars(select(Imovel).where(
        Imovel.imobiliaria_id == imobiliaria_id, Imovel.ativo.is_(True), Imovel.removido_do_feed_em.is_(None))).all()]
    pedidos_sem_oferta = []
    slug_por_nome = {v: k for k, v in CARACTERISTICAS.items()}
    for nome, total in itens.most_common():
        slug = slug_por_nome[nome]
        tem = sum(1 for i in carteira if _ponto_caracteristica(slug, i, i.textos()).status == "atende")
        if tem == 0:
            pedidos_sem_oferta.append({"nome": nome, "buscas": total})

    return {
        "periodo_dias": dias,
        "conversas": len(finais),
        "turnos": len(buscas),
        "acharam_bom_resultado": encontraram,
        "tipos": _top(tipos),
        "bairros": _top(bairros),
        "faixas_preco": _top(faixas),
        "quartos": _top(quartos),
        "itens": _top(itens, 15),
        "perto_de": _top(perto),
        "desejos": _top(desejos, 15),
        "nao_encontrado": faltas,
        "pedidos_sem_oferta": pedidos_sem_oferta[:10],
    }


def qualidade(db: Session, imobiliaria_id: int, dias: int = 30) -> list[dict]:
    """Anúncios que precisam melhorar, com o motivo — inclusive o que os
    compradores perguntaram e o anúncio não informa."""
    desde = agora_utc() - timedelta(days=dias)
    lacunas_por_imovel: dict[int, Counter] = defaultdict(Counter)
    for lacunas in db.scalars(select(RegistroBusca.lacunas).where(
            RegistroBusca.imobiliaria_id == imobiliaria_id, RegistroBusca.criado_em >= desde)).all():
        for imovel_id, faltas in (lacunas or {}).items():
            lacunas_por_imovel[int(imovel_id)].update(faltas)

    saida = []
    imoveis = db.scalars(select(Imovel).where(
        Imovel.imobiliaria_id == imobiliaria_id, Imovel.removido_do_feed_em.is_(None))).all()
    for imovel in imoveis:
        problemas = []
        if not imovel.fotos:
            problemas.append("Sem fotos")
        elif len(imovel.fotos) < 5:
            problemas.append(f"Só {len(imovel.fotos)} foto(s)")
        if len(imovel.descricao or "") < 300:
            problemas.append("Descrição curta (a busca tem pouco de onde comprovar o match)")
        if imovel.area_m2 is None:
            problemas.append("Sem área")
        if imovel.tipo not in ("terreno", "comercial") and imovel.quartos is None:
            problemas.append("Sem número de quartos")
        if not imovel.caracteristicas and not imovel.comodidades:
            problemas.append("Sem lista de itens/características")
        perguntado = [f"{nome} ({n}×)" for nome, n in lacunas_por_imovel.get(imovel.id, Counter()).most_common(4)]
        if perguntado:
            problemas.append("Compradores pediram e o anúncio não informa: " + ", ".join(perguntado))
        if problemas:
            peso = len(problemas) + sum(lacunas_por_imovel.get(imovel.id, Counter()).values()) / 3
            saida.append({"imovel_id": imovel.id, "titulo": imovel.titulo, "codigo": imovel.codigo_referencia,
                          "origem": imovel.origem, "problemas": problemas, "prioridade": round(peso, 1)})
    saida.sort(key=lambda x: x["prioridade"], reverse=True)
    return saida[:50]
