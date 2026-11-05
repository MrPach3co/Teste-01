"""O que o comprador pediu, em forma estruturada.

É o "estado" da conversa: a cada mensagem nova, os critérios anteriores são
atualizados (refinar, trocar, tirar) e devolvidos ao widget, que os manda de
volta no turno seguinte. Como vêm do navegador, tudo é revalidado aqui.
"""

from dataclasses import asdict, dataclass, field

from app.services.vocabulario import CARACTERISTICAS, CATEGORIAS_CONTEXTO, NOMES_PERTO_DE, TIPOS, normalizar

MAX_DESEJOS = 8
MAX_ITENS_LISTA = 10


def formatar_reais(valor: float) -> str:
    if valor >= 1_000_000:
        mi = valor / 1_000_000
        texto = f"{mi:.2f}".rstrip("0").rstrip(".").replace(".", ",")
        return f"R$ {texto} mi"
    if valor >= 10_000 and valor % 1_000 == 0:
        return f"R$ {valor / 1_000:.0f} mil"
    return f"R$ {valor:,.0f}".replace(",", ".")


@dataclass
class Criterios:
    finalidade: str | None = None  # "venda" | "aluguel"
    tipos: list[str] = field(default_factory=list)
    cidades: list[str] = field(default_factory=list)
    bairros: list[str] = field(default_factory=list)
    preco_max: float | None = None
    preco_min: float | None = None
    quartos_min: int | None = None
    suites_min: int | None = None
    banheiros_min: int | None = None
    vagas_min: int | None = None
    area_min: float | None = None
    caracteristicas: list[str] = field(default_factory=list)
    perto_de: list[str] = field(default_factory=list)
    desejos: list[str] = field(default_factory=list)

    # ---------- serialização e validação ----------

    def para_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def de_dict(cls, dados: dict | None) -> "Criterios":
        """Aceita dados não confiáveis (do navegador ou da IA) e limpa tudo."""
        if not isinstance(dados, dict):
            return cls()

        def numero(chave, minimo, maximo, inteiro=False):
            valor = dados.get(chave)
            if isinstance(valor, bool) or not isinstance(valor, (int, float)):
                return None
            if not (minimo <= valor <= maximo):
                return None
            return int(valor) if inteiro else float(valor)

        def lista_texto(chave, permitidos=None, tamanho=80, maximo=MAX_ITENS_LISTA):
            valor = dados.get(chave)
            if not isinstance(valor, list):
                return []
            saida: list[str] = []
            for item in valor:
                if not isinstance(item, str):
                    continue
                item = " ".join(item.split())[:tamanho]
                if not item or (permitidos is not None and item not in permitidos):
                    continue
                if normalizar(item) not in {normalizar(s) for s in saida}:
                    saida.append(item)
            return saida[:maximo]

        finalidade = dados.get("finalidade")
        return cls(
            finalidade=finalidade if finalidade in ("venda", "aluguel") else None,
            tipos=lista_texto("tipos", set(TIPOS)),
            cidades=lista_texto("cidades", tamanho=120),
            bairros=lista_texto("bairros", tamanho=120),
            preco_max=numero("preco_max", 1, 1_000_000_000),
            preco_min=numero("preco_min", 1, 1_000_000_000),
            quartos_min=numero("quartos_min", 1, 20, inteiro=True),
            suites_min=numero("suites_min", 1, 20, inteiro=True),
            banheiros_min=numero("banheiros_min", 1, 20, inteiro=True),
            vagas_min=numero("vagas_min", 1, 20, inteiro=True),
            area_min=numero("area_min", 1, 1_000_000),
            caracteristicas=lista_texto("caracteristicas", set(CARACTERISTICAS), maximo=len(CARACTERISTICAS)),
            perto_de=lista_texto("perto_de", set(CATEGORIAS_CONTEXTO)),
            desejos=lista_texto("desejos", maximo=MAX_DESEJOS),
        )

    def vazio(self) -> bool:
        return not any(
            [self.finalidade, self.tipos, self.cidades, self.bairros, self.preco_max, self.preco_min,
             self.quartos_min, self.suites_min, self.banheiros_min, self.vagas_min, self.area_min,
             self.caracteristicas, self.perto_de, self.desejos]
        )

    # ---------- conversa ----------

    def mesclar(self, novo: "Criterios") -> "Criterios":
        """Junta o turno novo ao anterior (usado pelo motor de regras; a IA já
        devolve os critérios completos). Valores simples do turno novo
        substituem; tipo, bairro e cidade novos substituem os antigos (o
        comprador mudou de ideia); itens desejados se acumulam."""

        def unir(a: list[str], b: list[str]) -> list[str]:
            return a + [x for x in b if normalizar(x) not in {normalizar(y) for y in a}]

        return Criterios(
            finalidade=novo.finalidade or self.finalidade,
            tipos=novo.tipos or self.tipos,
            cidades=novo.cidades or self.cidades,
            bairros=novo.bairros or self.bairros,
            preco_max=novo.preco_max or self.preco_max,
            preco_min=novo.preco_min or self.preco_min,
            quartos_min=novo.quartos_min or self.quartos_min,
            suites_min=novo.suites_min or self.suites_min,
            banheiros_min=novo.banheiros_min or self.banheiros_min,
            vagas_min=novo.vagas_min or self.vagas_min,
            area_min=novo.area_min or self.area_min,
            caracteristicas=unir(self.caracteristicas, novo.caracteristicas),
            perto_de=unir(self.perto_de, novo.perto_de),
            desejos=unir(self.desejos, novo.desejos)[:MAX_DESEJOS],
        )

    # ---------- textos ----------

    def rotulos(self) -> list[str]:
        """Chips do que foi entendido — transparência para o comprador."""
        chips: list[str] = []
        if self.finalidade:
            chips.append("Alugar" if self.finalidade == "aluguel" else "Comprar")
        chips.extend(TIPOS[t] for t in self.tipos)
        chips.extend(self.cidades)
        chips.extend(self.bairros)
        if self.preco_min and self.preco_max:
            chips.append(f"{formatar_reais(self.preco_min)} a {formatar_reais(self.preco_max)}")
        elif self.preco_max:
            chips.append(f"Até {formatar_reais(self.preco_max)}")
        elif self.preco_min:
            chips.append(f"A partir de {formatar_reais(self.preco_min)}")
        if self.quartos_min:
            chips.append(f"{self.quartos_min}+ quarto{'s' if self.quartos_min > 1 else ''}")
        if self.suites_min:
            chips.append(f"{self.suites_min}+ suíte{'s' if self.suites_min > 1 else ''}")
        if self.banheiros_min:
            chips.append(f"{self.banheiros_min}+ banheiro{'s' if self.banheiros_min > 1 else ''}")
        if self.vagas_min:
            chips.append(f"{self.vagas_min}+ vaga{'s' if self.vagas_min > 1 else ''}")
        if self.area_min:
            chips.append(f"{self.area_min:g}+ m²")
        chips.extend(CARACTERISTICAS[c] for c in self.caracteristicas)
        chips.extend(f"Perto de {NOMES_PERTO_DE[p]}" for p in self.perto_de)
        chips.extend(f"“{d}”" for d in self.desejos)
        return chips

    def resumo(self) -> str:
        """Uma frase com tudo o que a pessoa procura (vai no WhatsApp do corretor)."""
        partes: list[str] = []
        verbo = {"venda": "Comprar", "aluguel": "Alugar"}.get(self.finalidade or "", "")
        tipos = " ou ".join(TIPOS[t].lower() for t in self.tipos)
        cabeca = " ".join(p for p in [verbo, tipos] if p) or "Imóvel"
        lugares = self.bairros or self.cidades
        if lugares:
            cabeca += " em " + " ou ".join(lugares)
        partes.append(cabeca)
        for rotulo in self.rotulos():
            if rotulo in ("Alugar", "Comprar") or rotulo in self.bairros or rotulo in self.cidades:
                continue
            if rotulo in {TIPOS[t] for t in self.tipos}:
                continue
            partes.append(rotulo if rotulo.startswith("“") else rotulo[0].lower() + rotulo[1:])
        texto = ", ".join(partes)
        return texto[0].upper() + texto[1:]

    def assinatura(self) -> str:
        """Chave para agrupar buscas parecidas no relatório de demanda."""
        faixa = ""
        if self.preco_max:
            passo = 500 if self.finalidade == "aluguel" else 50_000
            faixa = formatar_reais(((self.preco_max + passo - 1) // passo) * passo)
        partes = [
            self.finalidade or "-",
            "/".join(sorted(self.tipos)) or "-",
            "/".join(sorted(normalizar(b) for b in self.bairros)) or "-",
            f"{self.quartos_min or 0}q",
            faixa or "-",
        ]
        return "|".join(partes)
