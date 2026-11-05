"""Leitura dos feeds XML que as imobiliárias já mandam para os portais.

Formatos suportados:
- VRSync (Grupo OLX: ZAP, VivaReal, OLX) — <ListingDataFeed><Listings><Listing>…
- "Carga" / <Imovel> (padrão ZAP antigo, e a família de formatos parecidos
  que muitos sistemas brasileiros exportam): a leitura é tolerante a nomes
  de campo diferentes (CodigoImovel, Codigo, Referencia…).

O XML é lido com defusedxml (bloqueia entidades externas e "billion laughs").
"""

import re
from dataclasses import dataclass, field

from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException

from app.services.vocabulario import caracteristica_de_item_feed, normalizar, tipo_do_texto


class FormatoNaoReconhecido(Exception):
    pass


@dataclass
class ImovelFeed:
    codigo: str
    titulo: str
    tipo: str
    finalidade: str
    preco: float
    preco_aluguel: float | None = None
    condominio: float | None = None
    iptu: float | None = None
    bairro: str = ""
    cidade: str = ""
    uf: str | None = None
    endereco: str | None = None
    mostrar_endereco: bool = False
    latitude: float | None = None
    longitude: float | None = None
    quartos: int | None = None
    suites: int | None = None
    banheiros: int | None = None
    vagas: int | None = None
    area_m2: float | None = None
    area_terreno: float | None = None
    descricao: str = ""
    caracteristicas: list[str] = field(default_factory=list)
    comodidades: list[str] = field(default_factory=list)
    fotos: list[dict] = field(default_factory=list)
    video_url: str | None = None
    url_anuncio: str | None = None
    planta_url: str | None = None


@dataclass
class ResultadoLeitura:
    formato: str
    imoveis: list[ImovelFeed]
    erros: list[str]


# ---------- utilidades ----------

def _nome(el) -> str:
    return el.tag.split("}")[-1] if isinstance(el.tag, str) else ""


def _chave(nome: str) -> str:
    return re.sub(r"[^a-z0-9]", "", normalizar(nome))


def _texto(el) -> str:
    return " ".join("".join(el.itertext()).split()) if el is not None else ""


def _filho(el, *nomes):
    if el is None:
        return None
    procurados = {_chave(n) for n in nomes}
    for filho in el:
        if _chave(_nome(filho)) in procurados:
            return filho
    return None


def _texto_filho(el, *nomes) -> str:
    return _texto(_filho(el, *nomes))


def _numero(valor: str | None) -> float | None:
    if not valor:
        return None
    limpo = re.sub(r"[^\d,.-]", "", valor)
    if not limpo:
        return None
    if "," in limpo and "." in limpo:
        limpo = limpo.replace(".", "").replace(",", ".") if limpo.rfind(",") > limpo.rfind(".") else limpo.replace(",", "")
    elif "," in limpo:
        limpo = limpo.replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(\.\d{3})+", limpo):
        limpo = limpo.replace(".", "")
    try:
        return float(limpo)
    except ValueError:
        return None


def _inteiro(valor: str | None) -> int | None:
    numero = _numero(valor)
    if numero is None or numero < 0 or numero > 100:
        return None
    return int(numero)


def _area(valor: str | None) -> float | None:
    numero = _numero(valor)
    return numero if numero and 0 < numero < 10_000_000 else None


def _coordenada(valor: str | None, limite: float) -> float | None:
    numero = _numero(valor)
    if numero is None or numero == 0 or abs(numero) > limite:
        return None
    return numero


def _url(valor: str | None) -> str | None:
    valor = (valor or "").strip()
    return valor if re.match(r"^https?://\S+$", valor) and len(valor) <= 500 else None


def _separar_caracteristicas(itens: list[str]) -> tuple[list[str], list[str]]:
    slugs, outros = [], []
    for item in itens:
        item = " ".join(item.split())
        if not item:
            continue
        slug = caracteristica_de_item_feed(item)
        if slug and slug not in slugs:
            slugs.append(slug)
        elif not slug and item not in outros and len(item) <= 80:
            outros.append(item)
    return slugs, outros[:40]


