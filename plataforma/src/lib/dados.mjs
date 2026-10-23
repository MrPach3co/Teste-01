// Lê os arquivos de conteudo/ e valida o formato.
// Usado pelo site (no build) e pelos scripts (gerador do e-book).
// Se algum campo estiver faltando ou errado, o processo para com uma
// mensagem dizendo exatamente qual arquivo e qual campo corrigir.
import fs from "node:fs";
import path from "node:path";
import yaml from "js-yaml";
import { z } from "astro/zod";
import { REFEICOES, OBJETIVOS, DIFICULDADES, SECOES, UNIDADES } from "./comum.mjs";

export const RAIZ = process.cwd();
const PASTA = path.join(RAIZ, "conteudo");

const hex = z.string().regex(/^#[0-9a-fA-F]{6}$/, "use uma cor no formato #RRGGBB");
const umDe = (obj, nome) =>
  z.string().refine((v) => v in obj, { message: `${nome} inválido. Use um destes: ${Object.keys(obj).join(", ")}` });

const MarcaSchema = z.object({
  nome: z.string().min(1),
  nome_metodo: z.string().min(1),
  slogan: z.string(),
  descricao_seo: z.string(),
  url_site: z.string().url(),
  logo: z.string(),
  cores: z.object({
    fundo: hex, fundo_alt: hex, texto: hex, texto_suave: hex,
    primaria: hex, acento: hex, destaque: hex, linha: hex,
  }),
  contato: z.object({ email: z.string(), instagram: z.string(), whatsapp: z.string() }),
  ebook: z.object({
    titulo: z.string(),
    subtitulo: z.string(),
    quantidade_receitas: z.number().int().positive(),
    preco: z.string(),
    preco_de: z.string(),
    parcelamento: z.string(),
    link_checkout: z.string(),
    garantia_dias: z.number().int().positive(),
    previsao_entrega: z.string(),
  }),
  amostra: z.object({
    quantidade_receitas: z.number().int().positive(),
    form_action: z.string(),
    campo_nome: z.string(),
    campo_email: z.string(),
    arquivo_pdf: z.string(),
  }),
  custo: z.object({
    referencia: z.string(),
    economica_ate: z.number().positive(),
    moderada_ate: z.number().positive(),
  }),
  empresa: z.object({
    razao_social: z.string(),
    cnpj: z.string(),
    cidade: z.string(),
    email_privacidade: z.string(),
  }),
});

const EquipeSchema = z.object({
  nutricionista: z.object({
    nome: z.string(), registro: z.string(), cargo: z.string(), foto: z.string(), bio: z.string(),
    formacao: z.array(z.string()).default([]),
  }),
  chef: z.object({
    nome: z.string(), cargo: z.string(), fotos: z.array(z.string()), bio: z.string(),
  }),
  negocio: z.object({ nome: z.string(), cargo: z.string(), mostrar_no_site: z.boolean() }),
});

const DepoimentoSchema = z.object({
  nome: z.string().min(1),
  descricao: z.string().default(""),
  texto: z.string().min(1),
  foto: z.string().default(""),
  autorizado: z.literal(true, {
    errorMap: () => ({ message: "só publique depoimentos com autorização por escrito (autorizado: true)" }),
  }),
  data: z.string().default(""),
});

const IngredienteSchema = z.object({
  nome: z.string().min(1),
  quantidade: z.number().positive().nullable().default(null),
  unidade: umDe(UNIDADES, "unidade").default("a-gosto"),
  secao: umDe(SECOES, "secao").default("outros"),
  nota: z.string().default(""),
  grupo: z.string().default(""),
  despensa: z.boolean().default(false),
}).refine((i) => i.unidade === "a-gosto" || i.quantidade != null, {
  message: "informe a quantidade (ou use unidade: a-gosto)",
});

const ReceitaSchema = z.object({
  titulo: z.string().min(1),
  exemplo: z.boolean().default(false),
  publicada: z.boolean().default(true),
  na_amostra: z.boolean().default(false),
  ordem: z.number().default(999),
  resumo: z.string(),
  foto: z.string().default(""),
  refeicoes: z.array(umDe(REFEICOES, "refeicao")).min(1),
  objetivos: z.array(umDe(OBJETIVOS, "objetivo")).min(1),
  tempo_preparo_min: z.number().int().positive(),
  tempo_ativo_min: z.number().int().positive().optional(),
  porcoes: z.number().int().positive(),
  dificuldade: umDe(DIFICULDADES, "dificuldade").default("facil"),
  custo_total_estimado: z.number().positive(),
  tags: z.array(z.string()).default([]),
  ingredientes: z.array(IngredienteSchema).min(1),
  preparo: z.array(z.string()).min(1),
  dicas: z.array(z.string()).default([]),
  substituicoes: z.array(z.string()).default([]),
  conservacao: z.string().default(""),
  nutricao: z.object({
    porcao: z.string(),
    calorias_kcal: z.number(),
    proteinas_g: z.number(),
    carboidratos_g: z.number(),
    gorduras_g: z.number(),
    fibras_g: z.number(),
    sodio_mg: z.number(),
    revisado_por_nutricionista: z.boolean().default(false),
    data_revisao: z.string().default(""),
  }),
});

function validar(rotulo, bruto, schema) {
  const resultado = schema.safeParse(bruto);
  if (!resultado.success) {
    const erros = resultado.error.issues
      .map((i) => `  • ${i.path.join(".") || "(raiz)"}: ${i.message}`)
      .join("\n");
    throw new Error(`\n\nErro em ${rotulo}:\n${erros}\n`);
  }
  return resultado.data;
}

export function lerYaml(arquivo, schema) {
  const bruto = yaml.load(fs.readFileSync(path.join(PASTA, arquivo), "utf8"));
  return validar(`conteudo/${arquivo}`, bruto, schema);
}

export function carregarMarca() {
  return lerYaml("marca.yaml", MarcaSchema);
}

export function carregarEquipe() {
  return lerYaml("equipe.yaml", EquipeSchema);
}

/** Textos livres (home, pré-venda, amostra). A estrutura é conferida nas páginas. */
export function carregarTextos(nome) {
  return yaml.load(fs.readFileSync(path.join(PASTA, "textos", `${nome}.yaml`), "utf8"));
}

export function carregarDepoimentos() {
  const lista = yaml.load(fs.readFileSync(path.join(PASTA, "depoimentos.yaml"), "utf8"))?.depoimentos ?? [];
  return lista.map((d, i) => validar(`conteudo/depoimentos.yaml (depoimento ${i + 1})`, d, DepoimentoSchema));
}

/**
 * Todas as receitas publicadas, em ordem. O slug (endereço) é o nome do arquivo.
 * Arquivos que começam com "_" (como o _modelo.yaml) são ignorados.
 */
export function carregarReceitas({ incluirRascunhos = false } = {}) {
  const pasta = path.join(PASTA, "receitas");
  return fs.readdirSync(pasta)
    .filter((f) => /\.ya?ml$/.test(f) && !f.startsWith("_"))
    .map((arquivo) => {
      const slug = arquivo.replace(/\.ya?ml$/, "");
      if (!/^[a-z0-9-]+$/.test(slug)) {
        throw new Error(`\n\nNome de arquivo inválido: conteudo/receitas/${arquivo}\n  Use só letras minúsculas sem acento, números e hífens (ex.: frango-ao-limao.yaml).\n`);
      }
      const bruto = yaml.load(fs.readFileSync(path.join(pasta, arquivo), "utf8"));
      return { slug, ...validar(`conteudo/receitas/${arquivo}`, bruto, ReceitaSchema) };
    })
    .filter((r) => incluirRascunhos || r.publicada)
    .sort((a, b) => a.ordem - b.ordem || a.titulo.localeCompare(b.titulo, "pt-BR"));
}

/** Versão enxuta das receitas para os componentes interativos (planejador e lista). */
export function resumirReceitas(receitas) {
  return Object.fromEntries(receitas.map((r) => [r.slug, {
    slug: r.slug,
    titulo: r.titulo,
    exemplo: r.exemplo,
    refeicoes: r.refeicoes,
    objetivos: r.objetivos,
    tempo: r.tempo_preparo_min,
    porcoes: r.porcoes,
    custo_total_estimado: r.custo_total_estimado,
    ingredientes: r.ingredientes.map(({ nome, quantidade, unidade, secao, despensa }) => ({ nome, quantidade, unidade, secao, despensa })),
  }]));
}
