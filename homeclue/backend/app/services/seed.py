"""Imobiliária de demonstração (usada na landing page e nos testes).

Imóveis FICTÍCIOS em bairros reais de Nova Friburgo, Teresópolis e
Cachoeiras de Macacu (onde a Homeclue começa) e de Rio das Ostras (Região dos
Lagos, onde a Correta também atua). O entorno (escolas,
comércio etc.) vem de dados reais do OpenStreetMap, guardados em
services/dados/osm_demo.json quando disponíveis.

Idempotente: pode rodar a cada deploy. Se a demonstração for de uma versão
anterior, ela é refeita. O dono da conta demo recebe uma senha aleatória
descartada, então ninguém entra no painel dela.
"""

import json
import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import gerar_hash_senha, gerar_senha_temporaria
from app.core.tempo import agora_utc
from app.core.textos_legais import TEXTO_CONSENTIMENTO_CONTA_V2
from app.db.session import SessionLocal
from app.models import BairroInfo, Empreendimento, Imobiliaria, Imovel, Unidade, Usuario
from app.services import contexto

logger = logging.getLogger(__name__)

CHAVE_DEMO = "pk_demo"
NOME_DEMO = "Imobiliária Demonstração · Serra e Lagos"
_ARQUIVO_OSM = Path(__file__).parent / "dados" / "osm_demo.json"

