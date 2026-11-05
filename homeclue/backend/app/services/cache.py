"""Cache com validade guardado no banco (vale para todos os processos)."""

import hashlib
import json
from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.tempo import agora_utc
from app.models import Cache


def chave_de(*partes) -> str:
    bruto = json.dumps(partes, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(bruto.encode("utf-8")).hexdigest()


def obter(db: Session, chave: str) -> dict | None:
    item = db.get(Cache, chave)
    if item is None or item.expira_em < agora_utc():
        return None
    return item.valor


def guardar(db: Session, chave: str, valor: dict, validade: timedelta) -> None:
    db.merge(Cache(chave=chave, valor=valor, expira_em=agora_utc() + validade))
    db.commit()
