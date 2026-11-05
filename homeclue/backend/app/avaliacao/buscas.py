"""As 30 buscas do primeiro passo do roadmap ("testar 30 buscas reais e
conferir se o match e a explicação batem com os anúncios") e o conferidor.

O conferidor não confia no motor: para cada ponto da explicação ele refaz
a checagem direto nos dados do anúncio. Qualquer afirmação sem prova conta
como violação da trava contra invenção.
"""

import re
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models import Imobiliaria
from app.services.busca import evidencia, motor
from app.services.busca.avaliacao import ImovelBusca, Ponto
from app.services.busca.criterios import Criterios
from app.services.vocabulario import COMODOS_DA_CARACTERISTICA, TIPOS_COMODO, normalizar

BUSCAS_PADRAO = [
    "Casa com quintal pra cachorro em Olaria",
    "Apartamento com sala com luz da manhã",
    "Casa perto de escola até 700 mil",
    "Quero alugar um apartamento de 2 quartos que aceite cachorro",
    "Sítio com nascente e fogão a lenha em Lumiar",
    "Casa com lareira e vista para a serra",
    "Apartamento no Centro perto do comércio até 450 mil",
    "Cobertura com churrasqueira e vista panorâmica",
    "Studio mobiliado para alugar no Centro até 1.500",
    "Casa em condomínio fechado com piscina aquecida",
    "Imóvel para investir que aceite financiamento",
    "Casa com escritório para home office numa rua tranquila",
    "Casa para família com 4 quartos e playground",
    "Casa em Teresópolis com lareira",
    "Sítio com cachoeira em Cachoeiras de Macacu",
    "Terreno em condomínio com vista para a serra",
    "Apartamento com elevador e portaria 24 horas",
    "Casa com piscina em Mury até 800 mil",
    "Quero alugar casa com quintal em Olaria",
    "Apartamento com academia e varanda em Teresópolis",
    "Casa com 3 quartos, 2 vagas, até 600 mil",
    "Imóvel com pé-direito alto e terraço",
    "Casa com pomar e horta",
    "Casa térrea sem escadas",
    "Apartamento até 300 mil em Conselheiro Paulino",
    "Casa com sol da tarde na varanda em Braunes",
    "Apartamento perto do hospital",
    "Casa com área gourmet e piscina, 2 suítes",
    "Algo perto da natureza, com vista para as montanhas",
    "Kitnet perto da rodoviária",
]

_FONTES_TEXTO = ("titulo", "descricao", "comodidades", "planta")
_NUMERICOS = {"quartos_min": "quartos", "suites_min": "suites", "banheiros_min": "banheiros", "vagas_min": "vagas"}


@dataclass
class ResultadoAvaliacao:
    buscas: list[dict] = field(default_factory=list)
    afirmacoes: int = 0
    violacoes: list[str] = field(default_factory=list)
    nao_informados: int = 0
    custo_usd: float = 0.0
    fonte: set[str] = field(default_factory=set)


def _numero_na_evidencia(evidencia_texto: str) -> int | None:
    achado = re.match(r"(\d+)", evidencia_texto)
    return int(achado.group(1)) if achado else None


def conferir_ponto(ponto: Ponto, imovel: ImovelBusca, criterios: Criterios) -> str | None:
    """Devolve a descrição da violação, ou None se a afirmação tem prova."""
    if ponto.status == "nao_informado":
        return None
    trecho = ponto.evidencia.strip("“”")
    if ponto.fonte == "planta" and ponto.evidencia.startswith("Planta: "):
        # Referência a um cômodo desenhado pela imobiliária na planta.
        nome = re.sub(r" \([\d.,]+ m²\)$", "", ponto.evidencia[len("Planta: "):])
        tipos = COMODOS_DA_CARACTERISTICA.get(ponto.chave[4:], set())
        existe = any((c.get("nome") or TIPOS_COMODO.get(c.get("tipo"), "")) == nome and c.get("tipo") in tipos
                     for c in imovel.comodos)
        return None if existe else f"cômodo que não está na planta: {ponto.evidencia}"
    if ponto.fonte in _FONTES_TEXTO:
        if not evidencia.trecho_presente(trecho.replace("… ", "").replace(" …", ""), imovel.textos()):
            return f"citação que não está no anúncio: {ponto.evidencia}"
        return None
    if ponto.fonte == "anuncio":
        chave = ponto.chave
        if chave == "tipo":
            ok = (ponto.status == "atende") == (imovel.tipo in criterios.tipos)
        elif chave == "bairro":
            ok = (ponto.status == "atende") == (normalizar(imovel.bairro) in {normalizar(b) for b in criterios.bairros})
        elif chave == "cidade":
            ok = (ponto.status == "atende") == (normalizar(imovel.cidade) in {normalizar(c) for c in criterios.cidades})
        elif chave == "preco_max":
            preco = imovel.preco_para(criterios.finalidade or ("aluguel" if imovel.finalidade == "aluguel" else "venda"))
            ok = (ponto.status == "atende") == (preco <= criterios.preco_max)
        elif chave in _NUMERICOS:
            valor = getattr(imovel, _NUMERICOS[chave])
            ok = valor is not None and _numero_na_evidencia(ponto.evidencia) == valor
            ok = ok and (ponto.status == "atende") == (valor >= getattr(criterios, chave))
        elif chave == "area_min":
            ok = imovel.area_m2 is not None and (ponto.status == "atende") == (imovel.area_m2 >= criterios.area_min)
        elif chave.startswith("car:"):
            slug = chave[4:]
            if ponto.evidencia == "Consta nos itens do anúncio":
                ok = slug in imovel.caracteristicas
            elif slug == "suite":
                ok = bool(imovel.suites)
            else:
                ok = False
        else:
            ok = True
        return None if ok else f"dado do anúncio não confere ({ponto.criterio}: {ponto.evidencia})"
    if ponto.fonte == "contexto":
        categoria = ponto.chave.split(":", 1)[1]
        proximos = (((imovel.contexto or {}).get("categorias") or {}).get(categoria) or {}).get("mais_proximos") or []
        if not proximos or proximos[0]["nome"] not in ponto.evidencia:
            return f"ponto de interesse que não está no contexto: {ponto.evidencia}"
        return None
    if ponto.fonte == "foto":
        fotos = (imovel.analise_fotos or {}).get("fotos", [])
        slug = ponto.chave[4:]
        if ponto.status != "indicio" or not any(slug in f.get("caracteristicas", []) for f in fotos):
            return "item atribuído à foto sem análise que o mostre"
        return None
    return f"fonte desconhecida: {ponto.fonte}"