# ---------- VRSync ----------

_TIPO_VRSYNC = [
    (r"penthouse|cobertura", "cobertura"),
    (r"kitnet|studio|loft", "studio"),
    (r"apartment|flat|apartamento", "apartamento"),
    (r"farm|ranch|agricultural|chacara|sitio|fazenda|rural", "rural"),
    (r"land|lot\b|terreno|lote", "terreno"),
    (r"home|house|condo|village|sobrado|casa", "casa"),
    (r"office|business|commercial|store|shop|building|warehouse|industrial|consult|loja|sala|galpao", "comercial"),
]


def _tipo_vrsync(texto: str, uso: str) -> str:
    t = normalizar(texto)
    if "commercial" in normalizar(uso) and not re.search(r"residential", t):
        if re.search(r"land|lot", t):
            return "terreno"
        return "comercial"
    for padrao, tipo in _TIPO_VRSYNC:
        if re.search(padrao, t):
            return tipo
    return tipo_do_texto(texto) or "casa"


def _ler_vrsync(raiz) -> tuple[list[ImovelFeed], list[str]]:
    imoveis, erros = [], []
    for listing in raiz.iter():
        if _nome(listing) != "Listing":
            continue
        codigo = _texto_filho(listing, "ListingID")
        try:
            detalhes = _filho(listing, "Details")
            local = _filho(listing, "Location")
            transacao = normalizar(_texto_filho(listing, "TransactionType"))
            venda = _numero(_texto_filho(detalhes, "ListPrice"))
            aluguel = _numero(_texto_filho(detalhes, "RentalPrice"))
            if "sale" in transacao and "rent" in transacao:
                finalidade = "venda_aluguel"
            elif "rent" in transacao:
                finalidade = "aluguel"
            else:
                finalidade = "venda"
            if finalidade == "venda_aluguel" and not (venda and aluguel):
                finalidade = "venda" if venda else "aluguel"
            preco = aluguel if finalidade == "aluguel" else venda
            if not codigo:
                raise ValueError("sem ListingID")
            if not preco or preco <= 0:
                raise ValueError("sem preço")
            tipo = _tipo_vrsync(_texto_filho(detalhes, "PropertyType"), _texto_filho(detalhes, "UsageType"))
            bairro = _texto_filho(local, "Neighborhood")
            cidade = _texto_filho(local, "City")
            if not bairro or not cidade:
                raise ValueError("sem bairro ou cidade")

            itens = [_texto(f) for f in (_filho(detalhes, "Features") or [])]
            slugs, outros = _separar_caracteristicas(itens)

            fotos, video, planta = [], None, None
            for item in (_filho(listing, "Media") or []):
                url = _url(_texto(item))
                meio = normalizar(item.get("medium", "image"))
                if not url:
                    continue
                if meio == "image":
                    foto = {"url": url, "legenda": item.get("caption", "")[:120]}
                    if item.get("primary", "").lower() == "true":
                        fotos.insert(0, foto)
                    else:
                        fotos.append(foto)
                elif meio == "video" and video is None:
                    video = url
                elif "floor" in meio or "planta" in meio:
                    planta = planta or url

            exibir = normalizar((local.get("displayAddress") if local is not None else "") or "")
            rua = _texto_filho(local, "Address")
            numero_rua = _texto_filho(local, "StreetNumber")
            uf_el = _filho(local, "State")
            uf = (uf_el.get("abbreviation") if uf_el is not None else None) or None
            imoveis.append(ImovelFeed(
                codigo=codigo[:80],
                titulo=(_texto_filho(listing, "Title") or f"{tipo.capitalize()} em {bairro}")[:200],
                tipo=tipo,
                finalidade=finalidade,
                preco=preco,
                preco_aluguel=aluguel if finalidade == "venda_aluguel" else None,
                condominio=_numero(_texto_filho(detalhes, "PropertyAdministrationFee")),
                iptu=_numero(_texto_filho(detalhes, "YearlyTax")),
                bairro=bairro[:120],
                cidade=cidade[:120],
                uf=uf[:2].upper() if uf else None,
                endereco=(f"{rua}, {numero_rua}" if rua and numero_rua and exibir == "all" else rua or None),
                mostrar_endereco=exibir in ("all", "street"),
                latitude=_coordenada(_texto_filho(local, "Latitude"), 90),
                longitude=_coordenada(_texto_filho(local, "Longitude"), 180),
                quartos=_inteiro(_texto_filho(detalhes, "Bedrooms")),
                suites=_inteiro(_texto_filho(detalhes, "Suites")),
                banheiros=_inteiro(_texto_filho(detalhes, "Bathrooms")),
                vagas=_inteiro(_texto_filho(detalhes, "Garage")),
                area_m2=_area(_texto_filho(detalhes, "LivingArea", "ConstructedArea", "UsableArea")),
                area_terreno=_area(_texto_filho(detalhes, "LotArea")),
                descricao=_texto_filho(detalhes, "Description")[:8000],
                caracteristicas=slugs,
                comodidades=outros,
                fotos=fotos[:40],
                video_url=video,
                url_anuncio=_url(_texto_filho(listing, "DetailViewUrl")),
                planta_url=planta,
            ))
        except ValueError as erro:
            erros.append(f"Imóvel {codigo or '(sem código)'}: {erro}")
    return imoveis, erros


