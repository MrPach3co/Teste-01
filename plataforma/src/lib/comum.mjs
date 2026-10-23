// Rótulos e funções puras compartilhadas entre o site, os componentes
// interativos (planejador, lista de compras) e o gerador do e-book.
// Sem dependências: roda no navegador e no Node.

export const REFEICOES = {
  "cafe-da-manha": "Café da manhã",
  almoco: "Almoço",
  lanche: "Lanche",
  jantar: "Jantar",
};

export const OBJETIVOS = {
  equilibrio: "Equilíbrio",
  "controle-de-peso": "Controle de peso",
  "ganho-de-massa": "Ganho de massa",
};

export const DIFICULDADES = { facil: "Fácil", media: "Média", avancada: "Avançada" };

export const DIAS = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"];
export const DIAS_CURTOS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"];

// Seções do mercado, na ordem em que aparecem na lista de compras
export const SECOES = {
  hortifruti: "Hortifrúti",
  acougue: "Açougue e peixaria",
  "laticinios-ovos": "Laticínios e ovos",
  mercearia: "Mercearia",
  graos: "Grãos, sementes e farinhas",
  padaria: "Padaria",
  congelados: "Congelados",
  temperos: "Temperos e condimentos",
  outros: "Outros",
};

// [singular, plural]. Unidades "contáveis" na cozinha.
export const UNIDADES = {
  g: ["g", "g"],
  kg: ["kg", "kg"],
  ml: ["ml", "ml"],
  l: ["L", "L"],
  unidade: ["un.", "un."],
  "colher-sopa": ["colher (sopa)", "colheres (sopa)"],
  "colher-cha": ["colher (chá)", "colheres (chá)"],
  xicara: ["xícara", "xícaras"],
  dente: ["dente", "dentes"],
  maco: ["maço", "maços"],
  fatia: ["fatia", "fatias"],
  folha: ["folha", "folhas"],
  ramo: ["ramo", "ramos"],
  lata: ["lata", "latas"],
  pitada: ["pitada", "pitadas"],
  "a-gosto": ["a gosto", "a gosto"],
};

const FRACOES = [
  [0, ""], [0.25, "¼"], [1 / 3, "⅓"], [0.5, "½"], [2 / 3, "⅔"], [0.75, "¾"], [1, ""],
];

/** 1.5 → "1 ½", 0.33 → "⅓" (para colheres, xícaras e unidades) */
export function fracao(valor) {
  let inteiro = Math.floor(valor);
  const resto = valor - inteiro;
  let melhor = FRACOES[0];
  for (const f of FRACOES) if (Math.abs(f[0] - resto) < Math.abs(melhor[0] - resto)) melhor = f;
  if (melhor[0] === 1) { inteiro += 1; melhor = FRACOES[0]; }
  if (inteiro === 0 && !melhor[1]) return "¼";
  return [inteiro || "", melhor[1]].filter(Boolean).join(" ");
}

function arredondarMetrico(valor) {
  if (valor >= 100) return Math.round(valor / 10) * 10;
  if (valor >= 10) return Math.round(valor / 5) * 5;
  return Math.round(valor * 10) / 10;
}

/** Converte kg→g e l→ml para poder somar quantidades */
export function normalizar(quantidade, unidade) {
  if (unidade === "kg") return { quantidade: quantidade * 1000, unidade: "g" };
  if (unidade === "l") return { quantidade: quantidade * 1000, unidade: "ml" };
  return { quantidade, unidade };
}

/** Texto da quantidade: (240, "g") → "240 g"; (1500, "g") → "1,5 kg"; (1.5, "xicara") → "1 ½ xícaras" */
export function formatarQuantidade(quantidade, unidade) {
  if (unidade === "a-gosto" || quantidade == null) return UNIDADES["a-gosto"][0];
  let { quantidade: q, unidade: u } = normalizar(quantidade, unidade);
  if (u === "g" && q >= 1000) { q = q / 1000; u = "kg"; }
  if (u === "ml" && q >= 1000) { q = q / 1000; u = "l"; }
  const [sing, plur] = UNIDADES[u] ?? [u, u];
  if (u === "g" || u === "ml") return `${arredondarMetrico(q).toLocaleString("pt-BR")} ${sing}`;
  if (u === "kg" || u === "l") return `${(Math.round(q * 100) / 100).toLocaleString("pt-BR")} ${sing}`;
  const texto = fracao(q);
  return `${texto} ${q > 1 ? plur : sing}`;
}

