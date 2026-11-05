"""Fila de tarefas em segundo plano, guardada no banco.

Roda dentro do próprio servidor (uma thread por processo), sem precisar de
Redis nem de outro serviço no Railway. Cada tarefa é travada com um UPDATE
condicional antes de rodar, então vários processos podem dividir a fila sem
executar nada em dobro. Falhas são repetidas com espera crescente.
"""

import logging
import threading
import traceback
from collections.abc import Callable
from datetime import timedelta

from sqlalchemy import and_, case, delete, or_, select, update
from sqlalchemy.orm import Session

from app.core.config import obter_settings
from app.core.tempo import agora_utc
from app.models import Imobiliaria, Tarefa
from app.services import cache

logger = logging.getLogger(__name__)

settings = obter_settings()

MAX_TENTATIVAS = 3
# Tarefas lentas e numerosas (uma por imóvel) vão para o fim da fila: com um
# feed de 1.000+ imóveis, um e-mail de senha não pode esperar todas elas.
_LENTAS = ("contexto_bairro", "analisar_fotos")
_TRAVA = timedelta(minutes=15)
_EXECUTORES: dict[str, Callable[[Session, Tarefa], None]] = {}


def executor(tipo: str):
    """Decorador que registra a função que executa um tipo de tarefa."""
    def registrar(funcao):
        _EXECUTORES[tipo] = funcao
        return funcao
    return registrar


def _carregar_executores() -> None:
    # Importados aqui para evitar import circular; cada módulo se registra com @executor.
    from app.services import avisos, cobranca, contexto  # noqa: F401
    from app.services.feed import sincronizar  # noqa: F401
    from app.services.ia import visao  # noqa: F401


def enfileirar(db: Session, tipo: str, *, imobiliaria_id: int | None = None, imovel_id: int | None = None,
               referencia: str | None = None, atraso: timedelta | None = None, commit: bool = True) -> None:
    """Agenda uma tarefa. Não duplica se já houver uma igual esperando."""
    ja_existe = db.scalar(select(Tarefa.id).where(
        Tarefa.tipo == tipo, Tarefa.status == "pendente",
        Tarefa.imobiliaria_id.is_(None) if imobiliaria_id is None else Tarefa.imobiliaria_id == imobiliaria_id,
        Tarefa.imovel_id.is_(None) if imovel_id is None else Tarefa.imovel_id == imovel_id,
        Tarefa.referencia.is_(None) if referencia is None else Tarefa.referencia == referencia,
    ).limit(1))
    if ja_existe is None:
        db.add(Tarefa(tipo=tipo, imobiliaria_id=imobiliaria_id, imovel_id=imovel_id, referencia=referencia,
                      executar_em=agora_utc() + (atraso or timedelta())))
    if commit:
        db.commit()


def _disponivel(agora):
    return or_(
        and_(Tarefa.status == "pendente", Tarefa.executar_em <= agora),
        and_(Tarefa.status == "executando", Tarefa.travado_ate < agora),
    )


def processar_uma(db: Session) -> bool:
    """Executa a próxima tarefa vencida. Retorna False se a fila está vazia."""
    _carregar_executores()
    agora = agora_utc()
    prioridade = case((Tarefa.tipo.in_(_LENTAS), 1), else_=0)
    tarefa_id = db.scalar(select(Tarefa.id).where(_disponivel(agora))
                          .order_by(prioridade, Tarefa.executar_em, Tarefa.id).limit(1))
    if tarefa_id is None:
        return False
    travou = db.execute(
        update(Tarefa).where(Tarefa.id == tarefa_id, _disponivel(agora))
        .values(status="executando", travado_ate=agora + _TRAVA, tentativas=Tarefa.tentativas + 1)
    ).rowcount
    db.commit()
    if travou != 1:
        return True  # outro processo pegou; segue para a próxima

    tarefa = db.get(Tarefa, tarefa_id)
    funcao = _EXECUTORES.get(tarefa.tipo)
    try:
        if funcao is None:
            raise RuntimeError(f"Tipo de tarefa desconhecido: {tarefa.tipo}")
        funcao(db, tarefa)
        db.rollback()  # descarta qualquer coisa que o executor tenha deixado sem commit
        tarefa = db.get(Tarefa, tarefa_id)
        tarefa.status, tarefa.concluido_em, tarefa.erro = "concluida", agora_utc(), None
    except Exception as erro:  # noqa: BLE001 — qualquer falha vira nova tentativa
        db.rollback()
        logger.warning("Tarefa %s (%s) falhou: %s", tarefa_id, tarefa.tipo, erro)
        tarefa = db.get(Tarefa, tarefa_id)
        tarefa.erro = "".join(traceback.format_exception_only(erro)).strip()[:2000]
        if tarefa.tentativas >= MAX_TENTATIVAS:
            tarefa.status = "erro"
        else:
            tarefa.status = "pendente"
            tarefa.executar_em = agora_utc() + timedelta(minutes=2 ** tarefa.tentativas)
    db.commit()
    return True


def processar_pendentes(db: Session, limite: int = 100) -> int:
    feitas = 0
    while feitas < limite and processar_uma(db):
        feitas += 1
    return feitas


def agendar_feeds(db: Session) -> None:
    """Enfileira a sincronização dos feeds que venceram. O UPDATE condicional
    garante que só um processo agende cada feed."""
    agora = agora_utc()
    vencidas = db.scalars(select(Imobiliaria.id).where(
        Imobiliaria.feed_url.is_not(None),
        or_(Imobiliaria.feed_proxima_sincronizacao.is_(None), Imobiliaria.feed_proxima_sincronizacao <= agora),
    )).all()
    for imobiliaria_id in vencidas:
        proxima = agora + timedelta(hours=settings.feed_intervalo_horas)
        pegou = db.execute(update(Imobiliaria).where(
            Imobiliaria.id == imobiliaria_id,
            or_(Imobiliaria.feed_proxima_sincronizacao.is_(None), Imobiliaria.feed_proxima_sincronizacao <= agora),
        ).values(feed_proxima_sincronizacao=proxima)).rowcount
        db.commit()
        if pegou == 1:
            enfileirar(db, "sincronizar_feed", imobiliaria_id=imobiliaria_id)


def limpar_antigas(db: Session) -> None:
    db.execute(delete(Tarefa).where(Tarefa.status == "concluida", Tarefa.concluido_em < agora_utc() - timedelta(days=7)))
    db.commit()
    cache.limpar_expirados(db)


class Executor:
    """Thread que esvazia a fila de tempos em tempos."""

    def __init__(self, fabrica_sessao, intervalo_segundos: float = 5.0):
        self._fabrica = fabrica_sessao
        self._intervalo = intervalo_segundos
        self._parar = threading.Event()
        self._thread = threading.Thread(target=self._rodar, name="homeclue-tarefas", daemon=True)

    def iniciar(self) -> None:
        self._thread.start()

    def parar(self) -> None:
        self._parar.set()
        self._thread.join(timeout=10)

    def _rodar(self) -> None:
        ciclos = 0
        while not self._parar.is_set():
            try:
                with self._fabrica() as db:
                    if ciclos % 12 == 0:  # ~1 vez por minuto
                        agendar_feeds(db)
                    if ciclos % 720 == 0:  # ~1 vez por hora
                        limpar_antigas(db)
                    processar_pendentes(db, limite=20)
            except Exception:  # noqa: BLE001 — a thread nunca pode morrer
                logger.exception("Erro no executor de tarefas")
            ciclos += 1
            self._parar.wait(self._intervalo)
