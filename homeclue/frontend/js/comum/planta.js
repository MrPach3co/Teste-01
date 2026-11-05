// Planta interativa: a imagem da planta com os cômodos desenhados por cima.
// Os cômodos que batem com o pedido ficam destacados; clicar mostra detalhes.
import { el, normalizar, svgEl } from './util.js';

// Que cômodos atendem cada característica (espelha services/vocabulario.py).
const COMODOS_DA_CARACTERISTICA = {
  escritorio: ['escritorio'], varanda: ['varanda', 'varanda-gourmet'], 'varanda-gourmet': ['varanda-gourmet'],
  piscina: ['piscina'], jardim: ['quintal', 'jardim'], 'area-de-servico': ['area-de-servico'], suite: ['suite'],
  closet: ['closet'], churrasqueira: ['varanda-gourmet'],
};
const PALAVRAS_DA_CARACTERISTICA = {
  lareira: ['lareira'], churrasqueira: ['churrasqueira'], 'vista-montanha': ['vista'], aquecimento: ['aquec'],
  'ar-condicionado': ['ar condicionado', 'ar-condicionado'],
};

// Devolve Map(id do cômodo -> motivo do destaque).
export function comodosDestacados(comodos, criterios) {
  const destaques = new Map();
  if (!criterios) return destaques;
  const adicionar = (c, motivo) => {
    if (!destaques.has(c.id)) destaques.set(c.id, []);
    if (!destaques.get(c.id).includes(motivo)) destaques.get(c.id).push(motivo);
  };
  const caracteristicas = criterios.caracteristicas || [];
  for (const c of comodos) {
    const notas = normalizar(`${c.nome || ''} ${c.notas || ''}`);
    for (const slug of caracteristicas) {
      if ((COMODOS_DA_CARACTERISTICA[slug] || []).includes(c.tipo)) adicionar(c, 'você pediu');
      if ((PALAVRAS_DA_CARACTERISTICA[slug] || []).some((p) => notas.includes(p))) adicionar(c, 'você pediu');
    }
    if ((criterios.quartos_min || criterios.suites_min) && (c.tipo === 'quarto' || c.tipo === 'suite')) adicionar(c, 'quartos');
    for (const desejo of criterios.desejos || []) {
      const palavras = normalizar(desejo).split(/\s+/).filter((p) => p.length >= 4);
      const sinonimos = /manha|nascente/.test(normalizar(desejo)) ? ['manha', 'nascente'] : [];
      if ([...palavras, ...sinonimos].some((p) => notas.includes(p))) adicionar(c, `“${desejo}”`);
    }
  }
  return new Map([...destaques].map(([id, motivos]) => [id, motivos.join(', ')]));
}

export function desenharPlanta(container, planta, { destaques = new Map(), tipos = {}, aoClicar } = {}) {
  container.replaceChildren();
  container.classList.add('planta');
  const img = el('img');
  img.src = planta.imagem;
  img.alt = 'Planta do imóvel';
  const sobreposicao = svgEl('svg', { viewBox: '0 0 1 1', preserveAspectRatio: 'none', class: 'planta-camada' });
  for (const c of planta.comodos) {
    const ret = svgEl('rect', {
      x: c.x, y: c.y, width: c.w, height: c.h, rx: 0.004,
      class: `planta-comodo${destaques.has(c.id) ? ' destaque' : ''}`, tabindex: 0, role: 'button',
    });
    const titulo = svgEl('title');
    titulo.textContent = `${c.nome || tipos[c.tipo] || c.tipo}${destaques.has(c.id) ? ' — combina com o seu pedido' : ''}`;
    ret.appendChild(titulo);
    const ativar = () => {
      sobreposicao.querySelectorAll('.selecionado').forEach((r) => r.classList.remove('selecionado'));
      ret.classList.add('selecionado');
      if (aoClicar) aoClicar(c);
    };
    ret.addEventListener('click', ativar);
    ret.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); ativar(); } });
    sobreposicao.appendChild(ret);
  }
  container.append(img, sobreposicao);
  // Rótulo nos cômodos que bateram com o pedido (HTML, para o texto não distorcer).
  for (const c of planta.comodos) {
    if (!destaques.has(c.id)) continue;
    const rotulo = el('span', 'planta-rotulo', `✓ ${c.nome || tipos[c.tipo] || c.tipo}`);
    rotulo.style.left = `${c.x * 100}%`;
    rotulo.style.top = `${c.y * 100}%`;
    container.appendChild(rotulo);
  }
  return { img, sobreposicao };
}

export function cartaoComodo(c, tipos, destaque) {
  const cartao = el('div', 'comodo-info');
  cartao.appendChild(el('strong', '', c.nome || tipos[c.tipo] || c.tipo));
  const meta = [tipos[c.tipo], c.area_m2 ? `${c.area_m2} m²` : null].filter(Boolean).join(' · ');
  if (meta) cartao.appendChild(el('span', 'comodo-meta', meta));
  if (destaque) cartao.appendChild(el('span', 'comodo-destaque', `Combina com o seu pedido (${destaque})`));
  if (c.notas) cartao.appendChild(el('p', '', c.notas));
  if (c.fotos && c.fotos.length) {
    const fotos = el('div', 'comodo-fotos');
    for (const url of c.fotos) {
      const a = el('a');
      a.href = url; a.target = '_blank'; a.rel = 'noopener';
      const img = el('img');
      img.src = url; img.alt = `Foto: ${c.nome || tipos[c.tipo] || ''}`; img.loading = 'lazy';
      a.appendChild(img);
      fotos.appendChild(a);
    }
    cartao.appendChild(fotos);
  } else {
    cartao.appendChild(el('span', 'comodo-meta', 'Sem fotos deste cômodo.'));
  }
  return cartao;
}
