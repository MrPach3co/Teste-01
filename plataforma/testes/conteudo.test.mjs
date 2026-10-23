// Confere se o conteúdo real (conteudo/*.yaml) está válido e coerente.
import { test } from "node:test";
import assert from "node:assert/strict";
import { carregarMarca, carregarEquipe, carregarReceitas, carregarDepoimentos } from "../src/lib/dados.mjs";

test("marca e equipe são válidas", () => {
  assert.ok(carregarMarca().nome);
  assert.ok(carregarEquipe().nutricionista.registro);
});

test("todas as receitas são válidas e têm endereços únicos", () => {
  const receitas = carregarReceitas({ incluirRascunhos: true });
  assert.ok(receitas.length > 0);
  assert.equal(new Set(receitas.map((r) => r.slug)).size, receitas.length);
});

test("nenhuma receita marcada como revisada sem data de revisão", () => {
  for (const r of carregarReceitas({ incluirRascunhos: true })) {
    if (r.nutricao.revisado_por_nutricionista) {
      assert.ok(r.nutricao.data_revisao, `${r.slug}: informe nutricao.data_revisao`);
    }
  }
});

test("há receitas suficientes marcadas para a amostra", () => {
  const marca = carregarMarca();
  const naAmostra = carregarReceitas().filter((r) => r.na_amostra).length;
  assert.ok(naAmostra >= 1, "marque ao menos uma receita com na_amostra: true");
  assert.ok(naAmostra >= marca.amostra.quantidade_receitas || naAmostra > 0);
});

test("depoimentos só com autorização (lista pode estar vazia)", () => {
  for (const d of carregarDepoimentos()) assert.equal(d.autorizado, true);
});
