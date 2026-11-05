from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db.session import obter_db
from app.models import Arquivo

router = APIRouter(prefix="/api/arquivos", tags=["arquivos"])


@router.get("/{arquivo_id}")
def servir(arquivo_id: str, db: Session = Depends(obter_db)) -> Response:
    """Imagens públicas (aparecem no site da imobiliária). O id é aleatório e
    o conteúdo é sempre uma imagem recodificada pelo servidor."""
    arquivo = db.get(Arquivo, arquivo_id) if len(arquivo_id) == 32 else None
    if arquivo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arquivo não encontrado.")
    return Response(
        content=arquivo.dados,
        media_type=arquivo.content_type,
        headers={
            "Cache-Control": "public, max-age=31536000, immutable",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'",
        },
    )
