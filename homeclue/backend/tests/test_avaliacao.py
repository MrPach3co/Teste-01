from app.avaliacao.buscas import BUSCAS_PADRAO, avaliar, conferir_ponto, relatorio_html
from app.models import Imobiliaria
from app.services.busca.avaliacao import ImovelBusca, Ponto
from app.services.busca.criterios import Criterios


def test_trinta_buscas_sem_nenhuma_invencao(db):
    demo = db.query(Imobiliaria).filter(Imobiliaria.chave_publica == "pk_demo").one()
    resultado = avaliar(db, demo)
    assert len(BUSCAS_PADRAO) == 30 and len(resultado.buscas) == 30
    assert resultado.violacoes == []
    assert resultado.afirmacoes > 150
    assert all(b["resultados"] for b in resultado.buscas)
    assert "violações da trava" in relatorio_html(resultado, demo.nome)


def test_conferidor_pega_invencao():
    imovel = ImovelBusca(id=1, titulo="Casa", tipo="casa", finalidade="venda", preco=500_000, preco_aluguel=None,
                         bairro="Olaria", cidade="Nova Friburgo", quartos=2, descricao="Casa com quintal.")
    c = Criterios(quartos_min=3, caracteristicas=["piscina"])
    inventada = Ponto("car:piscina", "Piscina", "atende", "“Casa com piscina aquecida.”", "descricao", 1.0)
    assert "não está no anúncio" in conferir_ponto(inventada, imovel, c)
    quartos_errado = Ponto("quartos_min", "3+ quartos", "atende", "3 quartos", "anuncio", 2.0)
    assert "não confere" in conferir_ponto(quartos_errado, imovel, c)
    item_inventado = Ponto("car:piscina", "Piscina", "atende", "Consta nos itens do anúncio", "anuncio", 1.0)
    assert conferir_ponto(item_inventado, imovel, c) is not None