# (código, bairro, cidade, dados)
_IMOVEIS = [
    ("DEMO-01", "Olaria", "Nova Friburgo", dict(
        titulo="Casa térrea com quintal e lareira em Olaria", tipo="casa", finalidade="venda", preco=690_000,
        quartos=3, suites=1, banheiros=2, vagas=2, area_m2=140, area_terreno=360,
        caracteristicas=["jardim", "pet-friendly", "churrasqueira", "lareira", "suite", "area-de-servico"],
        descricao="Casa térrea em rua tranquila de Olaria, com quintal gramado e cercado, ótimo para quem tem "
                  "cachorro. Sala de estar com lareira e janelas voltadas para o nascente, com sol da manhã. "
                  "Cozinha ampla integrada à área de churrasqueira. Três quartos, sendo uma suíte. Garagem para "
                  "dois carros. Aceita financiamento.")),
    ("DEMO-02", "Centro", "Nova Friburgo", dict(
        titulo="Apartamento de 2 quartos no Centro, perto do comércio", tipo="apartamento", finalidade="venda",
        preco=420_000, quartos=2, suites=0, banheiros=1, vagas=1, area_m2=68,
        caracteristicas=["elevador", "portaria-24h", "area-de-servico", "aceita-financiamento"],
        descricao="Apartamento de dois quartos no Centro, a poucos passos do comércio. Prédio com elevador e "
                  "portaria 24 horas. Sala clara e arejada, cozinha com armários planejados. Aceita financiamento.")),
    ("DEMO-03", "Cônego", "Nova Friburgo", dict(
        titulo="Casa em condomínio no Cônego com piscina e vista para a serra", tipo="casa", finalidade="venda",
        preco=1_150_000, quartos=4, suites=2, banheiros=3, vagas=3, area_m2=260, area_terreno=600,
        caracteristicas=["piscina", "varanda-gourmet", "lareira", "vista-montanha", "aquecimento", "jardim",
                         "condominio-fechado", "suite"],
        descricao="Casa em condomínio fechado no Cônego, com vista para a serra. Varanda gourmet com churrasqueira, "
                  "piscina aquecida e jardim. Lareira na sala de estar. Aquecimento solar. Quatro quartos, sendo "
                  "duas suítes, uma delas com closet.")),
    ("DEMO-04", "Braunes", "Nova Friburgo", dict(
        titulo="Apartamento para alugar em Braunes com lazer", tipo="apartamento", finalidade="aluguel",
        preco=1_800, condominio=420, quartos=2, suites=0, banheiros=1, vagas=1, area_m2=62,
        caracteristicas=["playground", "salao-de-festas", "area-de-servico"],
        descricao="Apartamento para alugar em Braunes, em condomínio com playground e salão de festas. "
                  "Não aceita animais.")),
    ("DEMO-05", "Lumiar", "Nova Friburgo", dict(
        titulo="Sítio em Lumiar com nascente e pomar", tipo="rural", finalidade="venda", preco=850_000,
        quartos=3, banheiros=2, vagas=None, area_m2=150, area_terreno=20_000,
        caracteristicas=["lareira", "jardim", "vista-montanha", "varanda"],
        descricao="Sítio em Lumiar com nascente e riacho no terreno, pomar com árvores frutíferas e horta. Casa com "
                  "fogão a lenha, lareira e varanda com vista para as montanhas. Acesso por estrada de terra, "
                  "a 4 km da vila.")),
    ("DEMO-06", "Vila Amélia", "Nova Friburgo", dict(
        titulo="Casa com quintal e escritório na Vila Amélia", tipo="casa", finalidade="venda", preco=560_000,
        quartos=3, suites=0, banheiros=2, vagas=1, area_m2=120, area_terreno=250,
        caracteristicas=["jardim", "varanda", "escritorio"],
        descricao="Casa com quintal e varanda na Vila Amélia. Escritório independente, ideal para home office. "
                  "Rua calma, a poucas quadras do comércio do bairro.")),
    ("DEMO-07", "Centro", "Nova Friburgo", dict(
        titulo="Cobertura duplex no Centro com terraço", tipo="cobertura", finalidade="venda", preco=980_000,
        condominio=900, quartos=3, suites=1, banheiros=2, vagas=2, area_m2=180,
        caracteristicas=["varanda-gourmet", "vista-montanha", "elevador", "churrasqueira", "suite"],
        descricao="Cobertura duplex no Centro com terraço e churrasqueira, vista panorâmica para a serra. Sala "
                  "com pé-direito alto. Prédio com elevador.")),
    ("DEMO-08", "Centro", "Nova Friburgo", dict(
        titulo="Studio mobiliado no Centro", tipo="studio", finalidade="aluguel", preco=1_200, condominio=280,
        quartos=1, suites=0, banheiros=1, vagas=0, area_m2=32, caracteristicas=["mobiliado"],
        descricao="Studio mobiliado no Centro, perto da rodoviária e do comércio. Aceita pets de pequeno porte.")),
    ("DEMO-09", "Mury", "Nova Friburgo", dict(
        titulo="Casa em Mury cercada de verde, com piscina", tipo="casa", finalidade="venda", preco=780_000,
        quartos=3, suites=1, banheiros=3, vagas=2, area_m2=200, area_terreno=1_200,
        caracteristicas=["piscina", "jardim", "churrasqueira", "lareira", "pet-friendly", "suite"],
        descricao="Casa em Mury, no caminho de Lumiar, cercada de verde. Piscina, churrasqueira e amplo jardim. "
                  "Lareira na sala. Aceita animais.")),
    ("DEMO-10", "Conselheiro Paulino", "Nova Friburgo", dict(
        titulo="Apartamento 2 quartos em Conselheiro Paulino", tipo="apartamento", finalidade="venda",
        preco=285_000, quartos=2, banheiros=1, vagas=1, area_m2=None, caracteristicas=[],
        descricao="Apartamento 2 quartos em Conselheiro Paulino.")),
    ("DEMO-11", "Olaria", "Nova Friburgo", dict(
        titulo="Casa para alugar em Olaria com quintal", tipo="casa", finalidade="aluguel", preco=2_600,
        quartos=3, suites=0, banheiros=2, vagas=1, area_m2=110, caracteristicas=["jardim"],
        descricao="Casa para alugar em Olaria, com quintal e área de serviço. Não aceita animais de grande porte.")),
    ("DEMO-12", "Agriões", "Teresópolis", dict(
        titulo="Apartamento no Agriões com varanda", tipo="apartamento", finalidade="venda", preco=520_000,
        condominio=650, quartos=2, suites=1, banheiros=2, vagas=1, area_m2=75,
        caracteristicas=["elevador", "academia", "varanda", "suite"],
        descricao="Apartamento no Agriões, em Teresópolis, com varanda e vista para o Dedo de Deus. Condomínio com "
                  "academia e elevador.")),
    ("DEMO-13", "Alto", "Teresópolis", dict(
        titulo="Casa em condomínio no Alto com lareira e piscina", tipo="casa", finalidade="venda",
        preco=1_450_000, quartos=4, suites=3, banheiros=4, vagas=3, area_m2=320, area_terreno=900,
        caracteristicas=["piscina", "lareira", "aquecimento", "jardim", "condominio-fechado", "portaria-24h", "suite"],
        descricao="Casa em condomínio fechado no Alto, com portaria 24h. Lareira, aquecimento central e piscina. "
                  "Jardim com gramado e playground do condomínio a poucos metros.")),
    ("DEMO-14", "Boca do Mato", "Cachoeiras de Macacu", dict(
        titulo="Sítio com cachoeira em Boca do Mato", tipo="rural", finalidade="venda", preco=480_000,
        quartos=2, banheiros=1, vagas=None, area_m2=90, area_terreno=10_000, caracteristicas=["jardim"],
        descricao="Sítio com cachoeira no terreno, poço artesiano e pomar. Casa simples de dois quartos.")),
    ("DEMO-15", "Cônego", "Nova Friburgo", dict(
        titulo="Terreno em condomínio no Cônego", tipo="terreno", finalidade="venda", preco=320_000,
        area_m2=None, area_terreno=450, caracteristicas=["condominio-fechado", "vista-montanha"],
        descricao="Terreno plano em condomínio no Cônego, com vista para a serra. Pronto para construir.")),
    ("DEMO-16", "Braunes", "Nova Friburgo", dict(
        titulo="Casa para venda ou aluguel em Braunes", tipo="casa", finalidade="venda_aluguel", preco=640_000,
        preco_aluguel=3_200, quartos=3, suites=1, banheiros=2, vagas=2, area_m2=130,
        caracteristicas=["jardim", "churrasqueira", "aceita-financiamento", "suite"],
        descricao="Casa para venda ou aluguel em Braunes, com churrasqueira e quintal. Bem iluminada, com sol da "
                  "tarde na varanda.")),
    ("DEMO-17", "Costazul", "Rio das Ostras", dict(
        titulo="Casa a 300 metros da praia em Costazul", tipo="casa", finalidade="venda", preco=720_000,
        quartos=3, suites=1, banheiros=2, vagas=2, area_m2=140, area_terreno=300,
        caracteristicas=["churrasqueira", "jardim", "suite", "aceita-financiamento"],
        descricao="Casa em Costazul a 300 metros da praia, com quintal e churrasqueira. Três quartos, sendo uma "
                  "suíte. Rua tranquila, perto do comércio do bairro.")),
    ("DEMO-18", "Centro", "Rio das Ostras", dict(
        titulo="Apartamento com vista para o mar no Centro de Rio das Ostras", tipo="apartamento",
        finalidade="aluguel", preco=2_200, condominio=480, quartos=2, suites=0, banheiros=1, vagas=1, area_m2=70,
        caracteristicas=["vista-mar", "elevador", "area-de-servico"],
        descricao="Apartamento com vista para o mar no Centro de Rio das Ostras, a uma quadra da orla. Prédio com "
                  "elevador. Aceita pets de pequeno porte.")),
    ("DEMO-19", "Enseada das Gaivotas", "Rio das Ostras", dict(
        titulo="Cobertura de frente para o mar na Enseada das Gaivotas", tipo="cobertura", finalidade="venda",
        preco=1_350_000, condominio=1_100, quartos=3, suites=2, banheiros=3, vagas=2, area_m2=190,
        caracteristicas=["vista-mar", "piscina", "varanda-gourmet", "elevador", "suite"],
        descricao="Cobertura de frente para o mar na Enseada das Gaivotas, com varanda gourmet e piscina privativa. "
                  "Três quartos, dois deles suítes.")),
]

