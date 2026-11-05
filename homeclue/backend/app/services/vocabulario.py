"""Vocabulário controlado do produto.

Os imóveis guardam características deste dicionário. A IA e o motor de
regras traduzem o texto livre do comprador para estes mesmos códigos, e é
isso que torna o match comparável e verificável.
"""

import re
import unicodedata

TIPOS: dict[str, str] = {
    "apartamento": "Apartamento",
    "casa": "Casa",
    "cobertura": "Cobertura",
    "studio": "Studio / Kitnet",
    "terreno": "Terreno",
    "rural": "Sítio / Chácara",
    "comercial": "Sala / Loja comercial",
}

SINONIMOS_TIPO: dict[str, str] = {
    "apartamento": "apartamento", "apartamentos": "apartamento", "apto": "apartamento", "ape": "apartamento",
    "flat": "apartamento",
    "casa": "casa", "casas": "casa", "sobrado": "casa", "casa de condominio": "casa", "casa de vila": "casa",
    "cobertura": "cobertura", "coberturas": "cobertura",
    "studio": "studio", "estudio": "studio", "kitnet": "studio", "quitinete": "studio", "loft": "studio",
    "terreno": "terreno", "terrenos": "terreno", "lote": "terreno", "lotes": "terreno",
    "sitio": "rural", "sitios": "rural", "chacara": "rural", "chacaras": "rural", "fazenda": "rural",
    "fazendinha": "rural", "area rural": "rural", "roca": "rural",
    "sala comercial": "comercial", "loja": "comercial", "ponto comercial": "comercial", "galpao": "comercial",
    "consultorio": "comercial", "imovel comercial": "comercial",
}

CARACTERISTICAS: dict[str, str] = {
    "piscina": "Piscina",
    "churrasqueira": "Churrasqueira",
    "varanda-gourmet": "Varanda gourmet",
    "varanda": "Varanda",
    "lareira": "Lareira",
    "aquecimento": "Aquecimento",
    "ar-condicionado": "Ar-condicionado",
    "vista-montanha": "Vista para a serra",
    "vista-mar": "Vista para o mar",
    "perto-da-praia": "Perto da praia",
    "jardim": "Jardim / quintal",
    "pet-friendly": "Aceita pets",
    "suite": "Suíte",
    "closet": "Closet",
    "escritorio": "Escritório / home office",
    "area-de-servico": "Área de serviço",
    "mobiliado": "Mobiliado",
    "reformado": "Reformado",
    "novo": "Novo / na planta",
    "elevador": "Elevador",
    "portaria-24h": "Portaria 24h",
    "condominio-fechado": "Condomínio fechado",
    "academia": "Academia",
    "salao-de-festas": "Salão de festas",
    "playground": "Playground",
    "quadra": "Quadra esportiva",
    "sauna": "Sauna",
    "acessibilidade": "Acessibilidade",
    "aceita-financiamento": "Aceita financiamento",
}

# Frases do COMPRADOR que viram característica. A busca é feita em texto
# normalizado (minúsculo, sem acento) e com fronteira de palavra.
SINONIMOS_CARACTERISTICA: dict[str, str] = {
    "piscina": "piscina",
    "churrasqueira": "churrasqueira", "churrasco": "churrasqueira",
    "varanda gourmet": "varanda-gourmet", "espaco gourmet": "varanda-gourmet", "area gourmet": "varanda-gourmet",
    "varanda": "varanda", "sacada": "varanda", "alpendre": "varanda",
    "lareira": "lareira",
    "aquecimento": "aquecimento", "aquecedor": "aquecimento", "aquecida": "aquecimento",
    "ar condicionado": "ar-condicionado", "ar-condicionado": "ar-condicionado",
    "vista para a serra": "vista-montanha", "vista da serra": "vista-montanha", "vista para as montanhas": "vista-montanha",
    "vista para a montanha": "vista-montanha", "vista montanha": "vista-montanha", "vista serra": "vista-montanha",
    "vista para o verde": "vista-montanha", "vista panoramica": "vista-montanha",
    "vista para o mar": "vista-mar", "vista mar": "vista-mar", "vista pro mar": "vista-mar",
    "praia": "perto-da-praia", "perto do mar": "perto-da-praia", "beira mar": "perto-da-praia",
    "beira-mar": "perto-da-praia", "pe na areia": "perto-da-praia", "orla": "perto-da-praia",
    "frente para o mar": "perto-da-praia", "frente ao mar": "perto-da-praia",
    "jardim": "jardim", "quintal": "jardim", "area externa": "jardim", "gramado": "jardim",
    "pet": "pet-friendly", "pets": "pet-friendly", "cachorro": "pet-friendly", "cachorros": "pet-friendly",
    "cao": "pet-friendly", "gato": "pet-friendly", "gatos": "pet-friendly", "animais": "pet-friendly",
    "animal": "pet-friendly",
    "suite": "suite", "suites": "suite",
    "closet": "closet",
    "escritorio": "escritorio", "home office": "escritorio", "trabalhar de casa": "escritorio",
    "area de servico": "area-de-servico", "lavanderia": "area-de-servico",
    "mobiliado": "mobiliado", "mobiliada": "mobiliado", "com moveis": "mobiliado",
    "reformado": "reformado", "reformada": "reformado",
    "na planta": "novo", "lancamento": "novo", "imovel novo": "novo", "casa nova": "novo", "apartamento novo": "novo",
    "elevador": "elevador",
    "portaria": "portaria-24h", "porteiro": "portaria-24h",
    "condominio fechado": "condominio-fechado", "seguranca": "condominio-fechado",
    "academia": "academia",
    "salao de festas": "salao-de-festas",
    "playground": "playground", "criancas": "playground", "brinquedoteca": "playground",
    "quadra": "quadra",
    "sauna": "sauna",
    "acessibilidade": "acessibilidade", "acessivel": "acessibilidade", "cadeirante": "acessibilidade",
    "sem escada": "acessibilidade", "sem escadas": "acessibilidade",
    "financiamento": "aceita-financiamento", "financiar": "aceita-financiamento", "financiado": "aceita-financiamento",
}

