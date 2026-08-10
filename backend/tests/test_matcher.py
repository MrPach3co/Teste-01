from app.services import matcher


def test_extrair_orcamento_em_milhoes():
    assert matcher.extrair_orcamento("até 2 milhões") == 2_000_000


def test_extrair_orcamento_em_mil():
    assert matcher.extrair_orcamento("até 850 mil") == 850_000


def test_extrair_orcamento_ausente():
    assert matcher.extrair_orcamento("uma casa bonita") is None


def test_extrair_quartos():
    assert matcher.extrair_quartos("preciso de 4 quartos") == 4


def test_extrair_tags_reconhece_sinonimos():
    tags = matcher.extrair_tags("casa moderna perto do mar com escritório")
    assert tags == {"moderna", "perto-do-mar", "escritorio"}


def test_calcular_match_soma_pontos_por_tag_e_orcamento():
    match_bom = matcher.calcular_match(
        tags_imovel={"perto-do-mar", "moderna"},
        preco=1_000_000,
        quartos=3,
        tags_pedidas={"perto-do-mar", "moderna"},
        orcamento=2_000_000,
        quartos_pedidos=3,
    )
    match_ruim = matcher.calcular_match(
        tags_imovel=set(),
        preco=5_000_000,
        quartos=1,
        tags_pedidas={"perto-do-mar", "moderna"},
        orcamento=2_000_000,
        quartos_pedidos=3,
    )
    assert match_bom > match_ruim


def test_calcular_match_fica_entre_30_e_99():
    match = matcher.calcular_match(
        tags_imovel=set(),
        preco=10_000_000,
        quartos=1,
        tags_pedidas={"perto-do-mar", "moderna", "piscina", "cobertura"},
        orcamento=100_000,
        quartos_pedidos=5,
    )
    assert 30 <= match <= 99
