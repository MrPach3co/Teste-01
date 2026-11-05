"""Sincroniza o estoque da imobiliária com o feed XML.

- Imóvel novo no feed → criado.
- Imóvel que já existia → atualizado (o feed é a fonte da verdade para os
  dados do anúncio; planta, corretor responsável e outros ajustes feitos no
  painel da Homeclue são preservados).
- Imóvel que saiu do feed → sai das buscas (não é apagado: os leads dele
  continuam no painel). Se voltar ao feed, volta às buscas.
- Feed vazio ou ilegível NUNCA apaga o estoque: a sincronização é abortada.
"""

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.planos import ANALISE_FOTOS, tem_recurso
from app.core.tempo import agora_utc
from app.models import Imobiliaria, Imovel, Tarefa
from app.services import limites
from app.services.feed import baixar as baixar_feed
from app.services.feed.parser import FormatoNaoReconhecido, ImovelFeed, ler
from app.services.tarefas import enfileirar, executor

logger = logging.getLogger(__name__)

# Campos que vêm do feed e sobrescrevem o que estiver no banco.
_CAMPOS_DO_FEED = [
    "titulo", "tipo", "finalidade", "preco", "preco_aluguel", "condominio", "iptu", "bairro", "cidade", "uf",
    "endereco", "mostrar_endereco", "quartos", "suites", "banheiros", "vagas", "area_m2", "area_terreno",
    "descricao", "caracteristicas", "comodidades", "fotos", "video_url", "url_anuncio",
]


class SincronizacaoFalhou(Exception):
    pass


def _aplicar(imovel: Imovel, dados: ImovelFeed) -> tuple[bool, bool]:
    """Copia os campos do feed. Retorna (local_mudou, fotos_mudaram)."""
    local_antes = (imovel.bairro, imovel.cidade, imovel.latitude, imovel.longitude)
    fotos_antes = [f.get("url") for f in (imovel.fotos or [])]
    for campo in _CAMPOS_DO_FEED:
        setattr(imovel, campo, getattr(dados, campo))
    if dados.latitude is not None and dados.longitude is not None:
        imovel.latitude, imovel.longitude = dados.latitude, dados.longitude
        imovel.coordenadas_aproximadas = not dados.mostrar_endereco
    if dados.planta_url and not (imovel.planta or {}).get("imagem"):
        imovel.planta = {"imagem": dados.planta_url, "comodos": []}
    local_depois = (imovel.bairro, imovel.cidade, imovel.latitude, imovel.longitude)
    return local_antes != local_depois, fotos_antes != [f.get("url") for f in imovel.fotos]


def sincronizar(db: Session, imobiliaria: Imobiliaria, conteudo: bytes | None = None) -> str:
    """Baixa (ou usa o conteúdo enviado), lê e aplica o feed. Retorna o resumo."""
    if conteudo is None:
        if not imobiliaria.feed_url:
            raise SincronizacaoFalhou("Nenhum endereço de feed configurado.")
        conteudo = baixar_feed.baixar(imobiliaria.feed_url)
    leitura = ler(conteudo)
    if not leitura.imoveis:
        detalhe = f" Primeiros problemas: {'; '.join(leitura.erros[:3])}" if leitura.erros else ""
        raise SincronizacaoFalhou(f"O feed não trouxe nenhum imóvel válido — nada foi alterado.{detalhe}")

    existentes = {
        i.codigo_referencia: i for i in db.scalars(select(Imovel).where(
            Imovel.imobiliaria_id == imobiliaria.id, Imovel.origem == "feed"))
    }
    agora = agora_utc()
    analisar_fotos = imobiliaria.analisar_fotos and tem_recurso(imobiliaria.plano, ANALISE_FOTOS)

    # Limite do plano: imóveis manuais ocupam vaga; os do feed entram até o limite.
    vagas = limites.vagas_de_imovel(db, imobiliaria)
    if vagas is not None:
        vagas += sum(1 for i in existentes.values() if i.removido_do_feed_em is None)

    novos = atualizados = fora_do_limite = 0
    no_feed: set[str] = set()
    for dados in leitura.imoveis:
        if vagas is not None and len(no_feed) >= vagas:
            fora_do_limite += 1
            continue
        no_feed.add(dados.codigo)
        imovel = existentes.get(dados.codigo)
        if imovel is None:
            imovel = Imovel(imobiliaria_id=imobiliaria.id, origem="feed", codigo_referencia=dados.codigo)
            db.add(imovel)
            novos += 1
        else:
            atualizados += 1
        local_mudou, fotos_mudaram = _aplicar(imovel, dados)
        imovel.removido_do_feed_em = None
        db.flush()
        if local_mudou or imovel.contexto is None:
            enfileirar(db, "contexto_bairro", imobiliaria_id=imobiliaria.id, imovel_id=imovel.id, commit=False)
        if analisar_fotos and (fotos_mudaram or imovel.analise_fotos is None) and imovel.fotos:
            imovel.analise_fotos = None
            enfileirar(db, "analisar_fotos", imobiliaria_id=imobiliaria.id, imovel_id=imovel.id, commit=False)

    removidos = 0
    for codigo, imovel in existentes.items():
        if codigo not in no_feed and imovel.removido_do_feed_em is None:
            imovel.removido_do_feed_em = agora
            removidos += 1

    partes = [f"{len(no_feed)} imóveis no ar", f"{novos} novos", f"{atualizados} atualizados", f"{removidos} saíram do feed"]
    if fora_do_limite:
        partes.append(f"{fora_do_limite} ficaram de fora pelo limite do plano")
    if leitura.erros:
        partes.append(f"{len(leitura.erros)} com problema ({'; '.join(leitura.erros[:3])})")
    resumo = ", ".join(partes) + "."

    imobiliaria.feed_formato = leitura.formato
    imobiliaria.feed_status = "ok"
    imobiliaria.feed_mensagem = resumo
    imobiliaria.feed_total = len(no_feed)
    imobiliaria.feed_ultima_sincronizacao = agora
    db.commit()
    return resumo


def registrar_falha(db: Session, imobiliaria: Imobiliaria, mensagem: str) -> None:
    db.rollback()
    imobiliaria.feed_status = "erro"
    imobiliaria.feed_mensagem = mensagem
    imobiliaria.feed_ultima_sincronizacao = agora_utc()
    db.commit()


@executor("sincronizar_feed")
def _executar(db: Session, tarefa: Tarefa) -> None:
    imobiliaria = db.get(Imobiliaria, tarefa.imobiliaria_id)
    if imobiliaria is None or not imobiliaria.feed_url:
        return
    try:
        sincronizar(db, imobiliaria)
    except (baixar_feed.FeedInvalido, FormatoNaoReconhecido, SincronizacaoFalhou) as erro:
        # Erro "esperado" (feed fora do ar, formato errado): registra e não repete agora;
        # a próxima tentativa acontece no próximo ciclo de sincronização.
        registrar_falha(db, imobiliaria, str(erro))

