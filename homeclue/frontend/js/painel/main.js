// Painel da imobiliária: roteamento entre seções.
import { el } from '../comum/util.js';
import { api, avisar, estado, sair, token } from './nucleo.js';

const PAGINAS = {
  inicio: () => import('./paginas/inicio.js'),
  imoveis: () => import('./paginas/imoveis.js'),
  integracao: () => import('./paginas/integracao.js'),
  leads: () => import('./paginas/leads.js'),
  demanda: () => import('./paginas/demanda.js'),
  lancamentos: () => import('./paginas/lancamentos.js'),
  bairros: () => import('./paginas/bairros.js'),
  widget: () => import('./paginas/widget.js'),
  equipe: () => import('./paginas/equipe.js'),
  plano: () => import('./paginas/plano.js'),
  conta: () => import('./paginas/conta.js'),
};

const $ = (id) => document.getElementById(id);

export async function recarregarSessao() {
  estado.sessao = await api('/api/auth/sessao');
  const { usuario, imobiliaria } = estado.sessao;
  $('nome-imob').textContent = imobiliaria.nome;
  $('nome-usuario').textContent = usuario.nome;
  $('link-admin').hidden = !estado.sessao.admin;
}

export async function atualizarContadorLeads() {
  try {
    const m = await api('/api/painel/metricas');
    $('contador-leads').textContent = m.leads_novos;
    $('contador-leads').hidden = !m.leads_novos;
  } catch { /* não é crítico */ }
}

let navegacao = 0;
async function navegar() {
  const [nome, query] = location.hash.slice(1).split('?');
  const pagina = PAGINAS[nome] ? nome : 'inicio';
  document.querySelectorAll('.menu a[data-secao]').forEach((a) => {
    a.classList.toggle('ativo', a.dataset.secao === pagina);
    if (a.dataset.secao === pagina) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current');
  });
  if (query && query.includes('pagamento=ok')) {
    avisar('Pagamento recebido! A mudança aparece em instantes, assim que o Stripe confirmar.');
  }
  const minha = ++navegacao;
  const destino = $('pagina');
  destino.replaceChildren(el('p', 'ajuda', 'Carregando…'));
  try {
    const modulo = await PAGINAS[pagina]();
    if (minha !== navegacao) return;
    const conteudo = el('div', 'pilha');
    await modulo.render(conteudo);
    if (minha === navegacao) destino.replaceChildren(conteudo);
  } catch (erro) {
    if (minha === navegacao) destino.replaceChildren(el('p', 'aviso aviso-erro', erro.message));
  }
  window.scrollTo({ top: 0 });
}

$('sair').addEventListener('click', sair);
window.addEventListener('hashchange', navegar);

(async function iniciar() {
  if (!token) { location.replace('entrar.html'); return; }
  try {
    await recarregarSessao();
  } catch (erro) {
    document.body.appendChild(el('p', 'vazio', `Não foi possível abrir o painel: ${erro.message} Recarregue a página.`));
    return;
  }
  $('painel').hidden = false;
  navegar();
  atualizarContadorLeads();
})();