export function formatarMoeda(valor) {
  return valor.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

export function formatarTempo(minutos) {
  if (minutos < 60) return `${minutos} min`;
  const h = Math.floor(minutos / 60);
  const m = minutos % 60;
  return m ? `${h} h ${m} min` : `${h} h`;
}

/** Faixa de custo por porção: 1 = econômica, 2 = moderada, 3 = especial */
export function faixaCusto(custoPorPorcao, faixas) {
  if (custoPorPorcao <= faixas.economica_ate) return { nivel: 1, simbolo: "$", rotulo: "Econômica" };
  if (custoPorPorcao <= faixas.moderada_ate) return { nivel: 2, simbolo: "$$", rotulo: "Moderada" };
  return { nivel: 3, simbolo: "$$$", rotulo: "Especial" };
}

/** Faixas de tempo usadas nos filtros */
export const FAIXAS_TEMPO = [
  { valor: "15", rotulo: "Até 15 min", max: 15 },
  { valor: "30", rotulo: "Até 30 min", max: 30 },
  { valor: "45", rotulo: "Até 45 min", max: 45 },
];

/**
 * Soma os ingredientes de várias receitas (já com as porções desejadas).
 *
 * @param {{receita: string, porcoes: number}[]} entradas  itens do planejador
 * @param {Record<string, {titulo: string, porcoes: number, custo_total_estimado: number, ingredientes: any[]}>} receitas  por slug
 * @returns {{secoes: {chave: string, rotulo: string, itens: any[]}[], despensa: any[], custoTotal: number, refeicoes: number}}
 */
export function montarListaDeCompras(entradas, receitas) {
  const itens = new Map();
  let custoTotal = 0;
  let refeicoes = 0;

  for (const entrada of entradas) {
    const receita = receitas[entrada.receita];
    if (!receita) continue;
    refeicoes += 1;
    const fator = entrada.porcoes / receita.porcoes;
    custoTotal += receita.custo_total_estimado * fator;

    for (const ing of receita.ingredientes) {
      const base = ing.quantidade == null ? { quantidade: null, unidade: "a-gosto" } : normalizar(ing.quantidade, ing.unidade);
      const chave = `${ing.nome.trim().toLowerCase()}|${base.unidade}`;
      const atual = itens.get(chave) ?? {
        chave,
        nome: ing.nome,
        unidade: base.unidade,
        quantidade: base.quantidade == null ? null : 0,
        secao: ing.secao,
        despensa: Boolean(ing.despensa),
        receitas: [],
      };
      if (atual.quantidade != null && base.quantidade != null) atual.quantidade += base.quantidade * fator;
      if (!atual.receitas.includes(receita.titulo)) atual.receitas.push(receita.titulo);
      itens.set(chave, atual);
    }
  }

  // Na lista de compras, unidades inteiras são arredondadas para cima
  // (não dá para comprar 1,5 ovo).
  for (const item of itens.values()) {
    if (item.quantidade != null && !["g", "ml"].includes(item.unidade)) {
      item.quantidade = Math.ceil(item.quantidade * 2 - 0.01) / 2;
      if (["unidade", "dente", "maco", "lata", "fatia"].includes(item.unidade)) item.quantidade = Math.ceil(item.quantidade);
    }
    item.texto = formatarQuantidade(item.quantidade, item.unidade);
  }

  const todos = [...itens.values()].sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR"));
  const despensa = todos.filter((i) => i.despensa);
  const secoes = Object.entries(SECOES)
    .map(([chave, rotulo]) => ({ chave, rotulo, itens: todos.filter((i) => !i.despensa && (SECOES[i.secao] ? i.secao : "outros") === chave) }))
    .filter((s) => s.itens.length);

  return { secoes, despensa, custoTotal, refeicoes };
}
