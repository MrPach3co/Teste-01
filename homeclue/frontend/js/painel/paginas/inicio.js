import { el, svgEl } from '../../comum/util.js';
import { api, aviso_bloqueado, cabecalho } from '../nucleo.js';

const numero = (v) => (v === null || v === undefined ? '∞' : v.toLocaleString('pt-BR'));
const reais = (v) => v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 });

function kpi(rotulo, valor, detalhe, uso) {
  const c = el('div', 'cartao kpi');
  c.append(el('span', 'kpi-rotulo', rotulo), el('span', 'kpi-valor', valor));
  if (detalhe) c.appendChild(el('span', 'kpi-detalhe', detalhe));
  if (uso !== undefined) {
    const m = el('div', `medidor${uso >= 0.85 ? ' alerta' : ''}`);
    m.setAttribute('role', 'meter');
    m.setAttribute('aria-valuenow', String(Math.round(uso * 100)));
    m.setAttribute('aria-valuemin', '0');
    m.setAttribute('aria-valuemax', '100');
    m.setAttribute('aria-label', rotulo);
    const i = el('i');
    i.style.width = `${Math.min(100, uso * 100)}%`;
    m.appendChild(i);
    c.appendChild(m);
  }
  return c;
}

// Barras diárias, uma série por gráfico (buscas e leads têm escalas diferentes).
function grafico(titulo, serie, campo, cor, unidade) {
  const fig = el('figure', 'cartao grafico');
  const legenda = el('figcaption', '', titulo);
  legenda.appendChild(el('small', '', 'últimos 30 dias'));
  const L = 600, A = 130, base = A - 1, topo = 6;
  const max = Math.max(1, ...serie.map((d) => d[campo]));
  const passo = L / serie.length;
  const largura = Math.max(2, passo - 2);
  const svg = svgEl('svg', { viewBox: `0 0 ${L} ${A}`, preserveAspectRatio: 'none', role: 'img' });
  const total = serie.reduce((s, d) => s + d[campo], 0);
  svg.setAttribute('aria-label', `${titulo}: ${total} nos últimos 30 dias, máximo de ${max} em um dia.`);
  svg.appendChild(svgEl('line', { x1: 0, x2: L, y1: base, y2: base, class: 'grade-linha' }));
  const dica = document.getElementById('dica');
  serie.forEach((d, i) => {
    const h = d[campo] ? Math.max(3, ((base - topo) * d[campo]) / max) : 0;
    const x = i * passo + 1;
    const r = Math.min(4, largura / 2, h);
    if (h) {
      svg.appendChild(svgEl('path', {
        d: `M${x},${base} V${base - h + r} Q${x},${base - h} ${x + r},${base - h} H${x + largura - r} Q${x + largura},${base - h} ${x + largura},${base - h + r} V${base} Z`,
        fill: cor, class: 'barra', 'data-i': i,
      }));
    }
    const alvo = svgEl('rect', { x: i * passo, y: 0, width: passo, height: A, class: 'alvo' });
    alvo.addEventListener('mousemove', (e) => {
      const [, mes, dia] = d.dia.split('-');
      dica.textContent = `${dia}/${mes} · ${d[campo]} ${unidade}`;
      dica.hidden = false;
      dica.style.left = `${e.clientX + 12}px`;
      dica.style.top = `${e.clientY - 34}px`;
      svg.querySelectorAll('.barra').forEach((b) => b.classList.toggle('foco', b.dataset.i === String(i)));
    });
    alvo.addEventListener('mouseleave', () => { dica.hidden = true; svg.querySelectorAll('.barra.foco').forEach((b) => b.classList.remove('foco')); });
    svg.appendChild(alvo);
  });
  const eixo = el('div', 'grafico-eixo');
  for (const d of [serie[0].dia, serie.at(-1).dia]) { const [, mes, dia] = d.split('-'); eixo.appendChild(el('span', '', `${dia}/${mes}`)); }
  fig.append(legenda, svg, eixo);
  return fig;
}

