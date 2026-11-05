"""Cache com validade guardado no banco (vale para todos os processos)."""

import hashlib
import json
from datetime import timedelta

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as insert_postgres
from sqlalchemy.dialects.sqlite import insert as insert_sqlite
from sqlalchemy.orm import Session

from app.core.tempo import agora_utc
from app.models import Cache


def chave_de(*partes) -> str:
    bruto = json.dumps(partes, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(bruto.encode("utf-8")).hexdigest()


def obter(db: Session, chave: str) -> dict | None:
    return obter_varios(db, [chave]).get(chave)


def obter_varios(db: Session, chaves: list[str]) -> dict[str, dict]:
    """Só o que ainda vale; chave ausente ou vencida não aparece."""
    if not chaves:
        return {}
    linhas = db.execute(select(Cache.chave, Cache.valor)
                        .where(Cache.chave.in_(set(chaves)), Cache.expira_em >= agora_utc()))
    return {chave: valor for chave, valor in linhas}


def guardar(db: Session, chave: str, valor: dict, validade: timedelta) -> None:
    guardar_varios(db, {chave: valor}, validade)


def guardar_varios(db: Session, itens: dict[str, dict], validade: timedelta) -> None:
    """Grava ou atualiza tudo de uma vez. É um upsert: duas buscas iguais ao
    mesmo tempo não brigam pela mesma chave (com merge, uma delas daria erro)."""
    if not itens:
        return
    expira_em = agora_utc() + validade
    insert = insert_postgres if db.get_bind().dialect.name == "postgresql" else insert_sqlite
    comando = insert(Cache).values([{"chave": c, "valor": v, "expira_em": expira_em} for c, v in itens.items()])
    comando = comando.on_conflict_do_update(
        index_elements=[Cache.chave],
        set_={"valor": comando.excluded.valor, "expira_em": comando.excluded.expira_em},
    )
    db.execute(comando)
    db.commit()


def limpar_expirados(db: Session) -> None:
    db.execute(delete(Cache).where(Cache.expira_em < agora_utc()))
    db.commit()
