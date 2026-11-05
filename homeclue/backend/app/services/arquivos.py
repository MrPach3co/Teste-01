"""Imagens enviadas pela imobiliária (logo, planta, fotos de cômodos).

Toda imagem é aberta e regravada pelo Pillow antes de ser guardada: isso
confirma que é mesmo uma imagem, limita o tamanho e remove metadados (EXIF,
inclusive a localização GPS que o celular grava nas fotos). Como o arquivo
servido é sempre uma imagem recodificada, um "SVG com script" ou um HTML
disfarçado nunca chega ao navegador de ninguém.
"""

import io
import uuid

from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy.orm import Session

from app.models import Arquivo

Image.MAX_IMAGE_PIXELS = 50_000_000  # trava contra "bomba de descompressão"

TAMANHO_MAXIMO_ENVIO = 15 * 1024 * 1024
_LADO_MAXIMO = {"logo": 600, "planta": 2400, "foto": 1800}


class ImagemInvalida(Exception):
    pass


def salvar_imagem(db: Session, imobiliaria_id: int, conteudo: bytes, tipo: str) -> Arquivo:
    if len(conteudo) > TAMANHO_MAXIMO_ENVIO:
        raise ImagemInvalida("A imagem passa de 15 MB.")
    try:
        imagem = Image.open(io.BytesIO(conteudo))
        imagem.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise ImagemInvalida("Arquivo não reconhecido como imagem (use JPG, PNG ou WebP).")
    formato_original = imagem.format
    if formato_original not in ("JPEG", "PNG", "WEBP", "GIF", "MPO"):
        raise ImagemInvalida("Formato não aceito. Use JPG, PNG ou WebP.")

    imagem = ImageOps.exif_transpose(imagem)  # respeita a rotação do celular antes de jogar o EXIF fora
    lado = _LADO_MAXIMO.get(tipo, 1800)
    imagem.thumbnail((lado, lado))

    tem_transparencia = imagem.mode in ("RGBA", "LA") or (imagem.mode == "P" and "transparency" in imagem.info)
    saida = io.BytesIO()
    if tipo == "planta" or (tipo == "logo" and (tem_transparencia or formato_original == "PNG")):
        imagem = imagem.convert("RGBA" if tem_transparencia else "RGB")
        imagem.save(saida, format="PNG", optimize=True)
        content_type = "image/png"
    else:
        imagem.convert("RGB").save(saida, format="JPEG", quality=84, optimize=True, progressive=True)
        content_type = "image/jpeg"

    dados = saida.getvalue()
    arquivo = Arquivo(
        id=uuid.uuid4().hex, imobiliaria_id=imobiliaria_id, tipo=tipo, content_type=content_type, dados=dados,
        tamanho=len(dados), largura=imagem.width, altura=imagem.height,
    )
    db.add(arquivo)
    db.flush()
    return arquivo


def url_do_arquivo(arquivo_id: str) -> str:
    return f"/api/arquivos/{arquivo_id}"
