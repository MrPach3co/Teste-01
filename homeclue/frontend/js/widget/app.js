// Widget de busca da Homeclue: conversa (texto, voz, foto), resultados com
// match explicado, rankings, comparação, detalhes e contato.
import { el } from '../comum/util.js';
import { blocoDeResultados } from './cartoes.js';
import { abrirComparador } from './comparador.js';
import { abrirDetalhe } from './detalhe.js';
import { abrirLancamentos } from './lancamentos.js';
import { abrirLead } from './lead.js';
import { estado, pedir } from './estado.js';

const $ = (id) => document.getElementById(id);
const conversa = $('conversa');
const entrada = $('texto');
const botaoEnviar = $('enviar');

function rolar(no) {
  if (no) conversa.scrollTo({ top: no.offsetTop - 12 });
  else conversa.scrollTop = conversa.scrollHeight;
}

function balao(texto, quem) {
  const b = el('div', `balao balao-${quem}`, texto);
  conversa.appendChild(b);
  rolar();
  return b;
}

function digitando() {
  const b = el('div', 'balao balao-ia');
  const d = el('span', 'digitando');
  d.setAttribute('aria-label', 'Procurando');
  d.append(el('i'), el('i'), el('i'));
  b.appendChild(d);
  conversa.appendChild(b);
  rolar();
  return b;
}

function chips(textos, aoClicar) {
  const caixa = el('div', 'chips');
  for (const t of textos) {
    const b = el('button', '', t);
    b.type = 'button';
    b.addEventListener('click', () => aoClicar(t));
    caixa.appendChild(b);
  }
  return caixa;
}

function alternarComparar(id, caixa) {
  if (caixa.checked) {
    if (estado.comparar.size >= 3) {
      caixa.checked = false;
      balao('Dá para comparar até 3 imóveis por vez.', 'ia');
      return;
    }
    estado.comparar.add(id);
  } else {
    estado.comparar.delete(id);
  }
  atualizarBarraComparar();
}

function atualizarBarraComparar() {
  const n = estado.comparar.size;
  $('barra-comparar').hidden = n === 0;
  $('texto-comparar').textContent = `${n} imóve${n === 1 ? 'l' : 'is'} para comparar`;
  $('abrir-comparar').disabled = n < 2;
  document.querySelectorAll('.comparar-check input').forEach((caixa) => {
    const cartao = caixa.closest('.imovel');
    if (cartao && cartao.dataset.id) caixa.checked = estado.comparar.has(Number(cartao.dataset.id));
  });
}

const opcoesCartao = {
  aoDetalhe: (id) => abrirDetalhe(id, { aoContato: contatoDoImovel }),
  aoComparar: alternarComparar,
  aoContato: (imovel) => contatoDoImovel(imovel),
};

function contatoDoImovel(imovel) {
  abrirLead({ imovelId: imovel.id, sobre: `${imovel.titulo}` }, (msg) => balao(msg, 'ia'));
}

function mostrarResposta(resposta, carregando) {
  carregando.remove();
  estado.criterios = resposta.criterios;
  estado.buscaId = resposta.busca_id;
  for (const r of resposta.resultados) estado.resultados.set(r.id, r);
  $('btn-nova').hidden = false;

  const b = balao('', 'ia');
  if (resposta.descricao_foto) b.appendChild(el('p', '', `Na sua foto: ${resposta.descricao_foto}`));
  b.appendChild(el('p', '', resposta.mensagem));
  if (resposta.entendido.length) {
    const entendido = el('div', 'entendido');
    entendido.setAttribute('aria-label', 'O que eu entendi');
    for (const t of resposta.entendido) entendido.appendChild(el('span', '', t));
    b.appendChild(entendido);
  }
  if (resposta.avisos.length) {
    const avisos = el('div', 'avisos');
    for (const a of resposta.avisos) avisos.appendChild(el('span', '', `⚠ ${a}`));
    b.appendChild(avisos);
  }

  if (resposta.resultados.length) {
    conversa.appendChild(blocoDeResultados(resposta, opcoesCartao));
  } else if (!resposta.criterios || resposta.entendido.length) {
    conversa.appendChild(chips(['Deixar meu contato'], () => abrirLead({}, (msg) => balao(msg, 'ia'))));
  }
  if (resposta.sugestoes.length) conversa.appendChild(chips(resposta.sugestoes, (t) => buscar(t)));
  rolar(b);
}

function mostrarErro(erro, carregando) {
  carregando.remove();
  balao(erro.message || 'Sem conexão no momento. Verifique sua internet e tente de novo.', 'ia');
}

async function buscar(texto, modo = 'texto') {
  if (!texto || texto.trim().length < 2) return;
  balao(texto, 'eu');
  const carregando = digitando();
  botaoEnviar.disabled = true;
  estado.turno += 1;
  try {
    const resposta = await pedir('/buscar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        texto, modo, sessao: estado.sessao, turno: estado.turno, criterios: estado.criterios,
        historico: estado.historico.slice(-6),
      }),
    });
    estado.historico.push(texto);
    mostrarResposta(resposta, carregando);
  } catch (erro) {
    mostrarErro(erro, carregando);
  } finally {
    botaoEnviar.disabled = false;
  }
}

