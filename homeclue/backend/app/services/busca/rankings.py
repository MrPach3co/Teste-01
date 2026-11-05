"""Rankings por perfil: melhor escolha, custo-benefício, família,
investimento e valorização.

Cada posição vem com o motivo, calculado só com dados que existem: preço
por m² comparado com a própria carteira da imobiliária, itens comprovados
no anúncio, contexto do bairro, e o que a imobiliária cadastrou sobre o
bairro. Nada de "este bairro vai valorizar" sem fonte.
"""

from statistics import median

from app.services.busca.avaliacao import ImovelBusca, Ponto, _fmt_distancia, _ponto_caracteristica
from app.services.vocabulario import TIPOS, normalizar

MIN_COMPARAVEIS = 3


def _reais(v: float) -> str:
    return f"R$ {v:,.0f}".replace(",", ".")


def _ppm2(imovel: ImovelBusca, finalidade: str) -> float | None:
    if not imovel.area_m2 or imovel.area_m2 < 10:
        return None
    return imovel.preco_para(finalidade) / imovel.area_m2


def _grupo_finalidade(imovel: ImovelBusca, finalidade: str) -> bool:
    if finalidade == "aluguel":
        return imovel.finalidade in ("aluguel", "venda_aluguel")
    return imovel.finalidade in ("venda", "venda_aluguel")


def _mediana_ppm2(carteira: list[ImovelBusca], finalidade: str, filtro) -> tuple[float | None, int]:
    valores = [p for i in carteira if _grupo_finalidade(i, finalidade) and filtro(i)
               and (p := _ppm2(i, finalidade)) is not None]
    return (median(valores), len(valores)) if len(valores) >= MIN_COMPARAVEIS else (None, len(valores))


def _custo_beneficio(itens, carteira, finalidade):
    saida = []
    for imovel, match in itens:
        ppm2 = _ppm2(imovel, finalidade)
        if ppm2 is None:
            continue
        mediana, n = _mediana_ppm2(carteira, finalidade, lambda i, t=imovel.tipo: i.tipo == t)
        grupo = f"{TIPOS[imovel.tipo].lower()}s" if mediana else "imóveis"
        if mediana is None:
            mediana, n = _mediana_ppm2(carteira, finalidade, lambda i: True)
        if mediana is None:
            continue
        diferenca = ppm2 / mediana - 1
        nota = (match or 50) * max(0.5, min(1.5, mediana / ppm2))
        sufixo = "/mês" if finalidade == "aluguel" else ""
        motivo = (f"{_reais(ppm2)}/m²{sufixo} — {abs(diferenca) * 100:.0f}% "
                  f"{'abaixo' if diferenca < 0 else 'acima'} da média de {grupo} desta imobiliária ({n} anúncios)")
        saida.append((nota, imovel.id, motivo))
    return saida


def _familia(itens):
    saida = []
    for imovel, match in itens:
        textos = imovel.textos()
        motivos, nota = [], 0.0
        if imovel.quartos and imovel.quartos >= 3:
            nota += 2
            motivos.append(f"{imovel.quartos} quartos")
        if imovel.suites:
            nota += 1
            motivos.append("suíte")
        for slug, peso, rotulo in (("jardim", 1.5, "quintal/jardim"), ("playground", 1, "playground"),
                                   ("condominio-fechado", 1, "condomínio fechado"), ("portaria-24h", 0.5, "portaria"),
                                   ("pet-friendly", 0.5, "aceita pets")):
            ponto: Ponto = _ponto_caracteristica(slug, imovel, textos)
            if ponto.status == "atende":
                nota += peso
                motivos.append(rotulo)
        escolas = ((imovel.contexto or {}).get("categorias") or {}).get("escola") or {}
        proximas = escolas.get("mais_proximos") or []
        if proximas and proximas[0]["distancia_m"] <= 1000:
            nota += 1.5
            motivos.append(f"escola a {_fmt_distancia(proximas[0]['distancia_m'])}")
        if imovel.area_m2 and imovel.area_m2 >= 100:
            nota += 1
            motivos.append(f"{imovel.area_m2:g} m²")
        if nota >= 2.5:
            saida.append((nota + (match or 0) / 100, imovel.id, "Para família: " + ", ".join(motivos)))
    return saida


