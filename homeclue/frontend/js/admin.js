// Painel do dono da Homeclue (acesso por ADMIN_EMAILS no servidor).
import { el } from './comum/util.js';

const token = (() => { try { return localStorage.getItem('hc_token'); } catch { return null; } })();
const $ = (id) => document.getElementById(id);
const reais = (v) => (v === null || v === undefined ? '—' : v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', minimumFractionDigits: 2, maximumFractionDigits: 4 }));

function tabela(no, cabecalho, linhas) {
  no.replaceChildren();
  const tr = el('tr');
  for (const c of cabecalho) tr.appendChild(el('th', '', c));
  no.appendChild(tr);
  for (const linha of linhas) {
    const l = el('tr');
    for (const c of linha) l.appendChild(el('td', '', c === null || c === undefined ? '—' : String(c)));
    no.appendChild(l);
  }
  if (!linhas.length) { const l = el('tr'); const td = el('td', 'ajuda', 'Sem dados ainda.'); td.colSpan = cabecalho.length; l.appendChild(td); no.appendChild(l); }
}

async function carregar() {
  if (!token) { location.replace('entrar.html'); return; }
  const r = await fetch(`/api/admin/resumo?cotacao=${encodeURIComponent($('cotacao').value)}`, { headers: { Authorization: `Bearer ${token}` } });
  if (!r.ok) {
    $('aviso').className = 'aviso aviso-erro';
    $('aviso').textContent = r.status === 403 ? 'Acesso restrito ao time da Homeclue (ADMIN_EMAILS).' : 'Não foi possível carregar.';
    $('aviso').hidden = false;
    return;
  }
  const d = await r.json();
  $('totais').replaceChildren();
  for (const [rotulo, valor, detalhe] of [
    ['Clientes', d.totais.clientes, `${d.totais.usuarios} usuários`],
    ['Receita mensal (tabela)', reais(d.totais.receita_mensal_brl), 'soma dos planos ativos'],
    ['Custo de IA no mês', reais(d.totais.custo_ia_mes_brl), d.modelo_configurado ? `modelo: ${d.modelo_configurado}` : 'IA não configurada'],
    ['Margem sobre IA', reais(d.totais.receita_mensal_brl - d.totais.custo_ia_mes_brl), 'antes de hospedagem e impostos'],
  ]) {
    const k = el('div', 'cartao kpi');
    k.append(el('span', 'kpi-rotulo', rotulo), el('span', 'kpi-valor', String(valor)), el('span', 'kpi-detalhe', detalhe));
    $('totais').appendChild(k);
  }
  tabela($('modelos'), ['Modelo', 'Buscas com IA', 'Custo médio/busca', 'Tokens entrada (média)', 'Tokens saída (média)'],
    d.custo_por_modelo.map((m) => [m.modelo, m.buscas, reais(m.custo_medio_brl), m.tokens_entrada_medio, m.tokens_saida_medio]));
  tabela($('clientes'), ['Imobiliária', 'Plano', 'Imóveis', 'Feed', 'Buscas (mês)', 'Leads (mês)', 'Custo IA (mês)', 'Custo/busca', 'Desde'],
    d.clientes.map((c) => [c.nome, c.plano, c.imoveis, c.feed || '—', c.buscas_mes, c.leads_mes, reais(c.custo_ia_mes_brl),
      reais(c.custo_por_busca_brl), new Date(c.criado_em).toLocaleDateString('pt-BR')]));
}

$('cotacao').addEventListener('change', carregar);
carregar();
