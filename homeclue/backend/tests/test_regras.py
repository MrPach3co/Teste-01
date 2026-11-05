from app.services.busca.criterios import Criterios
from app.services.busca.regras import aplicar_turno, extrair_orcamento, interpretar

B = ["Olaria", "Cônego", "Centro", "Lumiar", "Vila Amélia"]
C = ["Nova Friburgo", "Teresópolis"]


def test_orcamento_em_varios_formatos():
    assert extrair_orcamento("ate 2 milhoes") == (None, 2_000_000)
    assert extrair_orcamento("ate 1,5 mi") == (None, 1_500_000)
    assert extrair_orcamento("ate 800 mil") == (None, 800_000)
    assert extrair_orcamento("ate r$ 3.500 por mes") == (None, 3_500)
    assert extrair_orcamento("entre 300 e 500 mil") == (300_000, 500_000)
    assert extrair_orcamento("acima de 1 milhao") == (1_000_000, None)
    assert extrair_orcamento("3 quartos e 100 m2") == (None, None)


def test_pedido_do_documento():
    c, _ = interpretar("Casa com quintal pra cachorro em Olaria até 600 mil, 3 quartos", B, C)
    assert c.tipos == ["casa"] and c.bairros == ["Olaria"] and c.preco_max == 600_000 and c.quartos_min == 3
    assert set(c.caracteristicas) == {"jardim", "pet-friendly"}


def test_desejos_e_proximidade():
    c, _ = interpretar("apartamento de dois quartos com sala com luz da manhã perto de escola", B, C)
    assert c.quartos_min == 2
    assert c.perto_de == ["escola"]
    assert c.desejos == ["sol da manhã"]


def test_aluguel_inferido_e_mobiliado():
    c, _ = interpretar("até 2.500 por mês um studio mobiliado no Centro", B, C)
    assert c.finalidade == "aluguel" and c.tipos == ["studio"] and c.caracteristicas == ["mobiliado"]


def test_negacao_so_alcanca_o_item_negado():
    c, ajustes = interpretar("casa sem piscina com lareira e vista para a serra", B, C)
    assert "lareira" in c.caracteristicas and "vista-montanha" in c.caracteristicas
    assert ajustes["remover_caracteristicas"] == ["piscina"]


def test_tipo_depois_de_com_nao_e_tipo():
    c, _ = interpretar("casa com terreno grande", B, C)
    assert c.tipos == ["casa"] and "terreno grande" in c.desejos


def test_conversa_refina_troca_e_remove():
    turno1 = aplicar_turno(Criterios(), "quero comprar casa em Olaria até 600 mil com piscina e lareira", B, C)
    assert turno1.bairros == ["Olaria"] and set(turno1.caracteristicas) == {"piscina", "lareira"}
    turno2 = aplicar_turno(turno1, "e no Cônego?", B, C)
    assert turno2.bairros == ["Cônego"] and turno2.preco_max == 600_000
    turno3 = aplicar_turno(turno2, "não precisa de piscina, pode ser mais barato", B, C)
    assert turno3.caracteristicas == ["lareira"] and turno3.preco_max == 510_000


def test_criterios_do_navegador_sao_revalidados():
    c = Criterios.de_dict({"finalidade": "roubar", "tipos": ["casa", "castelo"], "preco_max": -5,
                           "quartos_min": True, "caracteristicas": ["piscina", "<script>"],
                           "desejos": ["x" * 500] + [f"d{i}" for i in range(20)]})
    assert c.finalidade is None and c.tipos == ["casa"] and c.preco_max is None and c.quartos_min is None
    assert c.caracteristicas == ["piscina"] and len(c.desejos) == 8 and len(c.desejos[0]) == 80


def test_resumo_para_o_corretor():
    c = Criterios(finalidade="venda", tipos=["casa"], bairros=["Olaria"], preco_max=600_000, quartos_min=3,
                  caracteristicas=["jardim"], perto_de=["escola"], desejos=["sol da manhã"])
    assert c.resumo() == "Comprar casa em Olaria, até R$ 600 mil, 3+ quartos, jardim / quintal, perto de escola, “sol da manhã”"
