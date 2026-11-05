from datetime import datetime, timezone


def agora_utc() -> datetime:
    """Agora em UTC, sem fuso (naive) — é assim que gravamos no banco,
    para SQLite e Postgres se comportarem igual."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
