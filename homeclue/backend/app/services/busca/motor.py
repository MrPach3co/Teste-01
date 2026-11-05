"""O motor de busca: conversa → critérios → match explicado → rankings.

Usado pelo widget (routers.publico) e pela avaliação das 30 buscas
(app.avaliacao), para que o que é testado seja exatamente o que roda.
"""

from dataclasses import dataclass, field
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.planos import RANKINGS, tem_recurso
from app.models import BairroInfo, Imobiliaria, Imovel
from app.services import cache
from app.services.busca import mensagens, rankings, regras
from app.services.busca.avaliacao import FATOR_STATUS, ImovelBusca, Ponto, avaliar, taxa_de_match
from app.services.busca.criterios import Criterios
from app.services.ia import cliente as ia_cliente
from app.services.ia import interpretacao, verificacao
from app.services.vocabulario import normalizar

MAX_RESULTADOS = 8
MAX_VERIFICADOS_PELA_IA = 8
_VERSAO_CACHE = 1


@dataclass
class ItemResultado:
    imovel: Imovel
    dados: ImovelBusca
    pontos: list[Ponto]
    match: int | None


@dataclass
class ResultadoBusca:
    criterios: Criterios
    fonte: str
    mensagem: str
    avisos: list[str]
    sugestoes: list[str]
    itens: list[ItemResultado]
    rankings: list[dict]
    uso: ia_cliente.UsoIA = field(default_factory=ia_cliente.UsoIA)


def imoveis_visiveis(db: Session, imobiliaria_id: int) -> list[Imovel]:
    return list(db.scalars(
        select(Imovel).where(
            Imovel.imobiliaria_id == imobiliaria_id,
            Imovel.ativo.is_(True),
            Imovel.removido_do_feed_em.is_(None),
        ).order_by(Imovel.criado_em.desc())
    ).all())


def _nomes_unicos(valores: list[str]) -> list[str]:
    vistos: dict[str, str] = {}
    for v in valores:
        vistos.setdefault(normalizar(v), v)
    return sorted(vistos.values())


def interpretar(db: Session, texto: str, anteriores: Criterios, historico: list[str], bairros: list[str],
                cidades: list[str], uso: ia_cliente.UsoIA) -> tuple[Criterios, str]:
    """Retorna (critérios atualizados, fonte "ia" | "regras")."""
    if ia_cliente.disponivel():
        chave = cache.chave_de("interpretacao", _VERSAO_CACHE, ia_cliente.modelo(), anteriores.para_dict(),
                               historico[-6:], normalizar(texto), bairros, cidades)
        em_cache = cache.obter(db, chave)
        if em_cache is not None:
            return Criterios.de_dict(em_cache), "ia"
        criterios = interpretacao.interpretar(texto, anteriores, historico, bairros, cidades, uso)
        if criterios is not None:
            cache.guardar(db, chave, criterios.para_dict(), timedelta(days=7))
            return criterios, "ia"
    return regras.aplicar_turno(anteriores, texto, bairros, cidades), "regras"


def _ordenar(item: ItemResultado):
    if item.match is None:
        return (1, 0, 0)  # sem critérios: mantém a ordem da carteira (mais recentes primeiro)
    atende = sum(1 for p in item.pontos if p.status == "atende")
    return (0, -item.match, -atende, item.dados.preco)


def executar(db: Session, imobiliaria: Imobiliaria, texto: str, anteriores: Criterios | None = None,
             historico: list[str] | None = None, criterios_extra: Criterios | None = None) -> ResultadoBusca:
    anteriores = anteriores or Criterios()
    historico = historico or []
    uso = ia_cliente.UsoIA()

    imoveis = imoveis_visiveis(db, imobiliaria.id)
    bairros = _nomes_unicos([i.bairro for i in imoveis])
    cidades = _nomes_unicos([i.cidade for i in imoveis])

    if texto.strip():
        criterios, fonte = interpretar(db, texto, anteriores, historico, bairros, cidades, uso)
    else:
        criterios, fonte = anteriores, "regras"
    if criterios_extra is not None:
        criterios = criterios.mesclar(criterios_extra)
        fonte = "ia"

    carteira = [ImovelBusca.de_imovel(i) for i in imoveis]
    por_id = {i.id: i for i in imoveis}
    candidatos = [d for d in carteira if por_id[d.id].atende_finalidade(criterios.finalidade)]

    itens = []
    for dados in candidatos:
        pontos = avaliar(dados, criterios)
        itens.append(ItemResultado(por_id[dados.id], dados, pontos, taxa_de_match(pontos)))
    itens.sort(key=_ordenar)

    # A IA confere os pedidos livres nos anúncios mais promissores; o código
    # confere a prova que ela citar (trava contra invenção).
    if criterios.desejos and ia_cliente.disponivel():
        topo = itens[:MAX_VERIFICADOS_PELA_IA]
        conferidas = verificacao.verificar_desejos(criterios.desejos, [i.dados for i in topo], uso)
        for item in topo:
            for indice, _desejo in enumerate(criterios.desejos):
                veredito = conferidas.get((item.dados.id, indice))
                if veredito is None:
                    continue
                status, trecho, origem = veredito
                for ponto in item.pontos:
                    if ponto.chave == f"desejo:{indice}" and FATOR_STATUS[ponto.status] <= FATOR_STATUS["nao_informado"]:
                        ponto.status, ponto.evidencia, ponto.fonte = status, f"“{trecho}”", origem
            item.match = taxa_de_match(item.pontos)
        itens.sort(key=_ordenar)

    itens = itens[:MAX_RESULTADOS]

    lista_rankings: list[dict] = []
    if itens and tem_recurso(imobiliaria.plano, RANKINGS):
        info_bairros = {
            normalizar(b.nome): {"valorizacao": b.valorizacao, "valorizacao_justificativa": b.valorizacao_justificativa}
            for b in db.scalars(select(BairroInfo).where(BairroInfo.imobiliaria_id == imobiliaria.id)).all()
        }
        lista_rankings = rankings.calcular(
            [(i.dados, i.match) for i in itens], carteira, criterios.finalidade, info_bairros,
            {i.dados.id: i.pontos for i in itens},
        )

    return ResultadoBusca(
        criterios=criterios,
        fonte=fonte,
        mensagem=mensagens.resposta(criterios, [(i.dados.titulo, i.match) for i in itens]),
        avisos=mensagens.avisos([i.pontos for i in itens]),
        sugestoes=mensagens.sugestoes(criterios),
        itens=itens,
        rankings=lista_rankings,
        uso=uso,
    )
