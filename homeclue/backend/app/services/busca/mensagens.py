"""Textos da conversa: resposta, avisos de "não sei", sugestões rápidas e
a mensagem pronta do WhatsApp. Tudo montado a partir dos dados — nenhum
texto livre gerado sobre os imóveis."""

from app.services.busca.avaliacao import Ponto
from app.services.busca.criterios import Criterios, formatar_reais


def resposta(criterios: Criterios, itens: list[tuple[str, int | None]]) -> str:
    """itens: (título, match) já ordenados."""
    if criterios.vazio():
        return ("Me conte o que você procura: comprar ou alugar, bairro, quantos quartos, orçamento "
                "e o que não pode faltar. Pode escrever do seu jeito.")
    if not itens:
        return ("Não encontrei imóveis com esse perfil agora. Deixe seu contato que um corretor te avisa quando surgir "
                "— ou mude algum critério.")
    titulo, match = itens[0]
    bons = sum(1 for _, m in itens if (m or 0) >= 70)
    if bons == 0:
        return (f"Nenhum imóvel atende tudo o que você pediu. Estes são os {len(itens)} mais próximos — "
                "veja em cada um o que bate e o que não bate.")
    plural = "opções" if len(itens) > 1 else "opção"
    return f"Encontrei {len(itens)} {plural}. A que mais combina é “{titulo}”, com {match}% de compatibilidade."


def avisos(pontos_por_imovel: list[list[Ponto]]) -> list[str]:
    """Quando NENHUM resultado informa algo que a pessoa pediu, dizemos isso
    com todas as letras em vez de esconder."""
    if not pontos_por_imovel:
        return []
    por_chave: dict[str, list[Ponto]] = {}
    for pontos in pontos_por_imovel:
        for ponto in pontos:
            por_chave.setdefault(ponto.chave, []).append(ponto)
    saida = []
    for chave, pontos in por_chave.items():
        if chave.startswith(("car:", "desejo:", "perto:")) and all(p.status == "nao_informado" for p in pontos):
            saida.append(f"Nenhum destes anúncios informa “{pontos[0].criterio.lower()}”. Vale perguntar ao corretor.")
    return saida[:3]


def sugestoes(criterios: Criterios) -> list[str]:
    if criterios.vazio():
        return []
    if not criterios.finalidade:
        return ["Quero comprar", "Quero alugar"]
    if not criterios.preco_max:
        if criterios.finalidade == "aluguel":
            return ["Até R$ 1.500 por mês", "Até R$ 2.500 por mês", "Até R$ 4.000 por mês"]
        return ["Até R$ 400 mil", "Até R$ 700 mil", "Até R$ 1 milhão"]
    if not criterios.quartos_min and not ({"terreno", "comercial"} & set(criterios.tipos)):
        return ["2 quartos", "3 quartos", "4 quartos ou mais"]
    opcoes = [("vagas", "Com garagem"), ("pet-friendly", "Que aceite pets"), ("escola", "Perto de escola"),
              ("jardim", "Com quintal"), ("mais_barato", "Um pouco mais barato")]
    saida = []
    for chave, texto in opcoes:
        ja_tem = (chave == "vagas" and criterios.vagas_min) or chave in criterios.caracteristicas \
            or chave in criterios.perto_de
        if not ja_tem:
            saida.append(texto)
    return saida[:3]


def texto_whatsapp(*, imobiliaria: str, titulo: str | None, codigo_ref: str | None, preco: float | None,
                   aluguel: bool, url_anuncio: str | None, resumo: str | None, match: int | None,
                   pontos_ok: list[str], codigo_lead: str, unidade: str | None = None) -> str:
    linhas = [f"Olá! Vim pela busca do site da {imobiliaria}."]
    if unidade:
        linhas.append(f"Tenho interesse na {unidade}.")
    elif titulo:
        ref = f" (cód. {codigo_ref})" if codigo_ref else ""
        valor = f" — {formatar_reais(preco)}{'/mês' if aluguel else ''}" if preco else ""
        linhas.append(f"Tenho interesse no imóvel “{titulo}”{ref}{valor}.")
        if url_anuncio:
            linhas.append(url_anuncio)
    else:
        linhas.append("Quero ajuda para encontrar um imóvel.")
    if resumo:
        linhas.append(f"O que eu procuro: {resumo}.")
    if match is not None and pontos_ok:
        linhas.append(f"Compatibilidade: {match}% (atende: {', '.join(pontos_ok[:5]).lower()}).")
    linhas.append(f"Código Homeclue: {codigo_lead}")
    return "\n".join(linhas)
