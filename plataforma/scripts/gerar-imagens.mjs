#!/usr/bin/env node
// Gera as imagens de compartilhamento (WhatsApp, Instagram, LinkedIn) e o
// ícone para celular, com as cores e fontes da marca.
// Rode de novo sempre que mudar o nome, o slogan ou as cores: npm run imagens
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const RAIZ = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
process.chdir(RAIZ);
const { carregarMarca } = await import("../src/lib/dados.mjs");
const { escaparHtml: e } = await import("../src/lib/comum.mjs");
const { chromium } = await import("playwright");

const marca = carregarMarca();
const c = marca.cores;
const fonte = (arquivo) => pathToFileURL(path.join(RAIZ, "node_modules/@fontsource-variable", arquivo)).href;
const estilos = `
  @font-face { font-family: F; src: url("${fonte("fraunces/files/fraunces-latin-full-normal.woff2")}"); }
  @font-face { font-family: F; font-style: italic; src: url("${fonte("fraunces/files/fraunces-latin-full-italic.woff2")}"); }
  @font-face { font-family: I; src: url("${fonte("instrument-sans/files/instrument-sans-latin-wght-normal.woff2")}"); }
  * { margin: 0; box-sizing: border-box; }
  body { width: 1200px; height: 630px; overflow: hidden; }`;

const og = `<!doctype html><html><head><meta charset="utf-8"><style>${estilos}
  .og { position: relative; width: 1200px; height: 630px; padding: 72px 80px; display: flex; flex-direction: column; justify-content: space-between;
    background: radial-gradient(90% 90% at 100% 0%, ${c.destaque}40, transparent 60%), ${c.primaria}; color: ${c.fundo}; font-family: I; overflow: hidden; }
  .marca { font-family: F; font-size: 34px; }
  h1 { font-family: F; font-weight: 400; font-size: 76px; line-height: 1.02; letter-spacing: -1px; max-width: 900px; font-variation-settings: "SOFT" 100, "WONK" 1; }
  h1 em { color: ${c.destaque}; }
  .rodape { display: flex; gap: 28px; font-size: 22px; opacity: .85; }
  .rodape span::before { content: "✓ "; color: ${c.destaque}; }
  svg { position: absolute; right: -160px; bottom: -200px; width: 640px; fill: none; stroke: ${c.fundo}; stroke-width: .6; opacity: .15; }
</style></head><body><div class="og">
  <div class="marca">${e(marca.nome)}</div>
  <h1>Refeições saudáveis e <em>gostosas</em>, sem complicação.</h1>
  <div class="rodape"><span>Receitas testadas por chef</span><span>Nutrição revisada</span><span>Custo por porção</span></div>
  <svg viewBox="0 0 200 200"><circle cx="100" cy="100" r="95"/><circle cx="100" cy="100" r="70"/><circle cx="100" cy="100" r="45"/><circle cx="100" cy="100" r="20"/></svg>
</div></body></html>`;

const icone = `<!doctype html><html><head><style>* { margin: 0 } body { width: 180px; height: 180px; }
  div { width: 180px; height: 180px; display: grid; place-items: center; background: ${c.primaria}; }
  span { width: 96px; height: 96px; border-radius: 50%; border: 7px solid ${c.fundo}; display: grid; place-items: center; }
  span::after { content: ""; width: 36px; height: 36px; border-radius: 50%; background: ${c.acento}; }
</style></head><body><div><span></span></div></body></html>`;

const navegador = await chromium.launch();
const pagina = await navegador.newPage({ viewport: { width: 1200, height: 630 } });
fs.mkdirSync("public/og", { recursive: true });

const temp = path.join(RAIZ, "public/og/.temp.html");
fs.writeFileSync(temp, og);
await pagina.goto(pathToFileURL(temp).href);
await pagina.evaluate(() => document.fonts.ready);
await pagina.screenshot({ path: "public/og/padrao.png" });

await pagina.setViewportSize({ width: 180, height: 180 });
await pagina.setContent(icone);
await pagina.screenshot({ path: "public/apple-touch-icon.png" });

fs.rmSync(temp);
await navegador.close();

// Favicon SVG com as cores atuais
fs.writeFileSync("public/favicon.svg",
  `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="${c.primaria}"/><circle cx="32" cy="32" r="17" fill="none" stroke="${c.fundo}" stroke-width="3"/><circle cx="32" cy="32" r="7" fill="${c.acento}"/></svg>\n`);

console.log("✓ public/og/padrao.png, public/apple-touch-icon.png e public/favicon.svg atualizados");
