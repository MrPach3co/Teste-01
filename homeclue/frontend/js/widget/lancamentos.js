// Lançamentos: lista de empreendimentos e espelho de vendas (2D e 3D).
import { STATUS, espelho2D, espelho3D, legenda } from '../comum/espelho.js';
import { el, reais, reaisCurto } from '../comum/util.js';
import { abrirLead } from './lead.js';
import { abrirCamada, estado, fecharCamada, linkWhatsApp, pedir } from './estado.js';

const camada = document.getElementById('camada-lancamentos');
let vista3d = null;

function topo(titulo, aoVoltar) {
  const t = el('div', 'camada-topo');
  const voltar = el('button', 'btn btn-ghost btn-sm', '← Voltar');
  voltar.type = 'button';
  voltar.addEventListener('click', aoVoltar);
  t.append(voltar, el('h2', '', titulo));
  return t;
}

function limpar3d() {
  if (vista3d) { vista3d.destruir(); vista3d = null; }
}

async function mostrarLista() {
  limpar3d();
  camada.replaceChildren(topo('Lançamentos', fecharCamada));
  const corpo = el('div', 'camada-corpo');
  camada.appendChild(corpo);
  let lista;
  try {
    lista = await pedir('/lancamentos');
  } catch (erro) {
    corpo.appendChild(el('p', 'camada-secao', erro.message));
    return;
  }
  const caixa = el('div', 'lista-lancamentos');
  for (const e of lista) {
    const b = el('button', 'cartao lancamento');
    b.type = 'button';
    b.append(el('strong', '', e.nome), el('span', 'imovel-local', `${e.bairro}, ${e.cidade}${e.previsao_entrega ? ` · entrega ${e.previsao_entrega}` : ''}`),
      el('span', '', `${e.disponivel} disponíveis · ${e.reservada} reservadas · ${e.vendida} vendidas`));
    if (e.preco_a_partir) b.appendChild(el('span', 'imovel-preco', `A partir de ${reais(e.preco_a_partir)}`));
    b.addEventListener('click', () => mostrarEspelho(e.id));
    caixa.appendChild(b);
  }
  corpo.appendChild(caixa);
}

function cartaoUnidade(emp, u) {
  const c = el('div', 'cartao cartao-unidade');
  c.append(el('strong', '', `Unidade ${u.codigo}${emp.torres.length > 1 ? ` — ${u.torre}` : ''} · ${u.andar}º andar`),
    el('span', `st-${u.status}`, STATUS[u.status].rotulo));
  const dados = [u.tipologia, u.area_m2 ? `${u.area_m2} m²` : null, u.quartos ? `${u.quartos} quartos` : null,
    u.vagas ? `${u.vagas} vaga${u.vagas > 1 ? 's' : ''}` : null].filter(Boolean).join(' · ');
  if (dados) c.appendChild(el('span', 'imovel-dados', dados));
  if (u.preco) c.appendChild(el('span', 'imovel-preco', reais(u.preco)));
  if (u.status !== 'vendida') {
    const acoes = el('div', 'imovel-acoes');
    if (emp.whatsapp) {
      const wa = el('a', 'btn btn-sm btn-whatsapp', 'WhatsApp');
      wa.href = linkWhatsApp({ unidadeId: u.id }); wa.target = '_blank'; wa.rel = 'noopener';
      acoes.appendChild(wa);
    }
    const contato = el('button', 'btn btn-sm', u.status === 'reservada' ? 'Entrar na fila' : 'Tenho interesse');
    contato.type = 'button';
    contato.addEventListener('click', () => abrirLead({ unidadeId: u.id, sobre: `${emp.nome} — unidade ${u.codigo}` }));
    acoes.appendChild(contato);
    c.appendChild(acoes);
  }
  return c;
}

async function mostrarEspelho(id) {
  limpar3d();
  let emp;
  try {
    emp = await pedir(`/lancamentos/${id}?sessao=${encodeURIComponent(estado.sessao)}`);
  } catch (erro) {
    camada.appendChild(el('p', 'camada-secao', erro.message));
    return;
  }
  camada.replaceChildren(topo(emp.nome, mostrarLista));
  const corpo = el('div', 'camada-corpo');
  const cabecalho = el('section', 'camada-secao');
  cabecalho.append(
    el('p', 'imovel-local', `${emp.bairro}, ${emp.cidade}${emp.previsao_entrega ? ` · previsão de entrega ${emp.previsao_entrega}` : ''}`),
    el('div', 'resumo-espelho'),
  );
  const resumo = cabecalho.querySelector('.resumo-espelho');
  resumo.append(el('span', '', `${emp.resumo.disponivel} disponíveis`), el('span', '', `${emp.resumo.reservada} reservadas`),
    el('span', '', `${emp.resumo.vendida} vendidas`));
  if (emp.resumo.preco_a_partir) resumo.appendChild(el('strong', '', `a partir de ${reaisCurto(emp.resumo.preco_a_partir)}`));
  if (emp.descricao) cabecalho.appendChild(el('p', 'descricao', emp.descricao));

  const filtros = el('div', 'filtros-espelho');
  const quartos = el('select');
  quartos.setAttribute('aria-label', 'Filtrar por quartos');
  const opcoes = [...new Set(emp.unidades.map((u) => u.quartos).filter(Boolean))].sort();
  quartos.appendChild(new Option('Todos os tamanhos', ''));
  for (const q of opcoes) quartos.appendChild(new Option(`${q} quartos`, String(q)));
  const soDisponiveis = el('label', 'check');
  const caixa = el('input');
  caixa.type = 'checkbox';
  soDisponiveis.append(caixa, document.createTextNode('Só disponíveis'));
  const alternador = el('div', 'alternador');
  const b2d = el('button', '', 'Grade');
  const b3d = el('button', '', 'Prédio 3D');
  b2d.type = b3d.type = 'button';
  alternador.append(b2d, b3d);
  filtros.append(alternador, quartos, soDisponiveis);
  cabecalho.append(filtros, legenda());

  const palco = el('div');
  const detalheUnidade = el('div');
  const secaoEspelho = el('section', 'camada-secao');
  secaoEspelho.append(palco, detalheUnidade);
  corpo.append(cabecalho, secaoEspelho);
  camada.appendChild(corpo);

  let modo = '2d';
  const filtro = (u) => (!quartos.value || String(u.quartos) === quartos.value) && (!caixa.checked || u.status === 'disponivel');
  const aoClicar = (u) => { detalheUnidade.replaceChildren(cartaoUnidade(emp, u)); detalheUnidade.scrollIntoView({ block: 'nearest' }); };
  const desenhar = async () => {
    limpar3d();
    b2d.setAttribute('aria-pressed', modo === '2d' ? 'true' : 'false');
    b3d.setAttribute('aria-pressed', modo === '3d' ? 'true' : 'false');
    if (modo === '2d') {
      palco.className = '';
      espelho2D(palco, emp, { aoClicar, filtro });
    } else {
      palco.className = 'palco-3d';
      vista3d = await espelho3D(palco, emp, { aoClicar, filtro });
    }
  };
  b2d.addEventListener('click', () => { modo = '2d'; desenhar(); });
  b3d.addEventListener('click', () => { modo = '3d'; desenhar(); });
  quartos.addEventListener('change', desenhar);
  caixa.addEventListener('change', desenhar);
  desenhar();
}

export function abrirLancamentos() {
  abrirCamada(camada, limpar3d);
  mostrarLista();
}
