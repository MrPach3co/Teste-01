from fastapi import APIRouter, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.db.session import obter_db
from app.models.imovel import Imovel
from app.schemas.busca import BuscaEntrada, BuscaResposta
from app.schemas.imovel import ImovelResultado
from app.services import llm_service, matcher

router = APIRouter(prefix="/api", tags=["busca"])

limiter = Limiter(key_func=get_remote_address)

MAXIMO_RESULTADOS = 3


@router.post("/buscar", response_model=BuscaResposta)
@limiter.limit("30/minute")
def buscar(request: Request, dados: BuscaEntrada, db: Session = Depends(obter_db)) -> BuscaResposta:
    interpretacao = llm_service.interpretar_busca(dados.texto)

    imoveis = db.query(Imovel).all()

    pontuados = []
    for imovel in imoveis:
        slugs_imovel = {tag.slug for tag in imovel.tags}
        match = matcher.calcular_match(
            tags_imovel=slugs_imovel,
            preco=imovel.preco,
            quartos=imovel.quartos,
            tags_pedidas=interpretacao.tags,
            orcamento=interpretacao.orcamento,
            quartos_pedidos=interpretacao.quartos,
        )
        pontuados.append((match, imovel))

    pontuados.sort(key=lambda item: item[0], reverse=True)
    melhores = pontuados[:MAXIMO_RESULTADOS]

    resultados = [
        ImovelResultado(
            id=imovel.id,
            nome=imovel.nome,
            bairro=imovel.bairro,
            preco=imovel.preco,
            quartos=imovel.quartos,
            area_m2=imovel.area_m2,
            cor_inicio=imovel.cor_inicio,
            cor_fim=imovel.cor_fim,
            match=match,
            motivo=imovel.descricao_diferencial,
        )
        for match, imovel in melhores
    ]

    if resultados:
        melhor = resultados[0]
        mensagem = (
            f'Encontrei {len(resultados)} boas opções. '
            f'A que mais combina é "{melhor.nome}", com {melhor.match}% de match.'
        )
    else:
        mensagem = "Não há imóveis cadastrados no momento."

    return BuscaResposta(mensagem=mensagem, fonte=interpretacao.fonte, resultados=resultados)