# Planta da casa de vitrine (DEMO-01). As coordenadas batem com o desenho em frontend/demo/planta-demo.svg.
_PLANTA_DEMO = {
    "imagem": "/demo/planta-demo.svg",
    "comodos": [
        {"id": "sala", "tipo": "sala", "nome": "Sala de estar", "x": 0.05, "y": 0.08, "w": 0.38, "h": 0.42,
         "area_m2": 28, "notas": "Janelas para o nascente (sol da manhã) e lareira", "fotos": []},
        {"id": "cozinha", "tipo": "cozinha", "nome": "Cozinha", "x": 0.43, "y": 0.08, "w": 0.25, "h": 0.30,
         "area_m2": 14, "notas": "Integrada à área de churrasqueira", "fotos": []},
        {"id": "servico", "tipo": "area-de-servico", "nome": "Área de serviço", "x": 0.68, "y": 0.08, "w": 0.14,
         "h": 0.30, "area_m2": 6, "notas": "", "fotos": []},
        {"id": "churrasqueira", "tipo": "varanda-gourmet", "nome": "Área de churrasqueira", "x": 0.82, "y": 0.08,
         "w": 0.13, "h": 0.44, "area_m2": 12, "notas": "Coberta, com pia e churrasqueira", "fotos": []},
        {"id": "suite", "tipo": "suite", "nome": "Suíte", "x": 0.05, "y": 0.52, "w": 0.28, "h": 0.40,
         "area_m2": 16, "notas": "", "fotos": []},
        {"id": "banho-suite", "tipo": "banheiro", "nome": "Banheiro da suíte", "x": 0.33, "y": 0.52, "w": 0.10,
         "h": 0.20, "area_m2": 4, "notas": "", "fotos": []},
        {"id": "banho", "tipo": "banheiro", "nome": "Banheiro social", "x": 0.33, "y": 0.72, "w": 0.10, "h": 0.20,
         "area_m2": 4, "notas": "", "fotos": []},
        {"id": "quarto2", "tipo": "quarto", "nome": "Quarto 2", "x": 0.43, "y": 0.52, "w": 0.21, "h": 0.40,
         "area_m2": 11, "notas": "", "fotos": []},
        {"id": "quarto3", "tipo": "quarto", "nome": "Quarto 3", "x": 0.64, "y": 0.52, "w": 0.18, "h": 0.40,
         "area_m2": 10, "notas": "", "fotos": []},
        {"id": "quintal", "tipo": "quintal", "nome": "Quintal", "x": 0.82, "y": 0.52, "w": 0.13, "h": 0.40,
         "area_m2": 30, "notas": "Gramado e cercado — bom para cachorro", "fotos": []},
    ],
}

