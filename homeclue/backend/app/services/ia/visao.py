"""Visão computacional com a Claude.

1. Busca por foto: o comprador manda uma foto de referência; a IA descreve o
   que se vê (tipo, itens do vocabulário, estilo) e isso vira critério de
   busca. A foto não é guardada.
2. Análise das fotos dos anúncios (opcional, por imobiliária): a IA olha as
   fotos de cada anúncio para encontrar o que o texto não diz ("anúncios
   pobres", no documento de produto). O que vem daí é mostrado como
   "parece aparecer na foto (análise automática)", com a foto ao lado para
   o comprador conferir — nunca como fato do anúncio.
"""

import base64
import io
import logging

from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy.orm import Session

from app.core.planos import ANALISE_FOTOS, tem_recurso
from app.core.tempo import agora_utc
from app.models import Arquivo, Imobiliaria, Imovel, Tarefa
from app.services.busca.criterios import Criterios
from app.services.ia.cliente import UsoIA, anulavel, chamar_json, disponivel, modelo
from app.services.tarefas import executor
from app.services.vocabulario import CARACTERISTICAS, TIPOS, TIPOS_COMODO, caracteristicas_validas

logger = logging.getLogger(__name__)

MAX_FOTOS_ANALISADAS = 6
_LADO_MAXIMO = 1568  # maior lado recomendado para imagens na API


def _jpeg_base64(conteudo: bytes) -> str:
    imagem = Image.open(io.BytesIO(conteudo))
    imagem = ImageOps.exif_transpose(imagem)
    imagem.thumbnail((_LADO_MAXIMO, _LADO_MAXIMO))
    saida = io.BytesIO()
    imagem.convert("RGB").save(saida, format="JPEG", quality=85)
    return base64.standard_b64encode(saida.getvalue()).decode("ascii")


# ---------- busca por foto ----------

_INSTRUCAO_REFERENCIA = """A pessoa enviou esta foto como referência do imóvel que gostaria de encontrar.
Descreva SOMENTE o que dá para ver na foto, sem supor nada além dela.
- e_imovel: false se a foto não mostra um imóvel, cômodo ou área externa de imóvel.
- tipo: o tipo de imóvel, se der para ver; senão null.
- caracteristicas: itens da lista que aparecem claramente na foto.
- estilo: até 4 traços marcantes que não estão na lista (ex.: "casa de pedra", "varanda de madeira", "cozinha com ilha"), em poucas palavras.
- descricao: uma frase curta sobre a foto, em português."""

_SCHEMA_REFERENCIA = {
    "type": "object",
    "properties": {
        "e_imovel": {"type": "boolean"},
        "tipo": anulavel({"type": "string", "enum": list(TIPOS)}),
        "caracteristicas": {"type": "array", "items": {"type": "string", "enum": list(CARACTERISTICAS)}},
        "estilo": {"type": "array", "items": {"type": "string"}},
        "descricao": {"type": "string"},
    },
    "required": ["e_imovel", "tipo", "caracteristicas", "estilo", "descricao"],
    "additionalProperties": False,
}


class FotoInvalida(Exception):
    pass


def descrever_foto_referencia(conteudo: bytes, uso: UsoIA) -> dict | None:
    if not disponivel():
        return None
    try:
        dados_imagem = _jpeg_base64(conteudo)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise FotoInvalida("Não conseguimos abrir a foto. Tente outra imagem (JPG ou PNG).")
    conteudo_msg = [
        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": dados_imagem}},
        {"type": "text", "text": "Lista de itens possíveis: " + ", ".join(f"{k} ({v})" for k, v in CARACTERISTICAS.items())},
    ]
    dados = chamar_json(uso, system=_INSTRUCAO_REFERENCIA, conteudo=conteudo_msg, schema=_SCHEMA_REFERENCIA)
    if dados is None:
        return None
    estilo = [" ".join(str(e).split())[:60] for e in (dados.get("estilo") or []) if isinstance(e, str) and e.strip()]
    return {
        "e_imovel": bool(dados.get("e_imovel")),
        "tipo": dados.get("tipo") if dados.get("tipo") in TIPOS else None,
        "caracteristicas": caracteristicas_validas(dados.get("caracteristicas") or []),
        "estilo": estilo[:4],
        "descricao": str(dados.get("descricao") or "")[:200],
    }


