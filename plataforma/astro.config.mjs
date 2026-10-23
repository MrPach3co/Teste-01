import { defineConfig } from "astro/config";
import sitemap from "@astrojs/sitemap";
import fs from "node:fs";
import yaml from "js-yaml";

// A URL do site vem de conteudo/marca.yaml, para não precisar editar aqui.
const { url_site } = yaml.load(fs.readFileSync("./conteudo/marca.yaml", "utf8"));

export default defineConfig({
  site: url_site,
  trailingSlash: "never",
  build: { format: "file" },
  integrations: [
    sitemap({ filter: (pagina) => !pagina.includes("/estilo") }),
  ],
});
