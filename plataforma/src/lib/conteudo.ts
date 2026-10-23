// Ponto único de acesso ao conteúdo dentro do site.
// A leitura e a validação ficam em dados.mjs (compartilhado com os scripts).
import {
  carregarMarca, carregarEquipe, carregarTextos, carregarDepoimentos, carregarReceitas, resumirReceitas,
} from "./dados.mjs";
import { faixaCusto } from "./comum.mjs";

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

const atalhos: Record<string, string> = {
  marca: marca.nome,
  metodo: marca.nome_metodo,
  nutricionista: equipe.nutricionista.nome,
  chef: equipe.chef.nome,
  preco: marca.ebook.preco,
  receitas_ebook: String(marca.ebook.quantidade_receitas),
  receitas_amostra: String(marca.amostra.quantidade_receitas),
  garantia: String(marca.ebook.garantia_dias),
};

/** Troca {marca}, {preco} etc. pelos valores da configuração */
export function t(texto: string = ""): string {
  return texto.replace(/\{(\w+)\}/g, (original, chave) => atalhos[chave] ?? original);
}

const escapar = (s: string) =>
  s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

/** Como t(), e transforma *palavra* em <em>palavra</em>. Use com set:html. */
export function rico(texto: string = ""): string {
  return escapar(t(texto)).replace(/\*([^*]+)\*/g, "<em>$1</em>");
}

/** Remove os asteriscos (para <title>, meta e PDF sem formatação) */
export const simples = (texto: string = "") => t(texto).replace(/\*/g, "");
