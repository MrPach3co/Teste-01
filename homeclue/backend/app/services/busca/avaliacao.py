"""Match explicado: avalia um imóvel contra os critérios, ponto a ponto.

Cada ponto diz o que foi pedido, se o imóvel atende, e A PROVA (o dado ou o
trecho do anúncio). O que o anúncio não informa aparece como "não
informado" — nunca é presumido. A taxa de match é a média ponderada dos
pontos, então é sempre explicável: ela vem só do que está na lista.
"""

from dataclasses import asdict, dataclass, field

from app.models import Imovel
from app.services.busca import evidencia
from app.services.busca.criterios import Criterios, formatar_reais
from app.services.vocabulario import (
    CARACTERISTICAS,
    CATEGORIAS_CONTEXTO,
    COMODOS_DA_CARACTERISTICA,
    DESEJOS_CONHECIDOS,
    NOMES_PERTO_DE,
    TERMOS_EVIDENCIA,
    TIPOS,
    TIPOS_COMODO,
    normalizar,
)

FATOR_STATUS = {"atende": 1.0, "parcial": 0.6, "indicio": 0.7, "nao_informado": 0.3, "nao_atende": 0.0}

PESOS = {
    "tipo": 2.0, "cidade": 2.5, "bairro": 2.0, "preco_max": 3.0, "preco_min": 1.0, "quartos_min": 2.0,
    "suites_min": 1.2, "banheiros_min": 0.8, "vagas_min": 1.0, "area_min": 1.0, "caracteristica": 1.0,
    "perto_de": 1.0, "desejo": 1.2,
}


@dataclass
class Ponto:
    chave: str
    criterio: str
    status: str
    evidencia: str
    fonte: str
    peso: float
    foto: str | None = None

    def para_dict(self) -> dict:
        return asdict(self)


@dataclass
class ImovelBusca:
    """Retrato de um anúncio para a busca (independe do banco)."""

    id: int
    titulo: str
    tipo: str
    finalidade: str
    preco: float
    preco_aluguel: float | None
    bairro: str
    cidade: str
    quartos: int | None = None
    suites: int | None = None
    banheiros: int | None = None
    vagas: int | None = None
    area_m2: float | None = None
    area_terreno: float | None = None
    condominio: float | None = None
    descricao: str = ""
    caracteristicas: list[str] = field(default_factory=list)
    comodidades: list[str] = field(default_factory=list)
    comodos: list[dict] = field(default_factory=list)
    contexto: dict | None = None
    analise_fotos: dict | None = None

    @classmethod
    def de_imovel(cls, imovel: Imovel) -> "ImovelBusca":
        return cls(
            id=imovel.id, titulo=imovel.titulo, tipo=imovel.tipo, finalidade=imovel.finalidade,
            preco=imovel.preco, preco_aluguel=imovel.preco_aluguel, bairro=imovel.bairro, cidade=imovel.cidade,
            quartos=imovel.quartos, suites=imovel.suites, banheiros=imovel.banheiros, vagas=imovel.vagas,
            area_m2=imovel.area_m2, area_terreno=imovel.area_terreno, condominio=imovel.condominio,
            descricao=imovel.descricao or "", caracteristicas=list(imovel.caracteristicas or []),
            comodidades=list(imovel.comodidades or []), comodos=list((imovel.planta or {}).get("comodos") or []),
            contexto=imovel.contexto, analise_fotos=imovel.analise_fotos,
        )

    def preco_para(self, finalidade: str | None) -> float:
        if finalidade == "aluguel" and self.finalidade == "venda_aluguel" and self.preco_aluguel:
            return self.preco_aluguel
        return self.preco

    def textos(self) -> list[tuple[str, str]]:
        """Tudo que a imobiliária escreveu sobre o imóvel — a única fonte
        válida de evidência textual."""
        textos = [("titulo", self.titulo), ("descricao", self.descricao)]
        if self.comodidades:
            textos.append(("comodidades", ". ".join(self.comodidades)))
        notas = [
            f"{c.get('nome') or TIPOS_COMODO.get(c.get('tipo', ''), '')}: {c['notas']}"
            for c in self.comodos if c.get("notas")
        ]
        if notas:
            textos.append(("planta", ". ".join(notas)))
        return textos


def _fmt_distancia(metros: float) -> str:
    return f"{metros / 1000:.1f} km".replace(".", ",") if metros >= 1000 else f"{round(metros / 10) * 10:.0f} m"


