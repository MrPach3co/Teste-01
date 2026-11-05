from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.dependencies import obter_imobiliaria_atual
from app.db.session import obter_db
from app.models import BairroInfo, Imobiliaria, Imovel
from app.schemas.bairro import BairroEntrada, BairroSaida

router = APIRouter(prefix="/api/bairros", tags=["bairros"])


@router.get("", response_model=list[BairroSaida])
def listar(imobiliaria: Imobiliaria = Depends(obter_imobiliaria_atual), db: Session = Depends(obter_db)):
    """Bairros da carteira, com o que a imobiliária já escreveu sobre cada um."""
    contagem = dict(db.execute(select(Imovel.bairro, func.count(Imovel.id)).where(
        Imovel.imobiliaria_id == imobiliaria.id, Imovel.removido_do_feed_em.is_(None)).group_by(Imovel.bairro)).all())
    info = {b.nome: b for b in db.scalars(select(BairroInfo).where(BairroInfo.imobiliaria_id == imobiliaria.id))}
    nomes = sorted(set(contagem) | set(info), key=lambda n: (-contagem.get(n, 0), n))
    return [
        BairroSaida(nome=n, imoveis=contagem.get(n, 0), descricao=info[n].descricao if n in info else "",
                    valorizacao=info[n].valorizacao if n in info else None,
                    valorizacao_justificativa=info[n].valorizacao_justificativa if n in info else "")
        for n in nomes
    ]


@router.put("/{nome}", response_model=BairroSaida)
def salvar(nome: str, dados: BairroEntrada, imobiliaria: Imobiliaria = Depends(obter_imobiliaria_atual),
           db: Session = Depends(obter_db)) -> BairroSaida:
    nome = " ".join(nome.split())[:120]
    info = db.scalar(select(BairroInfo).where(BairroInfo.imobiliaria_id == imobiliaria.id, BairroInfo.nome == nome))
    if info is None:
        info = BairroInfo(imobiliaria_id=imobiliaria.id, nome=nome)
        db.add(info)
    info.descricao = dados.descricao.strip()
    info.valorizacao = dados.valorizacao
    info.valorizacao_justificativa = dados.valorizacao_justificativa.strip()
    db.commit()
    total = db.scalar(select(func.count(Imovel.id)).where(Imovel.imobiliaria_id == imobiliaria.id,
                                                          Imovel.bairro == nome)) or 0
    return BairroSaida(nome=nome, imoveis=total, descricao=info.descricao, valorizacao=info.valorizacao,
                       valorizacao_justificativa=info.valorizacao_justificativa)
