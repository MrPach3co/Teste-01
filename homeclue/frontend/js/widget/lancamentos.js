// Lançamentos: lista de empreendimentos e o espelho de vendas imersivo —
// prédio 3D noturno ao fundo, painel escuro com os números, a unidade
// escolhida e a grade de todas as unidades (que também é o caminho acessível
// para quem não usa o 3D).
import { STATUS, espelho2D } from '../comum/espelho.js';
import { predio3D } from '../comum/predio3d.js';
import { contagem, el, reais, reaisCurto } from '../comum/util.js';
import { abrirLead } from './lead.js';
import { abrirCamada, estado, fecharCamada, linkWhatsApp, pedir } from './estado.js';

const camada = document.getElementById('camada-lancamentos');
let vista3d = null;

function limpar3d() {
  if (vista3d) { vista3d.destruir(); vista3d = null; }
}

function botao(texto, classe, aoClicar) {
  const b = el('button', classe, texto);
  b.type = 'button';
  b.addEventListener('click', aoClicar);
  return b;
}

async function mostrarLista() {
  limpar3d();
  camada.className = 'camada imersiva';
  const topo = el('div', 'lanc-topo-lista');
  topo.append(botao('← Voltar', 'lanc-voltar', fecharCamada), el('h2', '', 'Lançamentos'));
  const corpo = el('div', 'lanc-lista');
  camada.replaceChildren(topo, corpo);
  let lista;
  try {
    lista = await pedir('/lancamentos');
  } catch (erro) {
    corpo.appendChild(el('p', 'lanc-aviso', erro.message));
    return;
  }
  if (!lista.length) corpo.appendChild(el('p', 'lanc-aviso', 'Nenhum lançamento no momento.'));
  for (const e of lista) {
    const b = el('button', 'lancamento');
    b.type = 'button';
    const contagens = el('span', 'lanc-contagens');
    contagens.append(el('span', 'st-disponivel', contagem(e.disponivel, 'disponível', 'disponíveis')),
      el('span', 'st-reservada', contagem(e.reservada, 'reservada')), el('span', 'st-vendida', contagem(e.vendida, 'vendida')));
    b.append(el('span', 'lanc-sobretitulo', `${e.bairro}, ${e.cidade}${e.previsao_entrega ? ` · entrega ${e.previsao_entrega}` : ''}`),
      el('strong', '', e.nome), contagens);
    if (e.preco_a_partir) b.appendChild(el('span', 'lanc-a-partir', `a partir de ${reais(e.preco_a_partir)}`));
    b.appendChild(el('span', 'lanc-abrir', 'Ver o prédio em 3D →'));
    b.addEventListener('click', () => mostrarEspelho(e.id));
    corpo.appendChild(b);
  }
}

function ficha(rotulo, valor) {
  const d = el('div');
  d.append(el('dt', '', rotulo), el('dd', '', valor));
  return d;
}

function cartaoUnidade(emp, u) {
  const c = el('div', 'unidade-card');
  const topo = el('div', 'uc-topo');
  topo.append(el('span', 'uc-codigo', `Apto ${u.codigo}`), el('span', `uc-status st-${u.status}`, STATUS[u.status].rotulo));
  c.appendChild(topo);
  c.appendChild(el('span', 'uc-sub', `${u.andar}º andar${emp.torres.length > 1 ? ` · ${u.torre}` : ''}${u.tipologia ? ` · ${u.tipologia}` : ''}`));
  if (u.status === 'vendida') c.appendChild(el('span', 'uc-preco uc-vendida', 'Unidade vendida'));
  else if (u.preco) c.appendChild(el('span', 'uc-preco', reais(u.preco)));
  else c.appendChild(el('span', 'uc-preco uc-sob-consulta', 'Preço sob consulta'));
  const fichas = el('dl', 'uc-fichas');
  if (u.area_m2) fichas.appendChild(ficha('Área', `${u.area_m2} m²`));
  if (u.quartos) fichas.appendChild(ficha('Quartos', String(u.quartos)));
  if (u.suites) fichas.appendChild(ficha('Suítes', String(u.suites)));
  if (u.vagas) fichas.appendChild(ficha('Vagas', String(u.vagas)));
  if (u.area_m2 && u.preco && u.status !== 'vendida') fichas.appendChild(ficha('R$/m²', reaisCurto(Math.round(u.preco / u.area_m2))));
  if (fichas.children.length) c.appendChild(fichas);
  if (u.status !== 'vendida') {
    const acoes = el('div', 'uc-acoes');
    if (emp.whatsapp) {
      const wa = el('a', 'btn btn-whatsapp', 'Falar no WhatsApp');
      wa.href = linkWhatsApp({ unidadeId: u.id });
      wa.target = '_blank';
      wa.rel = 'noopener';
      acoes.appendChild(wa);
    }
    acoes.appendChild(botao(u.status === 'reservada' ? 'Entrar na fila' : 'Tenho interesse', 'btn btn-claro',
      () => abrirLead({ unidadeId: u.id, sobre: `${emp.nome} — unidade ${u.codigo}` })));
    c.appendChild(acoes);
  }
  c.appendChild(el('p', 'uc-nota', 'Preço e disponibilidade informados pela imobiliária. Confirme com o corretor.'));
  return c;
}

