"""Contexto do bairro: escolas, saúde, comércio, transporte, natureza e
segurança perto do imóvel, a partir do OpenStreetMap.

- Coordenadas: as do feed; sem elas, o centro do bairro (Nominatim),
  marcado como aproximado.
- Pontos de interesse: Overpass API, num raio por categoria.
- Tudo fica em cache no banco e o resultado é guardado no imóvel, então a
  busca nunca espera por isso. Dados © colaboradores do OpenStreetMap (ODbL).

Observação honesta: o OpenStreetMap pode estar incompleto em cidades do
interior. Por isso "nada encontrado" vira "não informado" na busca, nunca
"não tem".
"""

import logging
import math
import threading
import time
from datetime import timedelta

import httpx
from sqlalchemy.orm import Session

from app.core.config import obter_settings
from app.core.planos import CONTEXTO_BAIRRO, tem_recurso
from app.core.tempo import agora_utc
from app.models import Imobiliaria, Imovel, Tarefa
from app.services import cache
from app.services.tarefas import executor
from app.services.vocabulario import CATEGORIAS_CONTEXTO

logger = logging.getLogger(__name__)

settings = obter_settings()

# categoria -> (filtros Overpass, raio de busca em metros)
CONSULTAS: dict[str, tuple[list[str], int]] = {
    "escola": (['nwr["amenity"~"^(school|kindergarten|college|university)$"]'], 2000),
    "saude": (['nwr["amenity"~"^(hospital|clinic|doctors)$"]', 'nwr["healthcare"~"^(hospital|clinic|centre)$"]'], 3000),
    "comercio": (['nwr["shop"~"^(supermarket|convenience|bakery|butcher|greengrocer|mall|department_store)$"]',
                  'nwr["amenity"~"^(pharmacy|bank|marketplace)$"]'], 1500),
    "transporte": (['nwr["highway"="bus_stop"]', 'nwr["amenity"="bus_station"]'], 1000),
    "natureza": (['nwr["leisure"~"^(park|nature_reserve)$"]', 'nwr["tourism"="viewpoint"]',
                  'nwr["waterway"="waterfall"]', 'nwr["natural"="peak"]["name"]', 'nwr["boundary"="protected_area"]["name"]'],
                 4000),
    "seguranca": (['nwr["amenity"~"^(police|fire_station)$"]'], 3000),
}

_ROTULOS = {
    "school": "Escola", "kindergarten": "Educação infantil", "college": "Faculdade", "university": "Universidade",
    "hospital": "Hospital", "clinic": "Clínica", "doctors": "Consultório", "centre": "Centro de saúde",
    "supermarket": "Supermercado", "convenience": "Mercadinho", "bakery": "Padaria", "butcher": "Açougue",
    "greengrocer": "Hortifrúti", "mall": "Shopping", "department_store": "Loja de departamentos",
    "pharmacy": "Farmácia", "bank": "Banco", "marketplace": "Feira", "bus_stop": "Ponto de ônibus",
    "bus_station": "Rodoviária", "park": "Parque", "nature_reserve": "Reserva natural", "viewpoint": "Mirante",
    "waterfall": "Cachoeira", "peak": "Pico", "protected_area": "Área de proteção", "police": "Polícia",
    "fire_station": "Bombeiros",
}

_trava_nominatim = threading.Lock()
_ultima_chamada_nominatim = [0.0]


def distancia_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _http() -> httpx.Client:
    return httpx.Client(timeout=httpx.Timeout(45.0, connect=15.0), headers={"User-Agent": settings.user_agent})


def _nominatim(params: dict) -> list[dict]:
    """GET no Nominatim respeitando a política de no máximo 1 requisição por segundo."""
    with _trava_nominatim:
        espera = 1.5 - (time.monotonic() - _ultima_chamada_nominatim[0])
        if espera > 0:
            time.sleep(espera)
        try:
            with _http() as http:
                resposta = http.get(f"{settings.nominatim_url}/search", params={"format": "jsonv2", **params})
        finally:
            _ultima_chamada_nominatim[0] = time.monotonic()
    resposta.raise_for_status()
    return resposta.json()