export async function render(pagina) {
  const m = await api('/api/painel/metricas');
  const p = m.plano;
  const cor = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  pagina.appendChild(cabecalho('Visão geral', 'Como a busca do seu site está trabalhando neste mês — o valor que a Homeclue entrega, em números.'));
  if (p.limite_buscas_mes && m.buscas_mes >= p.limite_buscas_mes) {
    pagina.appendChild(aviso_bloqueado(`As ${numero(p.limite_buscas_mes)} buscas com IA do seu plano acabaram neste mês. `
      + 'A busca do seu site continua funcionando, no modo básico (sem IA), até o mês virar ou você mudar de plano.'));
  }

  const kpis = el('div', 'kpis');
  kpis.append(
    kpi('Conversas no mês', numero(m.conversas_mes), `${numero(m.buscas_mes)} buscas${p.limite_buscas_mes ? ` de ${numero(p.limite_buscas_mes)}` : ''}`,
      p.limite_buscas_mes ? m.buscas_mes / p.limite_buscas_mes : undefined),
    kpi('Leads no mês', numero(m.leads_mes), `${m.leads_whatsapp_mes} pelo WhatsApp · ${m.leads_formulario_mes} pelo formulário`),
    kpi('Conversão', `${m.conversao_mes.toLocaleString('pt-BR')}%`, 'conversas que viraram lead'),
    kpi('Negócios fechados', numero(m.negocios_fechados_mes), m.valor_fechado_mes ? reais(m.valor_fechado_mes) : 'marque no funil de leads'),
  );
  pagina.appendChild(kpis);

  const graficos = el('div', 'graficos');
  graficos.append(grafico('Buscas por dia', m.serie, 'buscas', cor('--serie-buscas'), 'buscas'),
    grafico('Leads por dia', m.serie, 'leads', cor('--serie-leads'), 'leads'));
  pagina.appendChild(graficos);

  const linha = el('div', 'duas-colunas');
  const vistos = el('div', 'cartao bloco');
  vistos.appendChild(el('h2', '', 'Imóveis mais vistos'));
  if (!m.mais_vistos.length) vistos.appendChild(el('p', 'ajuda', 'Assim que as buscas começarem, os imóveis mais procurados aparecem aqui.'));
  const lista = el('ul', 'lista-simples');
  for (const v of m.mais_vistos) {
    const li = el('li');
    li.append(el('span', '', v.titulo), el('small', '', `${v.visualizacoes} aberturas · ${v.aparicoes} buscas · ${v.leads} leads`));
    lista.appendChild(li);
  }
  vistos.appendChild(lista);

  const termos = el('div', 'cartao bloco');
  termos.appendChild(el('h2', '', 'Palavras mais usadas nas buscas'));
  const caixa = el('div', 'termos');
  for (const t of m.termos_populares) { const s = el('span', '', t.termo); s.appendChild(el('b', '', t.total)); caixa.appendChild(s); }
  if (!m.termos_populares.length) caixa.appendChild(el('p', 'ajuda', 'Instale o widget no seu site (Widget no site) para começar.'));
  termos.appendChild(caixa);
  if (m.relatorio_demanda) {
    const link = el('a', 'btn btn-sm', 'Ver o relatório de demanda completo');
    link.href = '#demanda';
    termos.appendChild(link);
  }
  termos.appendChild(el('h2', '', 'Buscas recentes'));
  const recentes = el('ul', 'lista-simples');
  for (const t of m.buscas_recentes) recentes.appendChild(el('li', '', `“${t}”`));
  if (!m.buscas_recentes.length) recentes.appendChild(el('li', 'ajuda', 'Nenhuma busca ainda.'));
  termos.appendChild(recentes);
  linha.append(vistos, termos);
  pagina.appendChild(linha);
}