async function mostrarEspelho(id) {
  limpar3d();
  let emp;
  try {
    emp = await pedir(`/lancamentos/${id}?sessao=${encodeURIComponent(estado.sessao)}`);
  } catch (erro) {
    camada.appendChild(el('p', 'lanc-aviso', erro.message));
    return;
  }
  camada.className = 'camada imersiva';
  let filtroStatus = '';
  let selecionada = null;
  let andarAtivo = null;

  // Cena 3D e o que flutua sobre ela
  const cena = el('div', 'lanc-cena');
  const palco = el('div', 'palco-3d');
  const topo = el('div', 'lanc-topo');
  const titulo = el('div', 'lanc-titulo');
  titulo.append(el('span', 'lanc-sobretitulo', `Lançamento · ${emp.bairro}, ${emp.cidade}`), el('h2', '', emp.nome));
  if (emp.previsao_entrega) titulo.appendChild(el('span', 'lanc-entrega', `Entrega ${emp.previsao_entrega}`));
  const voltar = botao('←', 'lanc-voltar lanc-voltar-icone', mostrarLista);
  voltar.setAttribute('aria-label', 'Voltar para a lista de lançamentos');
  topo.append(voltar, titulo);

  const filtros = el('div', 'lanc-filtros');
  const chips = [['', 'Todas', emp.unidades.length], ['disponivel', 'Disponíveis', emp.resumo.disponivel],
    ['reservada', 'Reservadas', emp.resumo.reservada], ['vendida', 'Vendidas', emp.resumo.vendida]].map(([chave, rotulo, n]) => {
    const b = botao('', `lanc-chip${chave ? ` st-${chave}` : ''}`, () => { filtroStatus = chave; atualizar(); });
    b.dataset.status = chave;
    b.append(el('i'), el('span', '', rotulo), el('b', '', String(n)));
    return b;
  });
  const tamanhos = el('select', 'lanc-select');
  tamanhos.setAttribute('aria-label', 'Filtrar por tamanho');
  tamanhos.appendChild(new Option('Todos os tamanhos', ''));
  for (const q of [...new Set(emp.unidades.map((u) => u.quartos).filter(Boolean))].sort()) {
    tamanhos.appendChild(new Option(`${q} quarto${q > 1 ? 's' : ''}`, String(q)));
  }
  tamanhos.addEventListener('change', () => atualizar());
  filtros.append(...chips, tamanhos);

  const andares = el('div', 'lanc-andares');
  andares.setAttribute('role', 'group');
  andares.setAttribute('aria-label', 'Andares');
  const maxAndar = Math.max(...emp.torres.map((t) => t.andares));
  const botoesAndar = [];
  for (let a = maxAndar; a >= 1; a -= 1) {
    const b = botao(`${a}º`, 'lanc-andar', () => {
      andarAtivo = andarAtivo === a ? null : a;
      if (vista3d) {
        if (andarAtivo) vista3d.focarAndar(andarAtivo);
        else vista3d.visaoGeral();
      }
      atualizar({ redesenhar3d: false });
    });
    b.dataset.andar = String(a);
    b.setAttribute('aria-label', `${a}º andar`);
    botoesAndar.push(b);
    andares.appendChild(b);
  }
  const geral = botao('Tudo', 'lanc-andar lanc-andar-geral', () => {
    andarAtivo = null;
    if (vista3d) vista3d.visaoGeral();
    atualizar({ redesenhar3d: false });
  });
  geral.setAttribute('aria-label', 'Ver o prédio inteiro');
  andares.appendChild(geral);
  const ajuda = el('p', 'lanc-ajuda', 'Arraste para girar · role ou pince para aproximar · toque numa janela');
  cena.append(palco, topo, filtros, andares, ajuda);

  // Painel
  const painel = el('aside', 'lanc-painel');
  const numeros = el('section', 'lanc-numeros');
  const grupoNumeros = el('div', 'lanc-numeros-grade');
  const numero = (rotulo, valor, classe) => {
    const d = el('div', `lanc-numero ${classe || ''}`);
    d.append(el('b', '', valor), el('span', '', rotulo));
    return d;
  };
  grupoNumeros.append(numero('disponíveis', String(emp.resumo.disponivel), 'st-disponivel'),
    numero('reservadas', String(emp.resumo.reservada), 'st-reservada'),
    numero('vendidas', String(emp.resumo.vendida), 'st-vendida'));
  if (emp.resumo.preco_a_partir) grupoNumeros.appendChild(numero('a partir de', reaisCurto(emp.resumo.preco_a_partir), 'lanc-numero-preco'));
  const total = Math.max(emp.unidades.length, 1);
  const barra = el('div', 'lanc-barra');
  barra.setAttribute('role', 'img');
  barra.setAttribute('aria-label', `${emp.resumo.disponivel} disponíveis, ${emp.resumo.reservada} reservadas e ${emp.resumo.vendida} vendidas de ${emp.unidades.length}`);
  for (const [chave, n] of [['vendida', emp.resumo.vendida], ['reservada', emp.resumo.reservada], ['disponivel', emp.resumo.disponivel]]) {
    if (!n) continue;
    const parte = el('i', `st-${chave}`);
    parte.style.flexGrow = String(n);
    barra.appendChild(parte);
  }
  const ocupadas = emp.resumo.vendida + emp.resumo.reservada;
  numeros.append(grupoNumeros, barra, el('p', 'lanc-vendido', `${Math.round((ocupadas / total) * 100)}% das unidades já vendidas ou reservadas`));

  const unidade = el('section', 'lanc-unidade');
  const vazio = el('div', 'unidade-vazia');
  vazio.append(el('strong', '', 'Escolha uma unidade'), el('span', '', 'Toque numa janela do prédio ou num apartamento da grade para ver preço, metragem e falar com o corretor.'));
  unidade.appendChild(vazio);

  const grade = el('section', 'lanc-grade');
  const legendaGrade = el('div', 'lanc-legenda');
  for (const [chave, s] of Object.entries(STATUS)) legendaGrade.appendChild(el('span', `st-${chave}`, s.rotulo));
  const gradeCorpo = el('div', 'lanc-grade-corpo');
  grade.append(el('h3', '', 'Espelho de vendas'), legendaGrade, gradeCorpo);

  painel.append(numeros, unidade, grade);
  if (emp.descricao) {
    const sobre = el('section', 'lanc-sobre');
    sobre.append(el('h3', '', 'Sobre o empreendimento'), el('p', '', emp.descricao));
    painel.appendChild(sobre);
  }

  const raiz = el('div', 'lanc');
  raiz.append(cena, painel);
  camada.replaceChildren(raiz);

  const filtro = (u) => (!filtroStatus || u.status === filtroStatus) && (!tamanhos.value || String(u.quartos) === tamanhos.value);
  function desenharGrade() {
    espelho2D(gradeCorpo, emp, { aoClicar: (u) => escolher(u), filtro, marcada: (u) => Boolean(selecionada && u.id === selecionada.id) });
  }
  function escolher(u, { doPredio = false } = {}) {
    selecionada = u;
    unidade.replaceChildren(cartaoUnidade(emp, u));
    if (vista3d && !doPredio) vista3d.selecionar(u);
    desenharGrade();
    if (matchMedia('(max-width: 899px)').matches) unidade.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
  function atualizar({ redesenhar3d = true } = {}) {
    for (const c of chips) c.setAttribute('aria-pressed', c.dataset.status === filtroStatus ? 'true' : 'false');
    for (const b of botoesAndar) b.setAttribute('aria-pressed', String(Number(b.dataset.andar) === andarAtivo));
    geral.setAttribute('aria-pressed', andarAtivo === null ? 'true' : 'false');
    if (redesenhar3d && vista3d) vista3d.repintar();
    desenharGrade();
  }
  atualizar();
  vista3d = await predio3D(palco, emp, { aoClicar: (u) => escolher(u, { doPredio: true }), filtro });
}

export function abrirLancamentos() {
  abrirCamada(camada, limpar3d);
  mostrarLista();
}
