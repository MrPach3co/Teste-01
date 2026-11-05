// Núcleo do painel: sessão, chamadas à API, avisos, modais e downloads.
import { el } from '../comum/util.js';

let tokenAtual = (() => { try { return localStorage.getItem('hc_token'); } catch { return null; } })();
export const token = tokenAtual;

/** Troca o token da sessão (a troca de senha devolve um novo; os outros aparelhos saem). */
export function guardarToken(novo) {
  tokenAtual = novo;
  try { localStorage.setItem('hc_token', novo); } catch { /* sem armazenamento */ }
}
export const estado = { sessao: null, vocabulario: null };

export function sair() {
  try { localStorage.removeItem('hc_token'); } catch { /* sem armazenamento */ }
  location.replace('entrar.html');
}

function erroDaApi(dados) {
  if (typeof dados.detail === 'string') return dados.detail;
  if (Array.isArray(dados.detail) && dados.detail.length) {
    const d = dados.detail[0];
    const campo = d.loc.filter((p) => p !== 'body').join('.');
    return `${campo ? campo + ': ' : ''}${d.msg.replace(/^Value error, /, '')}`;
  }
  return 'Algo deu errado. Tente de novo.';
}

export async function api(caminho, opcoes = {}) {
  const headers = { Authorization: `Bearer ${tokenAtual}`, ...(opcoes.headers || {}) };
  const config = { ...opcoes, headers };
  if (opcoes.json !== undefined) {
    headers['Content-Type'] = 'application/json';
    config.body = JSON.stringify(opcoes.json);
  }
  const r = await fetch(caminho, config);
  if (r.status === 401) { sair(); throw new Error('Sessão expirada.'); }
  if (r.status === 204) return null;
  const tipo = r.headers.get('content-type') || '';
  const dados = tipo.includes('json') ? await r.json() : await r.blob();
  if (!r.ok) {
    const erro = new Error(tipo.includes('json') ? erroDaApi(dados) : 'Algo deu errado.');
    erro.status = r.status;
    throw erro;
  }
  return dados;
}

export function enviarArquivo(caminho, arquivo, campo = 'arquivo') {
  const corpo = new FormData();
  corpo.append(campo, arquivo);
  return api(caminho, { method: 'POST', body: corpo });
}

let temporizador = null;
export function avisar(texto, tipo = 'ok') {
  const a = document.getElementById('aviso-global');
  a.className = `aviso aviso-${tipo}`;
  a.textContent = texto;
  a.hidden = false;
  clearTimeout(temporizador);
  temporizador = setTimeout(() => { a.hidden = true; }, 6000);
}

export function baixar(blob, nome) {
  const url = URL.createObjectURL(blob);
  const a = el('a');
  a.href = url; a.download = nome;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function vazio(titulo, texto, botao) {
  const v = el('div', 'cartao vazio');
  v.append(el('strong', '', titulo), el('span', '', texto));
  if (botao) v.appendChild(botao);
  return v;
}

export function botao(texto, classe, aoClicar) {
  const b = el('button', `btn ${classe || ''}`.trim(), texto);
  b.type = 'button';
  if (aoClicar) b.addEventListener('click', aoClicar);
  return b;
}

export function cabecalho(titulo, texto, ...acoes) {
  const cab = el('header', acoes.length ? 'cab cab-acoes' : 'cab');
  const textos = el('div');
  textos.appendChild(el('h1', '', titulo));
  if (texto) textos.appendChild(el('p', '', texto));
  cab.appendChild(textos);
  if (acoes.length) {
    const caixa = el('div', 'acoes');
    caixa.append(...acoes);
    cab.appendChild(caixa);
  }
  return cab;
}

export function campo(rotulo, entrada) {
  const l = el('label', 'campo');
  l.append(el('span', '', rotulo), entrada);
  return l;
}

export function entrada(nome, atributos = {}) {
  const tag = atributos.tag || 'input';
  const n = el(tag);
  n.name = nome;
  for (const [k, v] of Object.entries(atributos)) {
    if (k === 'tag' || v === undefined || v === null) continue;
    if (k === 'valor') n.value = v; else n.setAttribute(k, v);
  }
  return n;
}

export function selecao(nome, opcoes, valor) {
  const s = el('select');
  s.name = nome;
  for (const [v, rotulo] of opcoes) {
    const o = el('option', '', rotulo);
    o.value = v;
    s.appendChild(o);
  }
  if (valor !== undefined && valor !== null) s.value = String(valor);
  return s;
}

// Modal genérico: devolve {dialogo, conteudo, rodape, fechar}.
export function abrirModal(titulo, { largo = false } = {}) {
  const dialogo = document.getElementById('modal');
  dialogo.className = `modal${largo ? ' largo' : ''}`;
  dialogo.replaceChildren();
  const conteudo = el('div', 'modal-conteudo');
  const cab = el('div', 'modal-cab');
  const fechar = botao('✕', 'btn-ghost btn-sm', () => dialogo.close());
  fechar.setAttribute('aria-label', 'Fechar');
  cab.append(el('h2', '', titulo), fechar);
  conteudo.appendChild(cab);
  const rodape = el('div', 'modal-rodape');
  dialogo.append(conteudo, rodape);
  dialogo.showModal();
  return { dialogo, conteudo, rodape, fechar: () => dialogo.close() };
}

export function temRecurso(recurso) {
  return estado.sessao && estado.sessao.plano.recursos.includes(recurso);
}

export function ehDono() {
  return estado.sessao && estado.sessao.usuario.papel === 'dono';
}

export function aviso_bloqueado(texto) {
  const caixa = el('div', 'bloqueado');
  caixa.appendChild(el('span', '', texto));
  const link = el('a', 'btn btn-solid btn-sm', 'Ver planos');
  link.href = '#plano';
  caixa.appendChild(link);
  return caixa;
}

export async function garantirVocabulario() {
  if (!estado.vocabulario) estado.vocabulario = await api('/api/imoveis/vocabulario');
  return estado.vocabulario;
}
