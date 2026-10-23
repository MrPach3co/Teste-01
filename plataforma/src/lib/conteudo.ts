// Ponto único de acesso ao conteúdo dentro do site.
// A leitura e a validação ficam em dados.mjs (compartilhado com os scripts).
import {
  carregarMarca, carregarEquipe, carregarTextos, carregarDepoimentos, carregarReceitas, resumirReceitas,
} from "./dados.mjs";
import { faixaCusto, criarTextos } from "./comum.mjs";

export const marca = carregarMarca();
export const equipe = carregarEquipe();
export const depoimentos = carregarDepoimentos();
export const receitas = carregarReceitas();
export const receitasResumo = resumirReceitas(receitas);
export const textos = {
  home: carregarTextos("home"),
  amostra: carregarTextos("amostra"),
  preVenda: carregarTextos("pre-venda"),
};

export type Marca = typeof marca;
export type Receita = (typeof receitas)[number];

export const custoPorPorcao = (r: Receita) => r.custo_total_estimado / r.porcoes;
export const faixaDaReceita = (r: Receita) => faixaCusto(custoPorPorcao(r), marca.custo);

/** true enquanto o texto ainda for um marcador do tipo "[NOME DA MARCA]" */
export const pendente = (valor: string) => !valor || /^\[.*\]$/.test(valor.trim());

// ── Textos editáveis ──────────────────────────────────────────
// t("{marca}") → nome da marca · rico("*palavra*") → <em>palavra</em> (use com set:html)
export const { t, rico, simples } = criarTextos(marca, equipe) as {
  t: (texto?: string) => string;
  rico: (texto?: string) => string;
  simples: (texto?: string) => string;
};