# Como cada característica aparece no TEXTO DO ANÚNCIO (descrição, itens do feed).
TERMOS_EVIDENCIA: dict[str, list[str]] = {
    "piscina": ["piscina"],
    "churrasqueira": ["churrasqueira"],
    "varanda-gourmet": ["varanda gourmet", "espaco gourmet", "area gourmet"],
    "varanda": ["varanda", "sacada", "alpendre"],
    "lareira": ["lareira"],
    "aquecimento": ["aquecimento", "aquecedor", "aquecida", "aquecido"],
    "ar-condicionado": ["ar condicionado", "ar-condicionado", "split"],
    "vista-montanha": ["vista para a serra", "vista da serra", "vista para as montanhas", "vista para a montanha",
                       "vista panoramica", "vista para o verde", "vista para a mata"],
    "vista-mar": ["vista para o mar", "vista mar", "vista pro mar"],
    "perto-da-praia": ["praia", "beira-mar", "beira mar", "orla", "pe na areia", "frente para o mar", "frente ao mar"],
    "jardim": ["jardim", "quintal", "gramado", "area externa"],
    "pet-friendly": ["aceita pet", "aceita pets", "aceita animais", "aceita animal", "permite animais",
                     "pet friendly", "aceitam animais", "aceitam pets"],
    "suite": ["suite"],
    "closet": ["closet"],
    "escritorio": ["escritorio", "home office"],
    "area-de-servico": ["area de servico", "lavanderia"],
    "mobiliado": ["mobiliado", "mobiliada", "semi mobiliado", "semimobiliado"],
    "reformado": ["reformado", "reformada", "reforma recente"],
    "novo": ["na planta", "lancamento", "nunca habitado", "primeira locacao"],
    "elevador": ["elevador"],
    "portaria-24h": ["portaria 24", "portaria", "porteiro"],
    "condominio-fechado": ["condominio fechado"],
    "academia": ["academia", "fitness"],
    "salao-de-festas": ["salao de festas"],
    "playground": ["playground", "brinquedoteca"],
    "quadra": ["quadra"],
    "sauna": ["sauna"],
    "acessibilidade": ["acessibilidade", "acessivel", "rampa de acesso"],
    "aceita-financiamento": ["aceita financiamento", "financiamento", "financiavel"],
}

