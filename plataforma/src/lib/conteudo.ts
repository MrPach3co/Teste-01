// Lê os arquivos de conteudo/*.yaml e valida o formato no momento do build.
// Se algum campo estiver faltando ou errado, o build para com uma mensagem
// dizendo exatamente qual arquivo e qual campo corrigir.
import fs from "node:fs";
import path from "node:path";
import yaml from "js-yaml";
import { z } from "astro/zod";

const PASTA = path.resolve(process.cwd(), "conteudo");

const hex = z.string().regex(/^#[0-9a-fA-F]{6}$/, "use uma cor no formato #RRGGBB");

const MarcaSchema = z.object({
  nome: z.string().min(1),
  nome_metodo: z.string().min(1),
  slogan: z.string(),
  descricao_seo: z.string(),
  url_site: z.string().url(),
  logo: z.string(),
  cores: z.object({
    fundo: hex,
    fundo_alt: hex,
    texto: hex,
    texto_suave: hex,
    primaria: hex,
    acento: hex,
    destaque: hex,
    linha: hex,
  }),
  contato: z.object({
    email: z.string(),
    instagram: z.string(),
    whatsapp: z.string(),
  }),
  ebook: z.object({
    titulo: z.string(),
    preco: z.string(),
    preco_de: z.string(),
    link_checkout: z.string(),
    garantia_dias: z.number().int().positive(),
  }),
  amostra: z.object({
    quantidade_receitas: z.number().int().positive(),
    form_action: z.string(),
    arquivo_pdf: z.string(),
  }),
  empresa: z.object({
    razao_social: z.string(),
    cnpj: z.string(),
    email_privacidade: z.string(),
  }),
});

const EquipeSchema = z.object({
  nutricionista: z.object({
    nome: z.string(),
    registro: z.string(),
    cargo: z.string(),
    foto: z.string(),
    bio: z.string(),
  }),
  chef: z.object({
    nome: z.string(),
    cargo: z.string(),
    fotos: z.array(z.string()),
    bio: z.string(),
  }),
  negocio: z.object({
    nome: z.string(),
    cargo: z.string(),
    mostrar_no_site: z.boolean(),
  }),
});

export function lerYaml<T extends z.ZodTypeAny>(arquivo: string, schema: T): z.infer<T> {
  const caminho = path.join(PASTA, arquivo);
  const bruto = yaml.load(fs.readFileSync(caminho, "utf8"));
  const resultado = schema.safeParse(bruto);
  if (!resultado.success) {
    const erros = resultado.error.issues
      .map((i) => `  • ${i.path.join(".") || "(raiz)"}: ${i.message}`)
      .join("\n");
    throw new Error(`\n\nErro em conteudo/${arquivo}:\n${erros}\n`);
  }
  return resultado.data;
}

export const marca = lerYaml("marca.yaml", MarcaSchema);
export const equipe = lerYaml("equipe.yaml", EquipeSchema);

export type Marca = typeof marca;
