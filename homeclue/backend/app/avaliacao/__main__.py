"""Uso: python -m app.avaliacao [--chave pk_demo] [--saida avaliacao.html] [--buscas arquivo.txt]

Roda as 30 buscas (ou as do arquivo, uma por linha) contra o estoque da
imobiliária e gera um relatório para conferência humana. Com
ANTHROPIC_API_KEY configurada, usa a IA de verdade (e mostra o custo).
Termina com código de saída 1 se houver qualquer violação da trava.
"""

import argparse
import sys
from pathlib import Path

from sqlalchemy import select

from app.avaliacao.buscas import BUSCAS_PADRAO, avaliar, relatorio_html
from app.db.session import SessionLocal
from app.models import Imobiliaria
from app.services.seed import CHAVE_DEMO, semear


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chave", default=CHAVE_DEMO, help="chave pública da imobiliária (padrão: demonstração)")
    parser.add_argument("--saida", default="avaliacao-buscas.html")
    parser.add_argument("--buscas", help="arquivo .txt com uma busca por linha (padrão: as 30 do roadmap)")
    args = parser.parse_args()

    buscas = BUSCAS_PADRAO
    if args.buscas:
        buscas = [b.strip() for b in Path(args.buscas).read_text(encoding="utf-8").splitlines() if b.strip()]

    with SessionLocal() as db:
        if args.chave == CHAVE_DEMO:
            semear(db)
        imobiliaria = db.scalar(select(Imobiliaria).where(Imobiliaria.chave_publica == args.chave))
        if imobiliaria is None:
            print(f"Imobiliária com chave {args.chave} não encontrada.")
            return 2
        resultado = avaliar(db, imobiliaria, buscas)
        db.rollback()  # a avaliação não grava nada
        Path(args.saida).write_text(relatorio_html(resultado, imobiliaria.nome), encoding="utf-8")

    print(f"{len(resultado.buscas)} buscas, {resultado.afirmacoes} afirmações conferidas, "
          f"{len(resultado.violacoes)} violações, {resultado.nao_informados} 'não informado'. "
          f"Motor: {', '.join(sorted(resultado.fonte))}. Custo de IA: US$ {resultado.custo_usd:.4f}.")
    for violacao in resultado.violacoes[:20]:
        print("  VIOLAÇÃO:", violacao)
    print(f"Relatório: {args.saida}")
    return 1 if resultado.violacoes else 0


if __name__ == "__main__":
    sys.exit(main())