_BAIRROS = {
    "Olaria": ("Bairro residencial próximo ao Centro, com comércio de bairro e escolas. (Texto de exemplo da "
               "demonstração.)", "media", "Exemplo: procura constante por casas com quintal na região."),
    "Cônego": ("Bairro tranquilo e arborizado, com condomínios e vista para a serra. (Texto de exemplo.)", "alta",
               "Exemplo: novos condomínios e pouca oferta de terrenos."),
    "Centro": ("Comércio, serviços e rodoviária a pé. (Texto de exemplo.)", None, ""),
}


def _coordenadas_osm() -> dict:
    if _ARQUIVO_OSM.exists():
        return json.loads(_ARQUIVO_OSM.read_text(encoding="utf-8"))
    return {}


def _unidades_demo(emp: Empreendimento) -> None:
    tipologias = {1: (3, 1, 92.0, "3 quartos com suíte"), 2: (2, 0, 68.0, "2 quartos"),
                  3: (2, 0, 68.0, "2 quartos"), 4: (3, 1, 92.0, "3 quartos com suíte")}
    vendidas = {(1, 2), (1, 3), (2, 1), (2, 2), (3, 3), (4, 4), (5, 1), (6, 2)}
    reservadas = {(3, 1), (5, 3), (7, 4)}
    for andar in range(1, 9):
        for posicao in range(1, 5):
            quartos, suites, area, tipologia = tipologias[posicao]
            base = 6_800 if quartos == 3 else 6_500
            status = "vendida" if (andar, posicao) in vendidas else "reservada" if (andar, posicao) in reservadas else "disponivel"
            emp.unidades.append(Unidade(
                torre="Torre Única", andar=andar, posicao=posicao, codigo=f"{andar}{posicao:02d}", status=status,
                preco=round(area * base * (1 + 0.012 * andar), -3), area_m2=area, quartos=quartos, suites=suites,
                vagas=1, tipologia=tipologia,
            ))