# ---------- Carga / <Imovel> ----------

_SIM = {"1", "sim", "s", "true", "yes", "y", "x"}


def _ler_carga(raiz) -> tuple[list[ImovelFeed], list[str]]:
    imoveis, erros = [], []
    elementos = [el for el in raiz.iter() if _chave(_nome(el)) in ("imovel", "property", "anuncio")]
    for el in elementos:
        def campo(*nomes):
            return _texto_filho(el, *nomes)

        codigo = campo("CodigoImovel", "Codigo", "CodigoReferencia", "Referencia", "Ref", "Id", "IdImovel")
        try:
            if not codigo:
                raise ValueError("sem código")
            venda = _numero(campo("PrecoVenda", "ValorVenda", "PrecoDeVenda"))
            aluguel = _numero(campo("PrecoLocacao", "ValorLocacao", "ValorAluguel", "PrecoAluguel", "PrecoLocacaoMensal"))
            generico = _numero(campo("Preco", "Valor"))
            finalidade_txt = normalizar(campo("Finalidade", "Transacao", "TipoNegocio", "TipoOferta"))
            if venda and aluguel:
                finalidade = "venda_aluguel"
            elif aluguel or re.search(r"alug|loca", finalidade_txt):
                finalidade = "aluguel"
            else:
                finalidade = "venda"
            if finalidade == "aluguel":
                preco = aluguel or generico
            else:
                preco = venda or generico
            if not preco or preco <= 0:
                raise ValueError("sem preço")
            texto_tipo = " ".join([campo("TipoImovel", "Tipo"), campo("SubTipoImovel", "Subtipo", "Categoria")])
            tipo = tipo_do_texto(texto_tipo) or _tipo_vrsync(texto_tipo, "") or "casa"
            bairro, cidade = campo("Bairro"), campo("Cidade", "Municipio")
            if not bairro or not cidade:
                raise ValueError("sem bairro ou cidade")

            itens: list[str] = []
            for filho in el:
                nome = _nome(filho)
                if len(filho) == 0 and normalizar(_texto(filho)) in _SIM and caracteristica_de_item_feed(nome):
                    itens.append(nome)
            for container in (_filho(el, "Caracteristicas", "Features", "Itens", "Infraestrutura") or []):
                itens.append(_texto(container))
            slugs, outros = _separar_caracteristicas(itens)

            fotos = []
            for container in el.iter():
                if _chave(_nome(container)) not in ("fotos", "imagens", "images", "midias"):
                    continue
                for foto in container:
                    url = _url(_texto_filho(foto, "URLArquivo", "Url", "Link", "Caminho", "Arquivo") or _texto(foto))
                    if url:
                        principal = normalizar(_texto_filho(foto, "Principal", "Destaque")) in _SIM
                        item = {"url": url, "legenda": _texto_filho(foto, "Descricao", "Legenda")[:120]}
                        if principal:
                            fotos.insert(0, item)
                        else:
                            fotos.append(item)

            rua, numero_rua = campo("Endereco", "Logradouro"), campo("Numero")
            imoveis.append(ImovelFeed(
                codigo=codigo[:80],
                titulo=(campo("TituloImovel", "Titulo", "TituloAnuncio", "Title") or f"{tipo.capitalize()} em {bairro}")[:200],
                tipo=tipo,
                finalidade=finalidade,
                preco=preco,
                preco_aluguel=aluguel if finalidade == "venda_aluguel" else None,
                condominio=_numero(campo("PrecoCondominio", "ValorCondominio", "Condominio")),
                iptu=_numero(campo("ValorIPTU", "IPTU")),
                bairro=bairro[:120],
                cidade=cidade[:120],
                uf=(campo("UF", "Estado")[:2].upper() or None),
                endereco=(f"{rua}, {numero_rua}" if rua and numero_rua else rua or None),
                mostrar_endereco=normalizar(campo("MostrarEndereco", "ExibirEndereco")) in _SIM,
                latitude=_coordenada(campo("Latitude", "Lat", "GMapsLatitude"), 90),
                longitude=_coordenada(campo("Longitude", "Lng", "Lon", "GMapsLongitude"), 180),
                quartos=_inteiro(campo("QtdDormitorios", "Dormitorios", "Quartos", "QtdQuartos")),
                suites=_inteiro(campo("QtdSuites", "Suites")),
                banheiros=_inteiro(campo("QtdBanheiros", "Banheiros")),
                vagas=_inteiro(campo("QtdVagas", "Vagas", "VagasGaragem", "Garagens")),
                area_m2=_area(campo("AreaUtil", "AreaPrivativa", "AreaConstruida", "Area")),
                area_terreno=_area(campo("AreaTotal", "AreaTerreno")),
                descricao=campo("Observacao", "Descricao", "DescricaoImovel", "Description")[:8000],
                caracteristicas=slugs,
                comodidades=outros,
                fotos=fotos[:40],
                video_url=_url(campo("Video", "UrlVideo", "Youtube", "LinkVideo")),
                url_anuncio=_url(campo("UrlAnuncio", "LinkAnuncio", "Link")),
            ))
        except ValueError as erro:
            erros.append(f"Imóvel {codigo or '(sem código)'}: {erro}")
    return imoveis, erros


