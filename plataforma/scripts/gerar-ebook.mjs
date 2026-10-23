#!/usr/bin/env node
// ─────────────────────────────────────────────────────────────
//  Gerador do e-book em PDF
//
//  Monta o PDF diagramado a partir de conteudo/receitas/*.yaml,
//  com as cores e fontes da marca. Gera duas versões:
//
//   • Amostra grátis → public/downloads/amostra-gratis.pdf
//     (receitas com na_amostra: true; é publicada no site)
//   • E-book completo → ebook/saida/ebook-completo.pdf
//     (todas as receitas publicadas; NÃO vai para o site)
//
//  Uso:
//    npm run ebook              gera as duas versões
//    npm run ebook -- --amostra só a amostra
//    npm run ebook -- --completo só o e-book completo
// ─────────────────────────────────────────────────────────────
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const RAIZ = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
process.chdir(RAIZ);

const { carregarMarca, carregarEquipe, carregarReceitas, carregarTextos } = await import("../src/lib/dados.mjs");
const { montarHtml } = await import("./ebook/modelo.mjs");

const args = process.argv.slice(2);
const tipos = args.includes("--amostra") ? ["amostra"] : args.includes("--completo") ? ["completo"] : ["amostra", "completo"];

const marca = carregarMarca();
const equipe = carregarEquipe();
const textosHome = carregarTextos("home");
const todas = carregarReceitas();

const PASTA_TEMP = path.join(RAIZ, "ebook", ".temp");
fs.mkdirSync(PASTA_TEMP, { recursive: true });
fs.mkdirSync(path.join(RAIZ, "ebook", "saida"), { recursive: true });
fs.mkdirSync(path.join(RAIZ, "public", "downloads"), { recursive: true });

const url = (p) => pathToFileURL(path.join(RAIZ, p)).href;
const recursos = {
  // O CSS vai embutido no HTML: o Paged.js não consegue ler arquivos locais por fetch
  css: fs.readFileSync(path.join(RAIZ, "scripts/ebook/estilo.css"), "utf8"),
  pagedjs: url("node_modules/pagedjs/dist/paged.polyfill.js"),
  fontes: {
    fraunces: url("node_modules/@fontsource-variable/fraunces/files/fraunces-latin-full-normal.woff2"),
    frauncesItalico: url("node_modules/@fontsource-variable/fraunces/files/fraunces-latin-full-italic.woff2"),
    instrument: url("node_modules/@fontsource-variable/instrument-sans/files/instrument-sans-latin-wght-normal.woff2"),
  },
};

// Fotos: reduz para 1600 px de largura para o PDF não ficar pesado
async function prepararFotos(receitas) {
  const sharp = (await import("sharp")).default;
  const fotos = {};
  for (const r of receitas) {
    if (!r.foto) continue;
    const origem = path.join(RAIZ, "fotos", r.foto);
    if (!fs.existsSync(origem)) {
      console.warn(`  ! Foto não encontrada: fotos/${r.foto} (usando placeholder)`);
      continue;
    }
    const destino = path.join(PASTA_TEMP, `${r.slug}.jpg`);
    await sharp(origem).resize({ width: 1600, withoutEnlargement: true }).jpeg({ quality: 82, mozjpeg: true }).toFile(destino);
    fotos[r.slug] = pathToFileURL(destino).href;
  }
  return fotos;
}

let chromium;
try {
  ({ chromium } = await import("playwright"));
} catch {
  console.error("\nO Playwright não está instalado. Rode: npm install && npx playwright install chromium\n");
  process.exit(1);
}

const navegador = await chromium.launch().catch((erro) => {
  console.error("\nNão consegui abrir o Chromium. Rode uma vez: npx playwright install chromium\n");
  console.error(erro.message);
  process.exit(1);
});

for (const tipo of tipos) {
  const receitas = tipo === "amostra"
    ? todas.filter((r) => r.na_amostra).slice(0, marca.amostra.quantidade_receitas)
    : todas;
  if (!receitas.length) {
    console.warn(`  ! Nenhuma receita para a versão "${tipo}". Pulei.`);
    continue;
  }

  console.log(`→ Montando ${tipo === "amostra" ? "a amostra" : "o e-book completo"} (${receitas.length} receitas)…`);
  const fotos = await prepararFotos(receitas);
  const html = montarHtml({ tipo, receitas, fotos, marca, equipe, textosHome, recursos });
  const arquivoHtml = path.join(PASTA_TEMP, `${tipo}.html`);
  fs.writeFileSync(arquivoHtml, html);

  const pagina = await navegador.newPage();
  pagina.on("pageerror", (erro) => console.warn("  ! Erro na diagramação:", erro.message));
  pagina.on("console", (msg) => msg.type() === "error" && console.warn("  ! " + msg.text()));
  await pagina.goto(pathToFileURL(arquivoHtml).href, { waitUntil: "load" });
  await pagina.waitForFunction(() => window.__pronto === true, null, { timeout: 120_000 });
  const paginas = await pagina.evaluate(() => document.querySelectorAll(".pagedjs_page").length);

  const saida = tipo === "amostra"
    ? path.join(RAIZ, "public", marca.amostra.arquivo_pdf.replace(/^\//, ""))
    : path.join(RAIZ, "ebook", "saida", "ebook-completo.pdf");
  fs.mkdirSync(path.dirname(saida), { recursive: true });
  await pagina.pdf({ path: saida, preferCSSPageSize: true, printBackground: true });
  await pagina.close();

  const kb = Math.round(fs.statSync(saida).size / 1024);
  console.log(`  ✓ ${path.relative(RAIZ, saida)} · ${paginas} páginas · ${kb} KB`);
}

await navegador.close();
fs.rmSync(PASTA_TEMP, { recursive: true, force: true });
