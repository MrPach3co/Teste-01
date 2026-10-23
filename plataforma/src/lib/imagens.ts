// URL pública de uma foto da pasta fotos/, já otimizada (para SEO e redes sociais).
import { getImage } from "astro:assets";
import type { ImageMetadata } from "astro";

const arquivos = import.meta.glob<{ default: ImageMetadata }>("/fotos/**/*.{jpg,jpeg,png,webp,avif}");

export async function urlDaFoto(caminho: string, largura = 1200): Promise<string | undefined> {
  const carregar = caminho ? arquivos[`/fotos/${caminho.replace(/^\/+|^fotos\//g, "")}`] : undefined;
  if (!carregar) return undefined;
  const imagem = await getImage({ src: (await carregar()).default, width: largura, format: "jpg" });
  return imagem.src;
}
