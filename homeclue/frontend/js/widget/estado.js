// Estado compartilhado do widget e acesso à API pública.
const params = new URLSearchParams(location.search);

function novaSessao() {
  try {
    const salva = sessionStorage.getItem('hc_sessao');
    if (salva) return salva;
    const nova = crypto.randomUUID ? crypto.randomUUID() : String(Math.random()).slice(2);
    sessionStorage.setItem('hc_sessao', nova);
    return nova;
  } catch {
    return String(Math.random()).slice(2);
  }
}

export const estado = {
  chave: params.get('k') || '',
  modo: params.get('modo') || 'pagina',
  sessao: novaSessao(),
  config: null,
  criterios: null,
  historico: [],
  turno: 0,
  buscaId: null,
  resultados: new Map(), // id -> resultado (da última busca em que apareceu)
  comparar: new Set(),
};

export function api(caminho) {
  return `/api/publico/${encodeURIComponent(estado.chave)}${caminho}`;
}

export async function pedir(caminho, opcoes = {}) {
  const r = await fetch(api(caminho), opcoes);
  const dados = await r.json().catch(() => ({}));
  if (!r.ok) {
    const erro = new Error(typeof dados.detail === 'string' ? dados.detail : 'Não foi possível concluir agora. Tente de novo.');
    erro.status = r.status;
    erro.dados = dados;
    throw erro;
  }
  return dados;
}

export function registrarEvento(tipo, imovelId) {
  fetch(api('/eventos'), {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, keepalive: true,
    body: JSON.stringify({ tipo, imovel_id: imovelId ?? null, sessao: estado.sessao }),
  }).catch(() => {});
}

export function linkWhatsApp({ imovelId, unidadeId } = {}) {
  const q = new URLSearchParams({ sessao: estado.sessao });
  if (imovelId) q.set('imovel', imovelId);
  if (unidadeId) q.set('unidade', unidadeId);
  if (estado.buscaId) q.set('busca', estado.buscaId);
  return api(`/whatsapp?${q}`);
}

// Camadas em tela cheia: foco, Esc e botão "voltar" do celular.
const pilha = [];
export function abrirCamada(camada, aoFechar) {
  camada.hidden = false;
  pilha.push({ camada, aoFechar, foco: document.activeElement });
  const focavel = camada.querySelector('button, [href], input, select, textarea');
  if (focavel) focavel.focus();
}
export function fecharCamada() {
  const topo = pilha.pop();
  if (!topo) return;
  topo.camada.hidden = true;
  if (topo.aoFechar) topo.aoFechar();
  if (topo.foco && topo.foco.focus) topo.foco.focus();
}
document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && pilha.length) fecharCamada(); });