def _preco_rotulo(valor: float, finalidade: str) -> str:
    return formatar_reais(valor) + ("/mês" if finalidade == "aluguel" else "")


def _numerico(chave, criterio_rotulo, pedido, valor, singular, plural, peso_chave, tolerancia_parcial=1):
    if valor is None:
        return Ponto(chave, criterio_rotulo, "nao_informado", f"O anúncio não informa {plural}", "anuncio", PESOS[peso_chave])
    texto = f"{valor} {singular if valor == 1 else plural}"
    if valor >= pedido:
        status = "atende"
    elif valor >= pedido - tolerancia_parcial:
        status = "parcial"
    else:
        status = "nao_atende"
    return Ponto(chave, criterio_rotulo, status, texto, "anuncio", PESOS[peso_chave])


def _ponto_caracteristica(slug: str, imovel: ImovelBusca, textos) -> Ponto:
    rotulo = CARACTERISTICAS[slug]
    chave = f"car:{slug}"
    peso = PESOS["caracteristica"]

    # Negação explícita no texto pesa mais que a lista de itens (o texto é mais específico).
    achado = evidencia.procurar(TERMOS_EVIDENCIA.get(slug, [rotulo]), textos)
    if achado and achado.status == "nao_atende":
        return Ponto(chave, rotulo, "nao_atende", f"“{achado.trecho}”", achado.fonte, peso)

    if slug in imovel.caracteristicas:
        return Ponto(chave, rotulo, "atende", "Consta nos itens do anúncio", "anuncio", peso)
    if slug == "suite" and imovel.suites:
        return Ponto(chave, rotulo, "atende", f"{imovel.suites} suíte{'s' if imovel.suites > 1 else ''}", "anuncio", peso)
    if achado:
        return Ponto(chave, rotulo, "atende", f"“{achado.trecho}”", achado.fonte, peso)

    tipos_comodo = COMODOS_DA_CARACTERISTICA.get(slug, set())
    for comodo in imovel.comodos:
        if comodo.get("tipo") in tipos_comodo:
            nome = comodo.get("nome") or TIPOS_COMODO.get(comodo["tipo"], comodo["tipo"])
            area = f" ({comodo['area_m2']:g} m²)" if comodo.get("area_m2") else ""
            return Ponto(chave, rotulo, "atende", f"Planta: {nome}{area}", "planta", peso)

    for foto in (imovel.analise_fotos or {}).get("fotos", []):
        if slug in (foto.get("caracteristicas") or []):
            return Ponto(chave, rotulo, "indicio", "Parece aparecer em uma foto do anúncio (análise automática — confira na foto)",
                         "foto", peso, foto=foto.get("url"))

    return Ponto(chave, rotulo, "nao_informado", "O anúncio não menciona", "anuncio", peso)


def _ponto_perto_de(categoria: str, imovel: ImovelBusca) -> Ponto:
    nome = NOMES_PERTO_DE[categoria]
    chave = f"perto:{categoria}"
    rotulo = f"Perto de {nome}"
    peso = PESOS["perto_de"]
    contexto = (imovel.contexto or {}).get("categorias") if imovel.contexto else None
    if contexto is None:
        return Ponto(chave, rotulo, "nao_informado", "Contexto do bairro ainda não calculado", "contexto", peso)
    dados = contexto.get(categoria) or {}
    proximos = dados.get("mais_proximos") or []
    if not proximos:
        raio = _fmt_distancia(dados.get("raio_m", 0) or 0)
        return Ponto(chave, rotulo, "nao_informado", f"Nada mapeado em até {raio} (OpenStreetMap)", "contexto", peso)
    mais_perto = proximos[0]
    limite = CATEGORIAS_CONTEXTO[categoria][1]
    texto = f"{mais_perto['nome']} a {_fmt_distancia(mais_perto['distancia_m'])} (OpenStreetMap)"
    if mais_perto["distancia_m"] <= limite:
        status = "atende"
    elif mais_perto["distancia_m"] <= limite * 1.6:
        status = "parcial"
    else:
        status = "nao_atende"
    return Ponto(chave, rotulo, status, texto, "contexto", peso)


def _ponto_desejo(indice: int, desejo: str, textos) -> Ponto:
    chave = f"desejo:{indice}"
    rotulo = desejo[0].upper() + desejo[1:]
    peso = PESOS["desejo"]
    conhecido = DESEJOS_CONHECIDOS.get(desejo)
    if conhecido:
        achado = evidencia.procurar(conhecido[1], textos)
    else:
        achado = evidencia.procurar_frase_livre(desejo, textos)
    if achado:
        return Ponto(chave, rotulo, achado.status, f"“{achado.trecho}”", achado.fonte, peso)
    return Ponto(chave, rotulo, "nao_informado", "O anúncio não fala sobre isso", "anuncio", peso)