def geocodificar(db: Session, bairro: str, cidade: str, uf: str | None) -> tuple[float, float] | None:
    consulta = ", ".join(p for p in [bairro, cidade, uf, "Brasil"] if p)
    chave = cache.chave_de("geo", consulta.lower())
    guardado = cache.obter(db, chave)
    if guardado is not None:
        return (guardado["lat"], guardado["lon"]) if guardado.get("lat") is not None else None

    achados = _nominatim({"q": consulta, "limit": 1, "countrycodes": "br"})
    if not achados:
        cache.guardar(db, chave, {"lat": None, "lon": None}, timedelta(days=30))
        return None
    lat, lon = float(achados[0]["lat"]), float(achados[0]["lon"])
    cache.guardar(db, chave, {"lat": lat, "lon": lon}, timedelta(days=180))
    return lat, lon


def _consulta_overpass(lat: float, lon: float) -> str:
    partes = []
    for filtros, raio in CONSULTAS.values():
        for filtro in filtros:
            partes.append(f"{filtro}(around:{raio},{lat:.6f},{lon:.6f});")
    return f"[out:json][timeout:40];({''.join(partes)});out center tags;"


def _categoria(tags: dict) -> tuple[str, str] | None:
    amenity, shop = tags.get("amenity"), tags.get("shop")
    if amenity in ("school", "kindergarten", "college", "university"):
        return "escola", amenity
    if amenity in ("hospital", "clinic", "doctors"):
        return "saude", amenity
    if tags.get("healthcare") in ("hospital", "clinic", "centre"):
        return "saude", tags["healthcare"]
    if shop in ("supermarket", "convenience", "bakery", "butcher", "greengrocer", "mall", "department_store"):
        return "comercio", shop
    if amenity in ("pharmacy", "bank", "marketplace"):
        return "comercio", amenity
    if tags.get("highway") == "bus_stop":
        return "transporte", "bus_stop"
    if amenity == "bus_station":
        return "transporte", "bus_station"
    if tags.get("leisure") in ("park", "nature_reserve"):
        return "natureza", tags["leisure"]
    if tags.get("tourism") == "viewpoint":
        return "natureza", "viewpoint"
    if tags.get("waterway") == "waterfall":
        return "natureza", "waterfall"
    if tags.get("natural") == "peak":
        return "natureza", "peak"
    if tags.get("boundary") == "protected_area":
        return "natureza", "protected_area"
    if amenity in ("police", "fire_station"):
        return "seguranca", amenity
    return None


_TAGS_UTEIS = ("name", "amenity", "shop", "highway", "leisure", "tourism", "waterway", "natural", "boundary",
               "healthcare")


def _elementos_overpass(lat: float, lon: float) -> list[dict]:
    ultimo_erro: Exception | None = None
    for url in [u.strip() for u in settings.overpass_url.split(",") if u.strip()]:
        try:
            with _http() as http:
                resposta = http.post(url, data={"data": _consulta_overpass(lat, lon)})
            resposta.raise_for_status()
            return [
                {"lat": e.get("lat") or (e.get("center") or {}).get("lat"),
                 "lon": e.get("lon") or (e.get("center") or {}).get("lon"),
                 "tags": {k: v for k, v in (e.get("tags") or {}).items() if k in _TAGS_UTEIS}}
                for e in resposta.json().get("elements", [])
            ]
        except (httpx.HTTPError, ValueError) as erro:
            ultimo_erro = erro
    raise RuntimeError(f"Overpass indisponível: {ultimo_erro}")


# Plano B quando o Overpass está fora do ar: uma busca por categoria no
# Nominatim (mais leve, porque o Nominatim limita requisições com rigor).
_BUSCAS_NOMINATIM: dict[str, str] = {
    "escola": "school", "saude": "hospital", "comercio": "supermarket", "transporte": "bus station",
    "natureza": "park", "seguranca": "police",
}


