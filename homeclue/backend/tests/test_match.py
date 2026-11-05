from app.services.busca import evidencia
from app.services.busca.avaliacao import ImovelBusca, avaliar, taxa_de_match
from app.services.busca.criterios import Criterios


def _imovel(**extra) -> ImovelBusca:
    base = dict(id=1, titulo="Casa em Olaria", tipo="casa", finalidade="venda", preco=550_000, preco_aluguel=None,
                bairro="Olaria", cidade="Nova Friburgo", quartos=3, suites=1, banheiros=2, vagas=None, area_m2=140,
                descricao="")
    base.update(extra)
    return ImovelBusca(**base)


def _ponto(pontos, chave):
    return next(p for p in pontos if p.chave == chave)


def test_cada_ponto_tem_prova():
    imovel = _imovel(descricao="Sala com lareira e sol da manhã. Quintal gramado.", caracteristicas=["jardim"])
    c = Criterios(tipos=["casa"], bairros=["Olaria"], preco_max=600_000, quartos_min=3, caracteristicas=["jardim", "lareira"],
                  desejos=["sol da manhã"])
    pontos = avaliar(imovel, c)
    assert all(p.status == "atende" for p in pontos)
    assert _ponto(pontos, "car:lareira").evidencia == "“Sala com lareira e sol da manhã.”"
    assert _ponto(pontos, "car:jardim").evidencia == "Consta nos itens do anúncio"
    assert taxa_de_match(pontos) == 100


def test_o_que_o_anuncio_nao_diz_fica_nao_informado():
    pontos = avaliar(_imovel(), Criterios(vagas_min=1, caracteristicas=["piscina"], desejos=["rua tranquila"]))
    assert {p.status for p in pontos} == {"nao_informado"}
    assert taxa_de_match(pontos) == 30


def test_negacao_no_anuncio_vira_nao_atende():
    imovel = _imovel(descricao="Apartamento para alugar. Não aceita animais.", caracteristicas=["pet-friendly"])
    ponto = avaliar(imovel, Criterios(caracteristicas=["pet-friendly"]))[0]
    assert ponto.status == "nao_atende" and "Não aceita animais" in ponto.evidencia


def test_sem_garagem_e_sem_vizinhos():
    texto = "Casa sem vizinhos, com piscina. Sem garagem."
    assert evidencia.procurar(["piscina"], [("descricao", texto)]).status == "atende"
    assert evidencia.procurar(["garagem"], [("descricao", texto)]).status == "nao_atende"


def test_preco_um_pouco_acima_e_parcial():
    pontos = avaliar(_imovel(preco=640_000), Criterios(preco_max=600_000))
    assert pontos[0].status == "parcial" and "7% acima" in pontos[0].evidencia


def test_planta_e_contexto_como_fonte():
    imovel = _imovel(comodos=[{"tipo": "escritorio", "nome": "Escritório", "area_m2": 9, "notas": "Janela para o jardim"}],
                     contexto={"categorias": {"escola": {"raio_m": 2000, "mais_proximos": [
                         {"nome": "Escola Municipal X", "distancia_m": 420}]}}})
    pontos = avaliar(imovel, Criterios(caracteristicas=["escritorio"], perto_de=["escola", "saude"]))
    assert _ponto(pontos, "car:escritorio").fonte == "planta"
    assert _ponto(pontos, "perto:escola").status == "atende"
    assert "Escola Municipal X a 420 m" in _ponto(pontos, "perto:escola").evidencia
    assert _ponto(pontos, "perto:saude").status == "nao_informado"


def test_foto_analisada_e_so_indicio():
    imovel = _imovel(analise_fotos={"fotos": [{"url": "https://x/1.jpg", "caracteristicas": ["piscina"]}]})
    ponto = avaliar(imovel, Criterios(caracteristicas=["piscina"]))[0]
    assert ponto.status == "indicio" and ponto.foto == "https://x/1.jpg"


def test_trecho_citado_precisa_existir():
    textos = [("descricao", "Sala ampla com janelas para o nascente, recebe sol da manhã.")]
    assert evidencia.trecho_presente("recebe sol da manhã", textos)
    assert evidencia.trecho_presente("“janelas para o nascente…”", textos)
    assert not evidencia.trecho_presente("sala com vista para o mar", textos)
    assert not evidencia.trecho_presente("sol", textos)  # curto demais para provar algo


def test_frase_livre_com_palavras_na_mesma_frase():
    textos = [("descricao", "No quintal há um pé de jabuticaba carregado.")]
    achado = evidencia.procurar_frase_livre("pé de jabuticaba no quintal", textos)
    assert achado and achado.status == "atende"