def avaliar(imovel: ImovelBusca, c: Criterios) -> list[Ponto]:
    pontos: list[Ponto] = []
    textos = imovel.textos()

    if c.tipos:
        ok = imovel.tipo in c.tipos
        pontos.append(Ponto("tipo", " ou ".join(TIPOS[t] for t in c.tipos), "atende" if ok else "nao_atende",
                            TIPOS.get(imovel.tipo, imovel.tipo), "anuncio", PESOS["tipo"]))
    if c.cidades:
        ok = normalizar(imovel.cidade) in {normalizar(x) for x in c.cidades}
        pontos.append(Ponto("cidade", " ou ".join(c.cidades), "atende" if ok else "nao_atende",
                            f"Fica em {imovel.cidade}", "anuncio", PESOS["cidade"]))
    if c.bairros:
        ok = normalizar(imovel.bairro) in {normalizar(x) for x in c.bairros}
        pontos.append(Ponto("bairro", " ou ".join(c.bairros), "atende" if ok else "nao_atende",
                            f"Fica em {imovel.bairro}", "anuncio", PESOS["bairro"]))

    finalidade = c.finalidade or ("aluguel" if imovel.finalidade == "aluguel" else "venda")
    preco = imovel.preco_para(finalidade)
    if c.preco_max:
        if preco <= c.preco_max:
            status = "atende"
        elif preco <= c.preco_max * 1.1:
            status = "parcial"
        else:
            status = "nao_atende"
        detalhe = _preco_rotulo(preco, finalidade)
        if status != "atende":
            detalhe += f" ({(preco / c.preco_max - 1) * 100:.0f}% acima)"
        pontos.append(Ponto("preco_max", f"Até {_preco_rotulo(c.preco_max, finalidade)}", status, detalhe,
                            "anuncio", PESOS["preco_max"]))
    if c.preco_min:
        pontos.append(Ponto("preco_min", f"A partir de {_preco_rotulo(c.preco_min, finalidade)}",
                            "atende" if preco >= c.preco_min else "nao_atende", _preco_rotulo(preco, finalidade),
                            "anuncio", PESOS["preco_min"]))
    if c.quartos_min:
        pontos.append(_numerico("quartos_min", f"{c.quartos_min}+ quartos", c.quartos_min, imovel.quartos,
                                "quarto", "quartos", "quartos_min"))
    if c.suites_min:
        pontos.append(_numerico("suites_min", f"{c.suites_min}+ suítes", c.suites_min, imovel.suites,
                                "suíte", "suítes", "suites_min"))
    if c.banheiros_min:
        pontos.append(_numerico("banheiros_min", f"{c.banheiros_min}+ banheiros", c.banheiros_min, imovel.banheiros,
                                "banheiro", "banheiros", "banheiros_min"))
    if c.vagas_min:
        pontos.append(_numerico("vagas_min", f"{c.vagas_min}+ vagas", c.vagas_min, imovel.vagas,
                                "vaga", "vagas", "vagas_min"))
    if c.area_min:
        area = imovel.area_m2
        if area is None:
            pontos.append(Ponto("area_min", f"{c.area_min:g}+ m²", "nao_informado", "O anúncio não informa a área",
                                "anuncio", PESOS["area_min"]))
        else:
            status = "atende" if area >= c.area_min else ("parcial" if area >= c.area_min * 0.9 else "nao_atende")
            pontos.append(Ponto("area_min", f"{c.area_min:g}+ m²", status, f"{area:g} m²", "anuncio", PESOS["area_min"]))

    for slug in c.caracteristicas:
        pontos.append(_ponto_caracteristica(slug, imovel, textos))
    for categoria in c.perto_de:
        pontos.append(_ponto_perto_de(categoria, imovel))
    for i, desejo in enumerate(c.desejos):
        pontos.append(_ponto_desejo(i, desejo, textos))
    return pontos


def taxa_de_match(pontos: list[Ponto]) -> int | None:
    total = sum(p.peso for p in pontos)
    if not total:
        return None
    obtido = sum(p.peso * FATOR_STATUS[p.status] for p in pontos)
    return max(0, min(100, round(100 * obtido / total)))
