import { contagem, el } from '../../comum/util.js';
import { api, aviso_bloqueado, cabecalho, selecao, temRecurso } from '../nucleo.js';

let dias = 30;

function ranking(titulo, itens, vazioTexto) {
  const c = el('div', 'cartao bloco');
  c.appendChild(el('h2', '', titulo));
  if (!itens.length) { c.appendChild(el('p', 'ajuda', vazioTexto || 'Ainda sem dados.')); return c; }
  const lista = el('ul', 'lista-simples');
  for (const i of itens) {
    const li = el('li');
    li.append(el('span', '', i.nome), el('small', '', contagem(i.buscas, 'conversa')));
    lista.appendChild(li);
  }
  c.appendChild(lista);
  return c;
}

export async function render(pagina) {
  const periodo = selecao('dias', [['7', 'Últimos 7 dias'], ['30', 'Últimos 30 dias'], ['90', 'Últimos 90 dias'], ['365', 'Último ano']], dias);
  periodo.style.width = 'auto';
  periodo.addEventListener('change', () => { dias = Number(periodo.value); window.dispatchEvent(new HashChangeEvent('hashchange')); });
  pagina.appendChild(cabecalho('Relatório de demanda', 'O que as pessoas procuram no seu site, o que acham e o que falta no seu estoque — para saber que imóvel captar.', periodo));

  if (!temRecurso('relatorio_demanda')) {
    pagina.appendChild(aviso_bloqueado('O relatório de demanda faz parte dos planos pagos.'));
  } else {
    const r = await api(`/api/painel/demanda?dias=${dias}`);
    const resumo = el('div', 'kpis');
    for (const [rotulo, valor, detalhe] of [
      ['Conversas', r.conversas, contagem(r.turnos, 'mensagem', 'mensagens')],
      ['Acharam bom resultado', r.acharam_bom_resultado, 'algum imóvel com 70%+'],
      ['Não acharam', r.conversas - r.acharam_bom_resultado, 'oportunidade de captação'],
      ['Pedidos sem oferta', r.pedidos_sem_oferta.length, 'itens que nenhum anúncio comprova'],
    ]) {
      const k = el('div', 'cartao kpi');
      k.append(el('span', 'kpi-rotulo', rotulo), el('span', 'kpi-valor', String(valor)), el('span', 'kpi-detalhe', detalhe));
      resumo.appendChild(k);
    }
    pagina.appendChild(resumo);

    const falta = el('div', 'cartao bloco');
    falta.append(el('h2', '', 'O que procuram e não encontram no seu estoque'),
      el('p', 'ajuda', 'Conversas em que nenhum imóvel chegou a 70% de compatibilidade, agrupadas por perfil.'));
    if (!r.nao_encontrado.length) falta.appendChild(el('p', 'ajuda', 'Nenhuma — todo mundo achou algo bom. 🎉'));
    const tabela = el('table', 'tabela');
    if (r.nao_encontrado.length) {
      const cab = el('tr');
      cab.append(el('th', '', 'Perfil procurado'), el('th', '', 'Conversas'), el('th', '', 'Melhor match médio'));
      tabela.appendChild(cab);
    }
    for (const g of r.nao_encontrado) {
      const tr = el('tr');
      tr.append(el('td', '', g.descricao), el('td', '', String(g.buscas)), el('td', '', g.melhor_match_medio !== null ? `${g.melhor_match_medio}%` : '—'));
      tabela.appendChild(tr);
    }
    const rolagem = el('div', 'rolagem-x');
    rolagem.appendChild(tabela);
    falta.appendChild(rolagem);
    if (r.pedidos_sem_oferta.length) {
      falta.appendChild(el('h2', '', 'Itens pedidos que nenhum anúncio seu comprova ter'));
      const termos = el('div', 'termos');
      for (const i of r.pedidos_sem_oferta) { const s = el('span', '', i.nome); s.appendChild(el('b', '', i.buscas)); termos.appendChild(s); }
      falta.append(termos, el('p', 'ajuda', 'Pode ser falta de imóvel — ou anúncio que tem e não diz. Confira em “Anúncios que precisam melhorar”.'));
    }
    pagina.appendChild(falta);

    const grade = el('div', 'duas-colunas');
    grade.append(ranking('Bairros mais procurados', r.bairros), ranking('Tipos', r.tipos), ranking('Faixas de preço', r.faixas_preco),
      ranking('Quartos', r.quartos), ranking('Itens mais pedidos', r.itens), ranking('Perto de…', r.perto_de),
      ranking('Pedidos em palavras do cliente', r.desejos, 'Quando alguém pede algo como “sala com luz da manhã”, aparece aqui.'));
    pagina.appendChild(grade);
  }

  const qualidade = await api('/api/painel/qualidade');
  const q = el('div', 'cartao bloco');
  q.append(el('h2', '', 'Anúncios que precisam melhorar'),
    el('p', 'ajuda', 'Anúncio pobre não tem de onde a busca tirar o match. Os primeiros da lista são os que mais fazem diferença — inclusive o que os compradores perguntaram e o anúncio não responde.'));
  if (!qualidade.length) q.appendChild(el('p', 'ajuda', 'Tudo certo com os seus anúncios.'));
  const lista = el('ul', 'lista-simples');
  for (const item of qualidade.slice(0, 25)) {
    const li = el('li');
    const esquerda = el('span');
    esquerda.append(el('strong', '', item.titulo), el('br'), el('small', '', item.problemas.join(' · ')));
    li.append(esquerda, el('small', '', item.origem === 'feed' ? 'corrigir no seu sistema' : 'corrigir em Imóveis'));
    lista.appendChild(li);
  }
  q.appendChild(lista);
  pagina.appendChild(q);
}