# Itens que os feeds (VRSync em inglês e formatos em português) mandam.
ITENS_FEED: dict[str, str] = {
    "pool": "piscina", "private pool": "piscina", "piscina": "piscina",
    "bbq": "churrasqueira", "barbecue": "churrasqueira", "barbecue grill": "churrasqueira", "churrasqueira": "churrasqueira",
    "gourmet area": "varanda-gourmet", "gourmet space": "varanda-gourmet", "gourmet balcony": "varanda-gourmet",
    "varanda gourmet": "varanda-gourmet", "espaco gourmet": "varanda-gourmet",
    "balcony": "varanda", "varanda": "varanda", "sacada": "varanda",
    "fireplace": "lareira", "lareira": "lareira",
    "heating": "aquecimento", "solar heating": "aquecimento", "aquecimento": "aquecimento", "aquecimento solar": "aquecimento",
    "air conditioning": "ar-condicionado", "ar condicionado": "ar-condicionado",
    "mountain view": "vista-montanha", "vista para montanha": "vista-montanha", "vista montanha": "vista-montanha",
    "ocean view": "vista-mar", "sea view": "vista-mar", "vista mar": "vista-mar",
    "beach": "perto-da-praia", "close to the beach": "perto-da-praia", "beachfront": "perto-da-praia",
    "frente para o mar": "perto-da-praia", "perto da praia": "perto-da-praia", "beira mar": "perto-da-praia",
    "garden": "jardim", "garden area": "jardim", "backyard": "jardim", "lawn": "jardim", "jardim": "jardim",
    "quintal": "jardim",
    "pets allowed": "pet-friendly", "pet friendly": "pet-friendly", "aceita animais": "pet-friendly",
    "closet": "closet",
    "home office": "escritorio", "escritorio": "escritorio",
    "laundry": "area-de-servico", "service area": "area-de-servico", "area de servico": "area-de-servico",
    "lavanderia": "area-de-servico",
    "furnished": "mobiliado", "mobiliado": "mobiliado",
    "elevator": "elevador", "elevador": "elevador",
    "security 24 hours": "portaria-24h", "security guard on duty": "portaria-24h", "concierge": "portaria-24h",
    "caretaker": "portaria-24h", "doorman": "portaria-24h", "portaria 24h": "portaria-24h", "portaria 24 horas": "portaria-24h",
    "gated community": "condominio-fechado", "condominio fechado": "condominio-fechado",
    "gym": "academia", "fitness room": "academia", "academia": "academia",
    "party room": "salao-de-festas", "salao de festas": "salao-de-festas",
    "playground": "playground",
    "sports court": "quadra", "tennis court": "quadra", "quadra poliesportiva": "quadra", "quadra": "quadra",
    "sauna": "sauna",
    "disabled access": "acessibilidade", "acessibilidade": "acessibilidade",
}

# Cômodos que a imobiliária desenha na planta interativa.
TIPOS_COMODO: dict[str, str] = {
    "sala": "Sala", "cozinha": "Cozinha", "quarto": "Quarto", "suite": "Suíte", "banheiro": "Banheiro",
    "lavabo": "Lavabo", "varanda": "Varanda", "varanda-gourmet": "Varanda gourmet",
    "area-de-servico": "Área de serviço", "escritorio": "Escritório", "closet": "Closet", "garagem": "Garagem",
    "quintal": "Quintal", "jardim": "Jardim", "piscina": "Piscina", "despensa": "Despensa",
    "circulacao": "Circulação", "outro": "Outro",
}

# Que cômodo da planta comprova cada característica.
COMODOS_DA_CARACTERISTICA: dict[str, set[str]] = {
    "escritorio": {"escritorio"}, "varanda": {"varanda", "varanda-gourmet"}, "varanda-gourmet": {"varanda-gourmet"},
    "piscina": {"piscina"}, "jardim": {"quintal", "jardim"}, "area-de-servico": {"area-de-servico"},
    "suite": {"suite"}, "closet": {"closet"},
}

# Contexto do bairro (OpenStreetMap): categoria -> (rótulo, distância que conta como "perto").
CATEGORIAS_CONTEXTO: dict[str, tuple[str, int]] = {
    "escola": ("Escolas", 1000),
    "saude": ("Saúde", 2000),
    "comercio": ("Comércio", 800),
    "transporte": ("Transporte", 500),
    "natureza": ("Natureza", 1500),
    "seguranca": ("Segurança", 1500),
    "praia": ("Praia", 1000),
}

NOMES_PERTO_DE: dict[str, str] = {
    "escola": "escola", "saude": "hospital ou posto de saúde", "comercio": "comércio",
    "transporte": "ponto de ônibus", "natureza": "natureza", "seguranca": "polícia ou bombeiros",
    "praia": "praia",
}

# Frases do comprador que pedem proximidade.
PADROES_PERTO_DE: dict[str, str] = {
    "escola": r"escola|colegio|creche|faculdade|universidade",
    "saude": r"hospital|posto de saude|clinica|upa\b|pronto[- ]socorro",
    "comercio": r"comercio|mercado|supermercado|padaria|farmacia|centro comercial|lojas",
    "transporte": r"onibus|transporte|rodoviaria|ponto de",
    # "rio" sozinho; "Rio de Janeiro", "Rio das Ostras", "Rio Bonito"… são nomes de lugar.
    "natureza": r"natureza|mata|trilha|cachoeira|parque|verde|\brio\b(?! (?:d[aeo]s?|bonito|dourado|grande|novo)\b)",
    "seguranca": r"delegacia|policia|batalhao|bombeiro",
}

