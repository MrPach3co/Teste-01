import { defineConfig } from "astro/config";
import preact from "@astrojs/preact";
import sitemap from "@astrojs/sitemap";
import fs from "node:fs";
import yaml from "js-yaml";

// A URL do site vem de conteudo/marca.yaml, para não precisar editar aqui.
const { url_site } = yaml.load(fs.readFileSync("./conteudo/marca.yaml", "utf8"));

// Páginas que não devem aparecer no Google
const foraDoSitemap = ["/estilo", "/amostra-gratis/obrigado"];

export default defineConfig({
  site: url_site,
  trailingSlash: "never",
  build: { format: "file" },
  prefetch: { prefetchAll: true, defaultStrategy: "hover" },
  integrations: [
    preact(),
    sitemap({ filter: (pagina) => !foraDoSitemap.some((p) => pagina.replace(/\/$/, "").endsWith(p)) }),
  ],
});