def ler(conteudo: bytes) -> ResultadoLeitura:
    try:
        raiz = ElementTree.fromstring(conteudo, forbid_dtd=False)
    except DefusedXmlException:
        raise FormatoNaoReconhecido("O XML usa recursos bloqueados por segurança (entidades externas).")
    except ElementTree.ParseError as erro:
        raise FormatoNaoReconhecido(f"O arquivo não é um XML válido ({erro}).")

    if _nome(raiz) == "ListingDataFeed" or any(_nome(e) == "Listing" for e in raiz.iter()):
        imoveis, erros = _ler_vrsync(raiz)
        formato = "VRSync (ZAP/VivaReal/OLX)"
    elif any(_chave(_nome(e)) in ("imovel", "property", "anuncio") for e in raiz.iter()):
        imoveis, erros = _ler_carga(raiz)
        formato = "Carga / Imóvel (padrão ZAP)"
    else:
        raise FormatoNaoReconhecido(
            "Não reconhecemos o formato deste feed. Mande um exemplo para o suporte que a gente adiciona."
        )

    # Códigos repetidos no mesmo feed: fica o primeiro.
    vistos, unicos = set(), []
    for imovel in imoveis:
        if imovel.codigo in vistos:
            erros.append(f"Imóvel {imovel.codigo}: código repetido no feed (mantido o primeiro)")
            continue
        vistos.add(imovel.codigo)
        unicos.append(imovel)
    return ResultadoLeitura(formato=formato, imoveis=unicos, erros=erros)