def _investimento(itens, carteira, finalidade):
    if finalidade == "aluguel":
        return []
    saida = []
    for imovel, match in itens:
        if imovel.finalidade == "aluguel":
            continue
        motivos, nota = [], 0.0
        ppm2 = _ppm2(imovel, "venda")
        if ppm2:
            mediana, n = _mediana_ppm2(
                carteira, "venda",
                lambda i, b=normalizar(imovel.bairro), t=imovel.tipo: normalizar(i.bairro) == b and i.tipo == t)
            if mediana and ppm2 < mediana:
                abaixo = 1 - ppm2 / mediana
                nota += abaixo * 10
                motivos.append(f"preço/m² {abaixo * 100:.0f}% abaixo da média do bairro ({n} anúncios)")
        if imovel.area_m2:
            alugueis = [i.preco_para("aluguel") / i.area_m2 for i in carteira
                        if _grupo_finalidade(i, "aluguel") and i.tipo == imovel.tipo and i.area_m2
                        and normalizar(i.cidade) == normalizar(imovel.cidade)]
            if len(alugueis) >= MIN_COMPARAVEIS:
                aluguel_estimado = median(alugueis) * imovel.area_m2
                rendimento = aluguel_estimado / imovel.preco_para("venda") * 100
                nota += rendimento * 4
                taxa = f"{rendimento:.2f}".replace(".", ",")
                motivos.append(f"aluguel estimado {_reais(aluguel_estimado)}/mês (≈{taxa}% ao mês), "
                               f"pela média de {len(alugueis)} aluguéis desta imobiliária")
        if not motivos:
            continue
        if "aceita-financiamento" in imovel.caracteristicas:
            nota += 0.5
            motivos.append("aceita financiamento")
        saida.append((nota + (match or 0) / 200, imovel.id, "; ".join(m[0].upper() + m[1:] for m in motivos)))
    return saida


def _valorizacao(itens, bairros_info: dict[str, dict]):
    pesos = {"alta": 3, "media": 2, "baixa": 1}
    nomes = {"alta": "alto", "media": "médio", "baixa": "baixo"}
    saida = []
    for imovel, match in itens:
        info = bairros_info.get(normalizar(imovel.bairro))
        if not info or info.get("valorizacao") not in pesos:
            continue
        justificativa = info.get("valorizacao_justificativa") or f"potencial de valorização {nomes[info['valorizacao']]}"
        saida.append((pesos[info["valorizacao"]] + (match or 0) / 100, imovel.id,
                      f"Segundo a imobiliária, {imovel.bairro}: {justificativa}"))
    return saida


def calcular(itens: list[tuple[ImovelBusca, int | None]], carteira: list[ImovelBusca], finalidade: str | None,
             bairros_info: dict[str, dict], pontos_por_id: dict[int, list[Ponto]]) -> list[dict]:
    finalidade = finalidade or "venda"
    rankings = []

    def adicionar(chave, titulo, explicacao, candidatos, minimo=2):
        candidatos.sort(key=lambda x: x[0], reverse=True)
        if len(candidatos) >= minimo:
            rankings.append({
                "id": chave, "titulo": titulo, "explicacao": explicacao,
                "itens": [{"imovel_id": i, "motivo": m} for _, i, m in candidatos],
            })

    melhores = []
    for imovel, match in itens:
        pontos = pontos_por_id.get(imovel.id, [])
        ok = sum(1 for p in pontos if p.status == "atende")
        motivo = f"Atende {ok} de {len(pontos)} pontos do seu pedido" if pontos else "Mais recente da carteira"
        melhores.append(((match or 0) + ok / 100, imovel.id, motivo))
    adicionar("melhor", "Melhor escolha", "Maior compatibilidade com o que você pediu.", melhores, minimo=1)
    adicionar("custo_beneficio", "Custo-benefício",
              "Compatibilidade com o seu pedido e preço por m² comparado com imóveis parecidos desta imobiliária.",
              _custo_beneficio(itens, carteira, finalidade))
    adicionar("familia", "Família", "Quartos, suíte, quintal, segurança e escola por perto — só o que o anúncio comprova.",
              _familia(itens))
    adicionar("investimento", "Investimento",
              "Preço por m² abaixo da média do bairro e aluguel estimado com base nos aluguéis desta imobiliária.",
              _investimento(itens, carteira, finalidade))
    adicionar("valorizacao", "Valorização", "Conforme a avaliação da própria imobiliária sobre cada bairro.",
              _valorizacao(itens, bairros_info), minimo=1)
    return rankings