def criterios_da_foto(descricao: dict) -> Criterios:
    return Criterios(
        tipos=[descricao["tipo"]] if descricao.get("tipo") else [],
        caracteristicas=list(descricao.get("caracteristicas") or []),
        desejos=list(descricao.get("estilo") or []),
    )


# ---------- análise das fotos dos anúncios ----------

_INSTRUCAO_ANUNCIO = """Estas são fotos de um anúncio de imóvel. Para cada foto, diga:
- comodo: que parte do imóvel aparece (use um dos códigos dados);
- caracteristicas: itens da lista que aparecem CLARAMENTE na foto (na dúvida, não inclua);
- descricao: uma frase curta e objetiva do que se vê, em português.
Não suponha nada que não esteja visível."""

_COMODOS_FOTO = list(TIPOS_COMODO) + ["fachada", "vista", "area-comum"]

_SCHEMA_ANUNCIO = {
    "type": "object",
    "properties": {
        "fotos": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "indice": {"type": "integer"},
                    "comodo": {"type": "string", "enum": _COMODOS_FOTO},
                    "caracteristicas": {"type": "array", "items": {"type": "string", "enum": list(CARACTERISTICAS)}},
                    "descricao": {"type": "string"},
                },
                "required": ["indice", "comodo", "caracteristicas", "descricao"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["fotos"],
    "additionalProperties": False,
}


def _bloco_imagem(db: Session, url: str) -> dict | None:
    """Foto do feed vai por URL; foto enviada ao painel vai em base64."""
    if url.startswith("/api/arquivos/"):
        arquivo = db.get(Arquivo, url.rsplit("/", 1)[-1])
        if arquivo is None:
            return None
        return {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                             "data": _jpeg_base64(arquivo.dados)}}
    if url.startswith("https://"):
        return {"type": "image", "source": {"type": "url", "url": url}}
    return None


def analisar_fotos_imovel(db: Session, imovel: Imovel, uso: UsoIA) -> dict | None:
    blocos, urls = [], []
    for foto in imovel.fotos[:MAX_FOTOS_ANALISADAS]:
        bloco = _bloco_imagem(db, foto.get("url", ""))
        if bloco:
            blocos += [{"type": "text", "text": f"Foto {len(urls)}:"}, bloco]
            urls.append(foto["url"])
    if not blocos:
        return None
    blocos.append({"type": "text", "text": "Códigos de cômodo: " + ", ".join(_COMODOS_FOTO)
                   + "\nLista de itens: " + ", ".join(f"{k} ({v})" for k, v in CARACTERISTICAS.items())})
    dados = chamar_json(uso, system=_INSTRUCAO_ANUNCIO, conteudo=blocos, schema=_SCHEMA_ANUNCIO, max_tokens=6000)
    if dados is None:
        return None
    fotos = []
    for item in dados.get("fotos", []):
        indice = item.get("indice")
        if isinstance(indice, int) and 0 <= indice < len(urls):
            fotos.append({
                "url": urls[indice],
                "comodo": item.get("comodo") if item.get("comodo") in _COMODOS_FOTO else "outro",
                "caracteristicas": caracteristicas_validas(item.get("caracteristicas") or []),
                "descricao": str(item.get("descricao") or "")[:160],
            })
    return {"fotos": fotos, "modelo": modelo(), "custo_usd": round(uso.custo_usd, 5),
            "em": agora_utc().isoformat(timespec="minutes")}


@executor("analisar_fotos")
def _executar(db: Session, tarefa: Tarefa) -> None:
    imovel = db.get(Imovel, tarefa.imovel_id) if tarefa.imovel_id else None
    if imovel is None or not disponivel():
        return
    imobiliaria = db.get(Imobiliaria, imovel.imobiliaria_id)
    if not (imobiliaria.analisar_fotos and tem_recurso(imobiliaria.plano, ANALISE_FOTOS)):
        return
    resultado = analisar_fotos_imovel(db, imovel, UsoIA())
    if resultado is not None:
        imovel.analise_fotos = resultado
        db.commit()