def avaliar(db: Session, imobiliaria: Imobiliaria, buscas: list[str] | None = None,
            resultados_por_busca: int = 3) -> ResultadoAvaliacao:
    saida = ResultadoAvaliacao()
    for texto in buscas or BUSCAS_PADRAO:
        resultado = motor.executar(db, imobiliaria, texto)
        saida.custo_usd += resultado.uso.custo_usd
        saida.fonte.add(resultado.fonte)
        itens = []
        for item in resultado.itens[:resultados_por_busca]:
            pontos = []
            for ponto in item.pontos:
                violacao = conferir_ponto(ponto, item.dados, resultado.criterios)
                if ponto.status == "nao_informado":
                    saida.nao_informados += 1
                else:
                    saida.afirmacoes += 1
                if violacao:
                    saida.violacoes.append(f"“{texto}” → {item.dados.titulo}: {violacao}")
                pontos.append({**ponto.para_dict(), "violacao": violacao})
            itens.append({"titulo": item.dados.titulo, "match": item.match, "pontos": pontos})
        saida.buscas.append({"texto": texto, "entendido": resultado.criterios.rotulos(), "fonte": resultado.fonte,
                             "mensagem": resultado.mensagem, "avisos": resultado.avisos, "resultados": itens})
    return saida


_ICONES = {"atende": "✓", "parcial": "≈", "indicio": "◐", "nao_informado": "?", "nao_atende": "✗"}


def relatorio_html(avaliacao: ResultadoAvaliacao, nome: str) -> str:
    from html import escape

    linhas = [
        "<!doctype html><html lang='pt-BR'><meta charset='utf-8'><title>Avaliação das buscas — Homeclue</title>",
        "<style>body{font-family:system-ui;max-width:980px;margin:24px auto;padding:0 16px;color:#1B1A17}"
        "h2{margin-top:36px;font-size:18px}.chip{display:inline-block;background:#E3EBE4;border-radius:6px;"
        "padding:2px 8px;margin:2px;font-size:13px}table{border-collapse:collapse;width:100%;font-size:14px;margin:8px 0}"
        "td{border-bottom:1px solid #ddd;padding:6px;vertical-align:top}.ruim{background:#FBE9E6}"
        ".resumo{background:#F1EEE7;padding:14px;border-radius:10px}</style>",
        f"<h1>Avaliação das buscas — {escape(nome)}</h1>",
        f"<div class='resumo'><p><b>{len(avaliacao.buscas)}</b> buscas · <b>{avaliacao.afirmacoes}</b> afirmações "
        f"conferidas · <b>{len(avaliacao.violacoes)}</b> violações da trava contra invenção · "
        f"<b>{avaliacao.nao_informados}</b> pontos “não informado” · motor: {', '.join(sorted(avaliacao.fonte))} · "
        f"custo de IA: US$ {avaliacao.custo_usd:.4f}</p>"
        "<p>Para cada busca: o que foi entendido e os 3 primeiros resultados, com cada ponto e a prova. "
        "Leia como um corretor leria: o match faz sentido? A explicação está certa?</p></div>",
    ]
    for busca in avaliacao.buscas:
        linhas.append(f"<h2>“{escape(busca['texto'])}”</h2><p>"
                      + "".join(f"<span class='chip'>{escape(c)}</span>" for c in busca["entendido"])
                      + f"</p><p><i>{escape(busca['mensagem'])}</i></p>")
        for aviso in busca["avisos"]:
            linhas.append(f"<p>⚠ {escape(aviso)}</p>")
        for resultado in busca["resultados"]:
            linhas.append(f"<p><b>{escape(resultado['titulo'])}</b> — {resultado['match']}%</p><table>")
            for p in resultado["pontos"]:
                classe = " class='ruim'" if p["violacao"] else ""
                linhas.append(f"<tr{classe}><td>{_ICONES[p['status']]} {escape(p['criterio'])}</td>"
                              f"<td>{escape(p['evidencia'])}</td><td>{escape(p['fonte'])}</td>"
                              f"<td>{escape(p['violacao'] or '')}</td></tr>")
            linhas.append("</table>")
    return "\n".join(linhas)