def _elementos_nominatim(lat: float, lon: float) -> tuple[list[dict], bool]:
    """Retorna (elementos, completo). Para no primeiro "muitas requisições"."""
    elementos = []
    for categoria, termo in _BUSCAS_NOMINATIM.items():
        raio_graus = CONSULTAS[categoria][1] / 111_000
        caixa = f"{lon - raio_graus},{lat + raio_graus},{lon + raio_graus},{lat - raio_graus}"
        try:
            achados = _nominatim({"q": termo, "viewbox": caixa, "bounded": 1, "limit": 10})
        except httpx.HTTPError as erro:
            logger.warning("Nominatim interrompeu a busca de pontos de interesse: %s", erro)
            return elementos, False
        for achado in achados:
            tags = {achado.get("category", ""): achado.get("type", "")}
            if achado.get("name"):
                tags["name"] = achado["name"]
            elementos.append({"lat": float(achado["lat"]), "lon": float(achado["lon"]), "tags": tags})
    return elementos, True


def pontos_de_interesse(db: Session, lat: float, lon: float) -> dict:
    """Busca (ou lê do cache) os pontos de interesse em volta e resume por categoria."""
    chave = cache.chave_de("pois", round(lat, 3), round(lon, 3))
    guardado = cache.obter(db, chave)
    if guardado is not None:
        elementos = guardado["elementos"]
    else:
        validade = timedelta(days=30)
        try:
            elementos = _elementos_overpass(lat, lon)
        except RuntimeError as erro:
            logger.warning("%s — usando o Nominatim", erro)
            elementos, completo = _elementos_nominatim(lat, lon)
            if not completo:
                validade = timedelta(days=1)  # tenta de novo amanhã
        cache.guardar(db, chave, {"elementos": elementos}, validade)

    categorias: dict[str, dict] = {
        c: {"rotulo": CATEGORIAS_CONTEXTO[c][0], "raio_m": CONSULTAS[c][1], "total": 0, "mais_proximos": []}
        for c in CONSULTAS
    }
    candidatos: dict[str, list[dict]] = {c: [] for c in CONSULTAS}
    for elemento in elementos:
        if elemento.get("lat") is None or elemento.get("lon") is None:
            continue
        classe = _categoria(elemento["tags"])
        if classe is None:
            continue
        categoria, tipo = classe
        distancia = distancia_m(lat, lon, elemento["lat"], elemento["lon"])
        if distancia > CONSULTAS[categoria][1]:
            continue
        rotulo = _ROTULOS.get(tipo, tipo)
        nome = elemento["tags"].get("name") or rotulo
        candidatos[categoria].append({"nome": nome[:80], "tipo": rotulo, "distancia_m": round(distancia)})

    for categoria, lista in candidatos.items():
        lista.sort(key=lambda x: x["distancia_m"])
        categorias[categoria]["total"] = len(lista)
        vistos, mais_proximos = set(), []
        for item in lista:
            if item["nome"] in vistos:
                continue
            vistos.add(item["nome"])
            mais_proximos.append(item)
            if len(mais_proximos) == 3:
                break
        categorias[categoria]["mais_proximos"] = mais_proximos
    return categorias


def calcular(db: Session, imovel: Imovel) -> None:
    aproximado = imovel.coordenadas_aproximadas
    if imovel.latitude is None or imovel.longitude is None:
        coordenadas = geocodificar(db, imovel.bairro, imovel.cidade, imovel.uf)
        if coordenadas is None:
            imovel.contexto = {"categorias": None, "erro": "Não localizamos o bairro no mapa."}
            imovel.contexto_em = agora_utc()
            db.commit()
            return
        imovel.latitude, imovel.longitude = coordenadas
        imovel.coordenadas_aproximadas = aproximado = True
    categorias = pontos_de_interesse(db, imovel.latitude, imovel.longitude)
    imovel.contexto = {
        "categorias": categorias,
        "fonte": "OpenStreetMap",
        "aproximado": aproximado,
        "atualizado_em": agora_utc().isoformat(timespec="minutes"),
    }
    imovel.contexto_em = agora_utc()
    db.commit()


@executor("contexto_bairro")
def _executar(db: Session, tarefa: Tarefa) -> None:
    imovel = db.get(Imovel, tarefa.imovel_id) if tarefa.imovel_id else None
    if imovel is None:
        return
    imobiliaria = db.get(Imobiliaria, imovel.imobiliaria_id)
    if not tem_recurso(imobiliaria.plano, CONTEXTO_BAIRRO):
        return
    calcular(db, imovel)
