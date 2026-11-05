from app.services.interpretador import interpretar


def test_orcamento_em_varios_formatos():
    assert interpretar("até 2 milhões", []).orcamento_maximo == 2_000_000
    assert interpretar("até 1,5 mi", []).orcamento_maximo == 1_500_000
    assert interpretar("até 800 mil", []).orcamento_maximo == 800_000
    assert interpretar("até R$ 3.500 por mês", []).orcamento_maximo == 3_500
    assert interpretar("até R$ 3.500,00", []).orcamento_maximo == 3_500


def test_quartos_por_extenso():
    assert interpretar("apartamento de dois quartos", []).quartos_minimos == 2
    assert interpretar("3 dormitórios", []).quartos_minimos == 3


def test_tipo_finalidade_e_caracteristicas():
    f = interpretar("Quero alugar um apê? não, uma kitnet mobiliada que aceite cachorro", [])
    assert f.tipo == "studio"
    assert f.finalidade == "aluguel"
    assert set(f.caracteristicas) == {"mobiliado", "pet-friendly"}


def test_varanda_gourmet_nao_duplica():
    assert interpretar("com varanda gourmet", []).caracteristicas == ["varanda-gourmet"]


def test_bairro_sem_acento():
    assert interpretar("casa no jardim botanico", ["Jardim Botânico", "Centro"]).bairros == ["Jardim Botânico"]
