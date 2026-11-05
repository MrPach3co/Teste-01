"""Descrição de anúncio escrita pela IA (com plano B por modelo pronto)."""

from app.services.ia.cliente import UsoIA, chamar_texto, disponivel
from app.services.vocabulario import CARACTERISTICAS, TIPOS

_INSTRUCAO = (
    "Você é redator de anúncios imobiliários no Brasil. Escreva uma descrição de anúncio em português do Brasil, "
    "em 2 ou 3 parágrafos curtos, tom profissional e caloroso. Use SOMENTE os dados fornecidos: não invente "
    "características, distâncias, vizinhança, acabamentos nem qualquer coisa que não esteja nos dados — a busca "
    "da imobiliária mostra ao comprador o que o anúncio afirma, e uma invenção vira uma visita perdida. "
    "Sem markdown, emojis ou título — só o texto corrido do anúncio."
)


def _resumo(dados: dict) -> str:
    caracteristicas = ", ".join(CARACTERISTICAS.get(c, c) for c in dados.get("caracteristicas", []))
    finalidade = {"aluguel": "aluguel", "venda_aluguel": "venda ou aluguel"}.get(dados.get("finalidade"), "venda")
    linhas = [
        f"Título: {dados.get('titulo', '')}",
        f"Tipo: {TIPOS.get(dados.get('tipo', ''), dados.get('tipo', ''))} para {finalidade}",
        f"Local: {dados.get('bairro', '')}, {dados.get('cidade', '')}",
    ]
    if dados.get("preco"):
        linhas.append(f"Preço: R$ {dados['preco']:,.0f}".replace(",", "."))
    for campo, nome in (("quartos", "Quartos"), ("suites", "Suítes"), ("banheiros", "Banheiros"), ("vagas", "Vagas")):
        if dados.get(campo) is not None:
            linhas.append(f"{nome}: {dados[campo]}")
    if dados.get("area_m2"):
        linhas.append(f"Área: {dados['area_m2']:g} m²")
    if caracteristicas:
        linhas.append(f"Características: {caracteristicas}")
    if dados.get("observacoes"):
        linhas.append(f"Observações do corretor: {dados['observacoes']}")
    return "\n".join(linhas)


def gerar(dados: dict) -> tuple[str, str, UsoIA]:
    """Retorna (descrição, fonte "ia" | "modelo", uso)."""
    uso = UsoIA()
    if disponivel():
        texto = chamar_texto(uso, system=_INSTRUCAO, conteudo=_resumo(dados))
        if texto:
            return texto.strip(), "ia", uso
    return _modelo_pronto(dados), "modelo", uso


def _modelo_pronto(dados: dict) -> str:
    tipo = TIPOS.get(dados.get("tipo", ""), "Imóvel")
    finalidade = "para alugar" if dados.get("finalidade") == "aluguel" else "à venda"
    partes = [f"{tipo} {finalidade} em {dados.get('bairro', '')}, {dados.get('cidade', '')}"]
    if dados.get("area_m2"):
        partes[0] += f", com {dados['area_m2']:g} m²"
    quartos = dados.get("quartos")
    if quartos:
        partes[0] += f" e {quartos} quarto{'s' if quartos != 1 else ''}"
    partes[0] += "."
    caracteristicas = [CARACTERISTICAS[c].lower() for c in dados.get("caracteristicas", []) if c in CARACTERISTICAS]
    if caracteristicas:
        partes.append("Destaques: " + ", ".join(caracteristicas) + ".")
    if dados.get("vagas"):
        partes.append(f"Conta com {dados['vagas']} vaga{'s' if dados['vagas'] != 1 else ''} de garagem.")
    partes.append("Agende uma visita e conheça pessoalmente.")
    return " ".join(partes)
