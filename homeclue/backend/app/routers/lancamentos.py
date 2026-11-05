"""Espelho de lançamentos: empreendimento → torres → andares → unidades."""

import csv
import io

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import obter_imobiliaria_atual
from app.core.planos import LANCAMENTOS
from app.db.session import obter_db
from app.models import Empreendimento, Imobiliaria, Unidade
from app.schemas.lancamento import STATUS_UNIDADE, EmpreendimentoEntrada, EmpreendimentoSaida, UnidadeEntrada
from app.services import limites
from app.services.feed.parser import numero_br

router = APIRouter(prefix="/api/lancamentos", tags=["lançamentos"])


def _do_tenant(db: Session, imobiliaria: Imobiliaria, empreendimento_id: int) -> Empreendimento:
    emp = db.get(Empreendimento, empreendimento_id)
    if emp is None or emp.imobiliaria_id != imobiliaria.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lançamento não encontrado.")
    return emp


def _gerar_unidades(emp: Empreendimento) -> None:
    """Cria as unidades que faltam e apaga as que ficaram fora da nova grade.
    Unidades que continuam existindo mantêm status, preço e área."""
    existentes = {(u.torre, u.andar, u.posicao): u for u in emp.unidades}
    desejadas = set()
    for torre in emp.torres:
        for andar in range(1, torre["andares"] + 1):
            for posicao in range(1, torre["unidades_por_andar"] + 1):
                chave = (torre["nome"], andar, posicao)
                desejadas.add(chave)
                if chave not in existentes:
                    emp.unidades.append(Unidade(torre=torre["nome"], andar=andar, posicao=posicao,
                                                codigo=f"{andar}{posicao:02d}"))
    for chave, unidade in existentes.items():
        if chave not in desejadas:
            emp.unidades.remove(unidade)


@router.get("", response_model=list[EmpreendimentoSaida])
def listar(imobiliaria: Imobiliaria = Depends(obter_imobiliaria_atual), db: Session = Depends(obter_db)):
    return db.scalars(select(Empreendimento).where(Empreendimento.imobiliaria_id == imobiliaria.id)
                      .order_by(Empreendimento.criado_em.desc())).all()


@router.post("", response_model=EmpreendimentoSaida, status_code=status.HTTP_201_CREATED)
def criar(dados: EmpreendimentoEntrada, imobiliaria: Imobiliaria = Depends(obter_imobiliaria_atual),
          db: Session = Depends(obter_db)):
    limites.garantir_recurso(imobiliaria, LANCAMENTOS)
    _nomes_unicos(dados)
    emp = Empreendimento(imobiliaria_id=imobiliaria.id, **dados.model_dump(exclude={"torres"}),
                         torres=[t.model_dump() for t in dados.torres])
    db.add(emp)
    _gerar_unidades(emp)
    db.commit()
    db.refresh(emp)
    return emp


def _nomes_unicos(dados: EmpreendimentoEntrada) -> None:
    nomes = [t.nome.strip().lower() for t in dados.torres]
    if len(nomes) != len(set(nomes)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cada torre precisa de um nome diferente.")


@router.put("/{empreendimento_id}", response_model=EmpreendimentoSaida)
def atualizar(empreendimento_id: int, dados: EmpreendimentoEntrada,
              imobiliaria: Imobiliaria = Depends(obter_imobiliaria_atual), db: Session = Depends(obter_db)):
    limites.garantir_recurso(imobiliaria, LANCAMENTOS)
    _nomes_unicos(dados)
    emp = _do_tenant(db, imobiliaria, empreendimento_id)
    for campo, valor in dados.model_dump(exclude={"torres"}).items():
        setattr(emp, campo, valor)
    emp.torres = [t.model_dump() for t in dados.torres]
    _gerar_unidades(emp)
    db.commit()
    db.refresh(emp)
    return emp


@router.delete("/{empreendimento_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir(empreendimento_id: int, imobiliaria: Imobiliaria = Depends(obter_imobiliaria_atual),
            db: Session = Depends(obter_db)) -> None:
    db.delete(_do_tenant(db, imobiliaria, empreendimento_id))
    db.commit()


@router.put("/{empreendimento_id}/unidades", response_model=EmpreendimentoSaida)
def atualizar_unidades(empreendimento_id: int, unidades: list[UnidadeEntrada],
                       imobiliaria: Imobiliaria = Depends(obter_imobiliaria_atual), db: Session = Depends(obter_db)):
    """Atualiza várias unidades de uma vez (status, preço, área, tipologia)."""
    limites.garantir_recurso(imobiliaria, LANCAMENTOS)
    emp = _do_tenant(db, imobiliaria, empreendimento_id)
    por_id = {u.id: u for u in emp.unidades}
    for dados in unidades:
        unidade = por_id.get(dados.id)
        if unidade is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unidade {dados.id} não é deste lançamento.")
        for campo, valor in dados.model_dump(exclude={"id"}, exclude_unset=True).items():
            setattr(unidade, campo, valor)
    db.commit()
    db.refresh(emp)
    return emp


@router.post("/{empreendimento_id}/unidades/importar", response_model=EmpreendimentoSaida)
async def importar_unidades(empreendimento_id: int, arquivo: UploadFile = File(...),
                            imobiliaria: Imobiliaria = Depends(obter_imobiliaria_atual), db: Session = Depends(obter_db)):
    """CSV com colunas: torre;unidade;status;preco;area_m2;quartos;suites;vagas;tipologia."""
    limites.garantir_recurso(imobiliaria, LANCAMENTOS)
    emp = _do_tenant(db, imobiliaria, empreendimento_id)
    texto = (await arquivo.read(2 * 1024 * 1024)).decode("utf-8-sig", errors="replace")
    delimitador = ";" if texto.split("\n", 1)[0].count(";") >= texto.split("\n", 1)[0].count(",") else ","
    por_codigo = {(u.torre.lower(), u.codigo): u for u in emp.unidades}
    torre_unica = emp.torres[0]["nome"].lower() if len(emp.torres) == 1 else None
    erros = []
    for numero, linha in enumerate(csv.DictReader(io.StringIO(texto), delimiter=delimitador), start=2):
        linha = {(k or "").strip().lower(): (v or "").strip() for k, v in linha.items()}
        torre = (linha.get("torre") or torre_unica or "").lower()
        unidade = por_codigo.get((torre, linha.get("unidade", "")))
        if unidade is None:
            erros.append(f"Linha {numero}: unidade não encontrada")
            continue
        status_unidade = linha.get("status", "").lower().replace("í", "i")
        if status_unidade:
            status_unidade = {"vendido": "vendida", "reservado": "reservada"}.get(status_unidade, status_unidade)
            if status_unidade not in STATUS_UNIDADE:
                erros.append(f"Linha {numero}: status inválido")
                continue
            unidade.status = status_unidade
        for campo, conversor in (("preco", float), ("area_m2", float), ("quartos", int), ("suites", int), ("vagas", int)):
            bruto = linha.get(campo, "")
            if bruto:
                valor = numero_br(bruto)
                if valor is None or valor < 0:
                    erros.append(f"Linha {numero}: {campo} inválido")
                else:
                    setattr(unidade, campo, conversor(valor))
        if linha.get("tipologia"):
            unidade.tipologia = linha["tipologia"][:120]
    if erros and len(erros) > 20:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="; ".join(erros[:10]))
    db.commit()
    db.refresh(emp)
    return emp
