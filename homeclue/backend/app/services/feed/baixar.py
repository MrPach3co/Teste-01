"""Download seguro do feed XML.

O endereço é digitado pela imobiliária, então o servidor não pode ser usado
para alcançar a rede interna (SSRF): só http/https, e todo IP resolvido — em
cada redirecionamento — precisa ser público. Tamanho e tempo são limitados,
e feeds compactados (.gz) são aceitos com limite de descompressão.
"""

import ipaddress
import socket
import zlib
from urllib.parse import urljoin, urlsplit

import httpx

from app.core.config import obter_settings

settings = obter_settings()

TAMANHO_MAXIMO = 60 * 1024 * 1024
TAMANHO_MAXIMO_DESCOMPACTADO = 250 * 1024 * 1024
MAX_REDIRECIONAMENTOS = 5


class FeedInvalido(Exception):
    """Erro com mensagem pronta para mostrar à imobiliária."""


def validar_endereco(url: str) -> None:
    partes = urlsplit(url)
    if partes.scheme not in ("http", "https") or not partes.hostname:
        raise FeedInvalido("O endereço do feed precisa começar com http:// ou https://.")
    if settings.permitir_feed_rede_privada:
        return
    try:
        enderecos = {info[4][0] for info in socket.getaddrinfo(partes.hostname, partes.port or 443)}
    except socket.gaierror:
        raise FeedInvalido(f"Não encontramos o servidor “{partes.hostname}”. Confira o endereço do feed.")
    for endereco in enderecos:
        ip = ipaddress.ip_address(endereco.split("%")[0])
        if not ip.is_global or ip.is_multicast:
            raise FeedInvalido("Esse endereço aponta para uma rede interna e não pode ser usado como feed.")


def _descompactar_se_preciso(dados: bytes) -> bytes:
    if dados[:2] != b"\x1f\x8b":
        return dados
    descompactador = zlib.decompressobj(16 + zlib.MAX_WBITS)
    saida = descompactador.decompress(dados, TAMANHO_MAXIMO_DESCOMPACTADO + 1)
    if len(saida) > TAMANHO_MAXIMO_DESCOMPACTADO or descompactador.unconsumed_tail:
        raise FeedInvalido("O feed descompactado passa de 250 MB.")
    return saida


def baixar(url: str) -> bytes:
    atual = url
    with httpx.Client(timeout=httpx.Timeout(60.0, connect=15.0), follow_redirects=False,
                      headers={"User-Agent": settings.user_agent, "Accept-Encoding": "gzip"}) as http:
        for _ in range(MAX_REDIRECIONAMENTOS + 1):
            validar_endereco(atual)
            try:
                with http.stream("GET", atual) as resposta:
                    if resposta.status_code in (301, 302, 303, 307, 308):
                        destino = resposta.headers.get("location")
                        if not destino:
                            raise FeedInvalido("O servidor do feed redirecionou sem dizer para onde.")
                        atual = urljoin(atual, destino)
                        continue
                    if resposta.status_code != 200:
                        raise FeedInvalido(f"O servidor do feed respondeu com erro {resposta.status_code}.")
                    partes, total = [], 0
                    for pedaco in resposta.iter_bytes():
                        total += len(pedaco)
                        if total > TAMANHO_MAXIMO:
                            raise FeedInvalido("O feed passa de 60 MB.")
                        partes.append(pedaco)
                    return _descompactar_se_preciso(b"".join(partes))
            except httpx.TimeoutException:
                raise FeedInvalido("O servidor do feed demorou demais para responder.")
            except httpx.HTTPError as erro:
                raise FeedInvalido(f"Não conseguimos baixar o feed ({erro.__class__.__name__}).")
    raise FeedInvalido("Redirecionamentos demais no endereço do feed.")