async function buscarPorFoto(arquivo) {
  const b = balao('', 'eu');
  const img = el('img');
  img.alt = 'Foto de referência enviada';
  img.src = URL.createObjectURL(arquivo);
  b.append(img, el('span', '', 'Quero algo parecido com esta foto'));
  const carregando = digitando();
  estado.turno += 1;
  const corpo = new FormData();
  corpo.append('foto', arquivo);
  corpo.append('sessao', estado.sessao);
  corpo.append('turno', String(estado.turno));
  if (estado.criterios) corpo.append('criterios', JSON.stringify(estado.criterios));
  try {
    mostrarResposta(await pedir('/buscar-por-foto', { method: 'POST', body: corpo }), carregando);
  } catch (erro) {
    mostrarErro(erro, carregando);
  }
}

// ---------- voz (reconhecimento de fala do próprio navegador) ----------

function configurarVoz() {
  const Reconhecimento = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Reconhecimento) return;
  const botao = $('btn-voz');
  botao.hidden = false;
  let rec = null;
  botao.addEventListener('click', () => {
    if (rec) { rec.stop(); return; }
    rec = new Reconhecimento();
    rec.lang = 'pt-BR';
    rec.interimResults = true;
    rec.continuous = false;
    let final = '';
    botao.classList.add('ouvindo');
    botao.setAttribute('aria-label', 'Parar de ouvir');
    entrada.placeholder = 'Pode falar…';
    rec.onresult = (e) => {
      let parcial = '';
      for (const r of e.results) {
        if (r.isFinal) final = r[0].transcript; else parcial += r[0].transcript;
      }
      entrada.value = final || parcial;
    };
    rec.onerror = (e) => {
      if (e.error === 'not-allowed' || e.error === 'service-not-allowed') {
        balao('Não consegui usar o microfone. Libere o acesso ao microfone no navegador ou digite sua busca.', 'ia');
      }
    };
    rec.onend = () => {
      botao.classList.remove('ouvindo');
      botao.setAttribute('aria-label', 'Falar em vez de digitar');
      entrada.placeholder = 'Ex.: casa com quintal pra cachorro, até 700 mil';
      rec = null;
      const texto = entrada.value.trim();
      if (texto) {
        entrada.value = '';
        buscar(texto, 'voz');
      }
    };
    rec.start();
  });
}

// ---------- início ----------

$('form-busca').addEventListener('submit', (e) => {
  e.preventDefault();
  const texto = entrada.value.trim();
  if (texto.length < 2) return;
  entrada.value = '';
  buscar(texto);
});

$('btn-nova').addEventListener('click', () => {
  estado.criterios = null;
  estado.historico = [];
  estado.buscaId = null;
  estado.comparar.clear();
  atualizarBarraComparar();
  balao('Certo, vamos começar uma busca nova. O que você procura?', 'ia');
  if (estado.config) conversa.appendChild(chips(estado.config.exemplos, (t) => buscar(t)));
  rolar();
  entrada.focus();
});

$('btn-foto').addEventListener('click', () => $('arquivo-foto').click());
$('arquivo-foto').addEventListener('change', (e) => {
  const arquivo = e.target.files[0];
  e.target.value = '';
  if (arquivo) buscarPorFoto(arquivo);
});

$('limpar-comparar').addEventListener('click', () => { estado.comparar.clear(); atualizarBarraComparar(); });
$('abrir-comparar').addEventListener('click', () => abrirComparador(opcoesCartao));
$('btn-lancamentos').addEventListener('click', () => abrirLancamentos());

if (window.parent !== window && estado.modo === 'widget') {
  $('fechar').hidden = false;
  $('fechar').addEventListener('click', () => window.parent.postMessage({ homeclue: 'fechar' }, '*'));
}

async function iniciar() {
  if (!estado.chave) {
    $('nome-imobiliaria').textContent = 'Widget não configurado';
    $('form-busca').hidden = true;
    return;
  }
  try {
    estado.config = await pedir('/config');
  } catch {
    $('nome-imobiliaria').textContent = 'Busca indisponível';
    balao('Não foi possível carregar a busca desta imobiliária.', 'ia');
    $('form-busca').hidden = true;
    return;
  }
  const c = estado.config;
  document.title = `Busca de imóveis — ${c.nome}`;
  $('nome-imobiliaria').textContent = c.nome;
  if (c.logo_url) { $('logo').src = c.logo_url; $('logo').alt = c.nome; $('logo').hidden = false; }
  document.documentElement.style.setProperty('--cor', c.cor_primaria);
  $('marca').hidden = !c.mostrar_marca;
  $('btn-foto').hidden = !c.recursos.busca_por_foto;
  $('btn-lancamentos').hidden = !c.lancamentos;
  $('exemplos').replaceWith(chips(c.exemplos, (t) => buscar(t)));
  configurarVoz();
  const params = new URLSearchParams(location.search);
  if (params.get('q')) buscar(params.get('q'));
  if (params.get('abrir') === 'lancamentos' && c.lancamentos) abrirLancamentos();
}

iniciar();
