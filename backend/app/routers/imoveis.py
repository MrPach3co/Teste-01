from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import obter_db
from app.models.imovel import Imovel
from app.schemas.imovel import ImovelResultado

router = APIRouter(prefix="/api/imoveis", tags=["imóveis"])


@router.get("", response_model=list[ImovelResultado])
def listar_imoveis(db: Session = Depends(obter_db)) -> list[ImovelResultado]:
    imoveis = db.query(Imovel).all()
    return [
        ImovelResultado(
            id=imovel.id,
            nome=imovel.nome,
            bairro=imovel.bairro,
            preco=imovel.preco,
            quartos=imovel.quartos,
            area_m2=imovel.area_m2,
            cor_inicio=imovel.cor_inicio,
            cor_fim=imovel.cor_fim,
            match=0,
            motivo=imovel.descricao_diferencial,
        )
        for imovel in imoveis
    ]
