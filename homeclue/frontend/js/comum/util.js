// Utilidades compartilhadas por widget e painel. Texto vindo da API é sempre
// inserido com textContent (função el) — nunca innerHTML.

export function el(tag, classe, texto) {
  const n = document.createElement(tag);
  if (classe) n.className = classe;
  if (texto !== undefined && texto !== null) n.textContent = texto;
  return n;
}

export function svgEl(tag, atributos = {}) {
  const n = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [k, v] of Object.entries(atributos)) n.setAttribute(k, v);
  return n;
}

export function reais(v) {
  if (v === null || v === undefined) return '—';
  return v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 });
}

export function reaisCurto(v) {
  if (v >= 1_000_000) return `R$ ${(v / 1_000_000).toLocaleString('pt-BR', { maximumFractionDigits: 2 })} mi`;
  if (v >= 10_000) return `R$ ${Math.round(v / 1000).toLocaleString('pt-BR')} mil`;
  return reais(v);
}

export function precoDoImovel(imovel, finalidadePedida) {
  if (finalidadePedida === 'aluguel' && imovel.finalidade === 'venda_aluguel' && imovel.preco_aluguel) {
    return { valor: imovel.preco_aluguel, aluguel: true };
  }
  return { valor: imovel.preco, aluguel: imovel.finalidade === 'aluguel' };
}

export function distancia(m) {
  return m >= 1000 ? `${(m / 1000).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} km` : `${Math.round(m / 10) * 10} m`;
}

export function normalizar(t) {
  return (t || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
}

export function gradiente(id) {
  const pares = [['#2E5741', '#9DB8A4'], ['#9C4A26', '#E2B59A'], ['#3B4A5E', '#A9B8C9'], ['#6B5B3E', '#D9C9A3'],
    ['#1F3B2C', '#C9D6C2'], ['#5E3B4A', '#D4AFC0']];
  const [a, b] = pares[id % pares.length];
  return `linear-gradient(135deg, ${a}, ${b})`;
}

export function fundoFoto(no, url, id) {
  if (url) no.style.backgroundImage = `url("${encodeURI(url)}")`;
  else no.style.backgroundImage = gradiente(id);
}

// Vídeos: YouTube e Vimeo viram embed; o resto vira link.
export function urlDeEmbed(url) {
  if (!url) return null;
  let m = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/shorts\/)([\w-]{6,})/);
  if (m) return `https://www.youtube-nocookie.com/embed/${m[1]}`;
  m = url.match(/vimeo\.com\/(\d+)/);
  if (m) return `https://player.vimeo.com/video/${m[1]}`;
  return null;
}

export const ICONE_STATUS = { atende: '✓', parcial: '≈', indicio: '◐', nao_informado: '?', nao_atende: '✗' };
export const ROTULO_STATUS = {
  atende: 'Atende', parcial: 'Quase', indicio: 'Parece ter', nao_informado: 'Não informado', nao_atende: 'Não atende',
};
export const ROTULO_FONTE = {
  anuncio: 'dado do anúncio', titulo: 'título do anúncio', descricao: 'descrição do anúncio',
  comodidades: 'itens do anúncio', planta: 'planta', foto: 'foto (análise automática)', contexto: 'OpenStreetMap',
};

/** "1 busca", "2 buscas" (com o número formatado em pt-BR). */
export function contagem(n, singular, plural = `${singular}s`) {
  return `${Number(n || 0).toLocaleString('pt-BR')} ${Number(n) === 1 ? singular : plural}`;
}