# Pedidos frequentes que não são característica nem campo estruturado.
# canônico -> (padrão na frase do comprador, termos que comprovam no anúncio)
DESEJOS_CONHECIDOS: dict[str, tuple[str, list[str]]] = {
    "sol da manhã": (r"(luz|sol) (da|de|pela|na) manha|sol nascente",
                     ["sol da manha", "sol pela manha", "luz da manha", "sol nascente", "face nascente", "posicao nascente"]),
    "sol da tarde": (r"(luz|sol) (da|de|pela|na) tarde|sol poente",
                     ["sol da tarde", "sol pela tarde", "sol poente", "face poente"]),
    "imóvel claro e arejado": (r"\b(claro|clara|iluminad[oa]|arejad[oa]|ventilad[oa]|ensolarad[oa])\b",
                               ["iluminado", "iluminada", "claro", "clara", "arejado", "arejada", "ventilado",
                                "ventilada", "ensolarado", "ensolarada", "iluminacao natural", "bem iluminado"]),
    "rua tranquila": (r"rua (tranquila|calma|sem saida|silenciosa)|lugar (tranquilo|calmo|silencioso)|silencioso|sossego",
                      ["rua tranquila", "rua calma", "rua sem saida", "silencioso", "silenciosa", "tranquilo",
                       "tranquila", "sossego"]),
    "fogão a lenha": (r"fogao a lenha", ["fogao a lenha"]),
    "pé-direito alto": (r"pe[- ]direito alto", ["pe direito alto", "pe-direito alto", "pe direito duplo"]),
    "cozinha americana": (r"cozinha americana", ["cozinha americana", "cozinha integrada"]),
    "armários planejados": (r"planejad[oa]s?|armarios", ["planejado", "planejada", "planejados", "planejadas",
                                                         "armarios embutidos"]),
    "casa térrea": (r"\bterrea\b|um andar so|uma pavimento|sem escadas?", ["terrea", "um pavimento", "sem escadas"]),
    "poço artesiano": (r"poco artesiano|poco", ["poco artesiano", "poco"]),
    "água no terreno": (r"nascente|riacho|corrego|cachoeira no terreno|rio no terreno|agua no terreno",
                        ["nascente", "riacho", "corrego", "cachoeira", "lago", "agua corrente"]),
    "pomar e horta": (r"pomar|horta|arvores frutiferas", ["pomar", "horta", "arvores frutiferas", "frutiferas"]),
    "andar alto": (r"andar alto", ["andar alto"]),
    "garagem coberta": (r"garagem coberta|vaga coberta", ["garagem coberta", "vaga coberta"]),
}

# Palavras que, logo antes do termo, invertem o sentido ("não aceita animais").
NEGACOES = ("nao", "sem", "nem", "proibido", "proibida", "proibidos", "exceto", "vedado", "vedada")


def normalizar(texto: str) -> str:
    """Minúsculas e sem acentos — "Condomínio" e "condominio" viram a mesma coisa."""
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", sem_acento.lower()).strip()


def caracteristicas_validas(slugs: list[str]) -> list[str]:
    """Descarta slugs desconhecidos e duplicados, preservando a ordem."""
    vistos: list[str] = []
    for slug in slugs:
        if slug in CARACTERISTICAS and slug not in vistos:
            vistos.append(slug)
    return vistos


_PRIORIDADE_TIPO = ["cobertura", "studio", "rural", "terreno", "comercial", "casa", "apartamento"]


def tipo_do_texto(texto: str) -> str | None:
    """Tipo de um anúncio a partir do texto do sistema. O mais específico
    vence: "Apartamento Duplex/Cobertura" é cobertura, "Casa comercial" é comercial."""
    t = f" {normalizar(texto)} "
    achados = {tipo for chave, tipo in SINONIMOS_TIPO.items() if re.search(rf"\b{re.escape(chave)}\b", t)}
    return next((tipo for tipo in _PRIORIDADE_TIPO if tipo in achados), None)


def caracteristica_de_item_feed(item: str) -> str | None:
    """Traduz um item de feed ("Pool", "Lareira") para o vocabulário."""
    n = normalizar(item)
    if n in ITENS_FEED:
        return ITENS_FEED[n]
    for chave in sorted(ITENS_FEED, key=len, reverse=True):
        if re.search(rf"\b{re.escape(chave)}\b", n):
            return ITENS_FEED[chave]
    return None