def _montar(db: Session, demo: Imobiliaria) -> None:
    osm = _coordenadas_osm()
    for i, (codigo, bairro, cidade, dados) in enumerate(_IMOVEIS):
        imovel = Imovel(imobiliaria_id=demo.id, origem="manual", codigo_referencia=codigo, bairro=bairro,
                        cidade=cidade, uf="RJ", **dados)
        local = osm.get(f"{bairro}|{cidade}")
        if local:
            # Pequeno deslocamento para os imóveis do mesmo bairro não ficarem no mesmo ponto.
            imovel.latitude = local["lat"] + 0.0012 * ((i % 3) - 1)
            imovel.longitude = local["lon"] + 0.0012 * ((i % 2) * 2 - 1)
            imovel.coordenadas_aproximadas = True
            imovel.contexto = {
                "categorias": contexto.resumir(local["elementos"], imovel.latitude, imovel.longitude),
                "fonte": "OpenStreetMap", "aproximado": True,
                "atualizado_em": agora_utc().isoformat(timespec="minutes"),
            }
            imovel.contexto_em = agora_utc()
        if codigo == "DEMO-01":
            imovel.planta = _PLANTA_DEMO
        db.add(imovel)

    for nome, (descricao, valorizacao, justificativa) in _BAIRROS.items():
        db.add(BairroInfo(imobiliaria_id=demo.id, nome=nome, descricao=descricao, valorizacao=valorizacao,
                          valorizacao_justificativa=justificativa))

    emp = Empreendimento(
        imobiliaria_id=demo.id, nome="Residencial Vale das Hortênsias (fictício)", bairro="Braunes",
        cidade="Nova Friburgo", previsao_entrega="Dez/2027",
        descricao="Lançamento fictício para demonstração do espelho de vendas: torre única de 8 andares, "
                  "4 apartamentos por andar, de 2 e 3 quartos.",
        torres=[{"nome": "Torre Única", "andares": 8, "unidades_por_andar": 4}],
    )
    _unidades_demo(emp)
    db.add(emp)


def semear(db: Session) -> Imobiliaria:
    demo = db.scalar(select(Imobiliaria).where(Imobiliaria.chave_publica == CHAVE_DEMO))
    if demo is not None and demo.nome == NOME_DEMO:
        return demo
    if demo is not None:
        db.delete(demo)  # demonstração de versão anterior: refaz do zero
        db.flush()

    demo = Imobiliaria(nome=NOME_DEMO, chave_publica=CHAVE_DEMO, cor_primaria="#1F3B2C", plano="premium",
                       whatsapp="+55 22 90000-0000")
    db.add(demo)
    db.flush()
    db.add(Usuario(
        imobiliaria_id=demo.id, nome="Conta de demonstração", email="demo@homeclue.invalid",
        senha_hash=gerar_hash_senha(gerar_senha_temporaria()), papel="dono",
        consentimento_em=agora_utc(), consentimento_texto=TEXTO_CONSENTIMENTO_CONTA_V2,
    ))
    _montar(db, demo)
    db.commit()
    return demo


if __name__ == "__main__":
    with SessionLocal() as sessao:
        semear(sessao)
        print("Imobiliária de demonstração pronta.")
