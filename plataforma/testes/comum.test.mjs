// Testes das regras que mais importam: soma da lista de compras e formatação.
// Rode com: npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import { montarListaDeCompras, formatarQuantidade, faixaCusto, fracao, criarTextos } from "../src/lib/comum.mjs";

const receitas = {
  a: {
    titulo: "A", porcoes: 2, custo_total_estimado: 20,
    ingredientes: [
      { nome: "Limão", quantidade: 1, unidade: "unidade", secao: "hortifruti" },
      { nome: "farinha", quantidade: 1, unidade: "kg", secao: "graos" },
      { nome: "sal", quantidade: null, unidade: "a-gosto", secao: "temperos", despensa: true },
    ],
  },
  b: {
    titulo: "B", porcoes: 4, custo_total_estimado: 40,
    ingredientes: [
      { nome: "limão", quantidade: 2, unidade: "unidade", secao: "hortifruti" },
      { nome: "Farinha", quantidade: 500, unidade: "g", secao: "graos" },
      { nome: "cebola", quantidade: 0.5, unidade: "unidade", secao: "hortifruti" },
    ],
  },
};

test("soma ingredientes iguais, ignorando maiúsculas, e converte kg em g", () => {
  const lista = montarListaDeCompras([{ receita: "a", porcoes: 2 }, { receita: "b", porcoes: 4 }], receitas);
  const itens = lista.secoes.flatMap((s) => s.itens);
  assert.equal(itens.find((i) => i.nome.toLowerCase() === "limão").quantidade, 3);
  assert.equal(itens.find((i) => i.nome.toLowerCase() === "farinha").texto, "1,5 kg");
  assert.equal(lista.custoTotal, 60);
  assert.equal(lista.refeicoes, 2);
});

test("ajusta pelas porções e arredonda unidades para cima", () => {
  // receita B pede ½ cebola para 4 porções; para 2 porções = ¼ → compra 1 inteira
  const lista = montarListaDeCompras([{ receita: "b", porcoes: 2 }], receitas);
  const cebola = lista.secoes.flatMap((s) => s.itens).find((i) => i.nome === "cebola");
  assert.equal(cebola.quantidade, 1);
  assert.equal(lista.custoTotal, 20);
});

test("itens de despensa ficam separados e 'a gosto' não vira número", () => {
  const lista = montarListaDeCompras([{ receita: "a", porcoes: 2 }], receitas);
  assert.equal(lista.despensa.length, 1);
  assert.equal(lista.despensa[0].texto, "a gosto");
});

test("ignora receitas que não existem mais", () => {
  const lista = montarListaDeCompras([{ receita: "apagada", porcoes: 2 }], receitas);
  assert.equal(lista.refeicoes, 0);
});

test("formata quantidades de cozinha", () => {
  assert.equal(formatarQuantidade(1.5, "xicara"), "1 ½ xícaras");
  assert.equal(formatarQuantidade(1, "colher-sopa"), "1 colher (sopa)");
  assert.equal(formatarQuantidade(240, "g"), "240 g");
  assert.equal(formatarQuantidade(1250, "g"), "1,25 kg");
  assert.equal(formatarQuantidade(null, "a-gosto"), "a gosto");
  assert.equal(fracao(0.33), "⅓");
  assert.equal(fracao(2.75), "2 ¾");
});

test("classifica a faixa de custo por porção", () => {
  const faixas = { economica_ate: 8, moderada_ate: 16 };
  assert.equal(faixaCusto(5, faixas).simbolo, "$");
  assert.equal(faixaCusto(12, faixas).simbolo, "$$");
  assert.equal(faixaCusto(20, faixas).simbolo, "$$$");
});

test("textos: troca atalhos, escapa HTML e aplica itálico", () => {
  const { t, rico } = criarTextos(
    { nome: "Marca", nome_metodo: "M", ebook: { preco: "R$ 1", quantidade_receitas: 50, garantia_dias: 7 }, amostra: { quantidade_receitas: 5 } },
    { nutricionista: { nome: "N" }, chef: { nome: "C" } },
  );
  assert.equal(t("{marca} tem {receitas_ebook} receitas"), "Marca tem 50 receitas");
  assert.equal(rico("<b>*oi*</b>"), "&lt;b&gt;<em>oi</em>&lt;/b&gt;");
});
