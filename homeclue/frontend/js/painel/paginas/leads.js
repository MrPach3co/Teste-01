import { el } from '../../comum/util.js';
import { api, avisar, baixar, botao, cabecalho, entrada, selecao, vazio } from '../nucleo.js';
import { atualizarContadorLeads } from '../main.js';

const STATUS = {
  novo: 'Novo', em_contato: 'Em contato', visita: 'Visita marcada', proposta: 'Proposta', fechado: 'Fechado', perdido: 'Perdido',
};
const filtro = { status: '', origem: '', q: '' };
const data = (iso) => new Date(iso + (iso.endsWith('Z') ? '' : 'Z')).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });

function numeroWhatsApp(telefone) {
  const d = (telefone || '').replace(/\D/g, '');
  return d.length <= 11 ? `55${d}` : d;
}

async function salvar(lead, campos, mensagem) {
  try {
    await api(`/api/leads/${lead.id}`, { method: 'PATCH', json: campos });
    if (mensagem) avisar(mensagem);
    atualizarContadorLeads();
  } catch (e) { avisar(e.message, 'erro'); }
}

function cartao(lead, recarregar) {
  const c = el('article', 'cartao lead');
  const principal = el('div');
  const titulo = el('h3', '', lead.nome || (lead.origem === 'whatsapp' ? 'Contato pelo WhatsApp' : 'Sem nome'));
  if (lead.codigo) titulo.appendChild(el('span', 'codigo', lead.codigo));
  titulo.appendChild(el('span', 'etiqueta', lead.origem === 'whatsapp' ? 'WhatsApp' : 'Formulário'));
  const sobre = lead.unidade_descricao || lead.imovel_titulo;
  principal.append(titulo, el('div', 'meta', [`Chegou em ${data(lead.criado_em)}`, sobre ? `interessado em ${sobre}` : null,
    lead.match !== null ? `${lead.match}% compatível` : null, lead.corretor_nome ? `corretor: ${lead.corretor_nome}` : null].filter(Boolean).join(' · ')));

  const contatos = el('div', 'contatos');
  if (lead.telefone) {
    const wa = el('a', 'btn btn-sm btn-whatsapp', 'WhatsApp');
    wa.href = `https://wa.me/${numeroWhatsApp(lead.telefone)}`; wa.target = '_blank'; wa.rel = 'noopener';
    const tel = el('a', 'btn btn-sm', lead.telefone);
    tel.href = `tel:${lead.telefone.replace(/[^\d+]/g, '')}`;
    contatos.append(wa, tel);
  }
  if (lead.email) { const m = el('a', 'btn btn-sm', lead.email); m.href = `mailto:${lead.email}`; contatos.appendChild(m); }
  if (lead.origem === 'whatsapp' && !lead.telefone) {
    contatos.appendChild(el('span', 'ajuda', `A pessoa chamou no WhatsApp com o código ${lead.codigo}. Ache a conversa e complete os dados aqui.`));
  }
  principal.appendChild(contatos);
  if (lead.resumo_busca || lead.busca_texto) {
    const q = el('div', 'citacao');
    q.append(el('b', '', 'Procura: '), document.createTextNode(lead.resumo_busca || `“${lead.busca_texto}”`));
    principal.appendChild(q);
  }
  if (lead.mensagem) {
    const q = el('div', 'citacao');
    q.append(el('b', '', 'Mensagem: '), document.createTextNode(lead.mensagem));
    principal.appendChild(q);
  }

  const lado = el('div', 'lead-lado');
  const status = selecao('status', Object.entries(STATUS), lead.status);
  status.setAttribute('aria-label', 'Etapa do lead');
  const valor = entrada('valor', { type: 'number', min: 0, step: 1000, valor: lead.valor_negocio, placeholder: 'Valor do negócio (R$)' });
  valor.hidden = !['proposta', 'fechado'].includes(lead.status);
  status.addEventListener('change', () => {
    valor.hidden = !['proposta', 'fechado'].includes(status.value);
    salvar(lead, { status: status.value }, `${lead.nome || lead.codigo}: ${STATUS[status.value]}.`);
  });
  valor.addEventListener('change', () => salvar(lead, { valor_negocio: valor.value ? Number(valor.value) : null }, 'Valor salvo.'));
  const notas = entrada('notas', { tag: 'textarea', valor: lead.notas, maxlength: 5000, placeholder: 'Anotações (salvam ao sair do campo)' });
  notas.addEventListener('change', () => salvar(lead, { notas: notas.value }, 'Anotação salva.'));
  lado.append(status, valor, notas);
  if (lead.origem === 'whatsapp') {
    const nome = entrada('nome', { valor: lead.nome, placeholder: 'Nome do cliente' });
    const tel = entrada('telefone', { valor: lead.telefone, placeholder: 'Telefone do cliente' });
    lado.append(nome, tel, botao('Salvar dados do cliente', 'btn-sm', () => salvar(lead, { nome: nome.value.trim(), telefone: tel.value.trim() }, 'Dados salvos.').then(recarregar)));
  }
  lado.appendChild(botao('Excluir lead', 'btn-sm btn-ghost btn-perigo', async () => {
    if (!confirm('Excluir este lead? Use quando o cliente pedir a exclusão dos dados (LGPD).')) return;
    try { await api(`/api/leads/${lead.id}`, { method: 'DELETE' }); avisar('Lead excluído.'); recarregar(); } catch (e) { avisar(e.message, 'erro'); }
  }));
  c.append(principal, lado);
  return c;
}

export async function render(pagina) {
  const recarregar = () => window.dispatchEvent(new HashChangeEvent('hashchange'));
  pagina.appendChild(cabecalho('Leads', 'Cada contato chega com o imóvel, o que a pessoa procura e um código. Quem chama no WhatsApp manda o código na mensagem — busque por ele aqui e acompanhe até fechar.',
    botao('Exportar para Excel', '', async () => {
      try { baixar(await api('/api/leads/exportar.csv'), `leads-${new Date().toISOString().slice(0, 10)}.csv`); } catch (e) { avisar(e.message, 'erro'); }
    })));

  const filtros = el('div', 'filtros');
  const busca = entrada('q', { valor: filtro.q, placeholder: 'Buscar por código (ex.: K7Q2XA), nome ou telefone' });
  const origem = selecao('origem', [['', 'WhatsApp e formulário'], ['whatsapp', 'Só WhatsApp'], ['formulario', 'Só formulário']], filtro.origem);
  filtros.append(busca, origem);
  const chips = el('div', 'chips');
  for (const [v, rotulo] of [['', 'Todos'], ...Object.entries(STATUS)]) {
    const b = botao(rotulo, filtro.status === v ? 'ativo' : '', () => { filtro.status = v; recarregar(); });
    chips.appendChild(b);
  }
  pagina.append(filtros, chips);

  const q = new URLSearchParams();
  if (filtro.status) q.set('status_lead', filtro.status);
  if (filtro.origem) q.set('origem', filtro.origem);
  if (filtro.q) q.set('q', filtro.q);
  const leads = await api(`/api/leads?${q}`);
  const lista = el('div', 'lista-leads');
  if (!leads.length) {
    lista.appendChild(vazio(filtro.status || filtro.q || filtro.origem ? 'Nada com esse filtro' : 'Nenhum lead ainda',
      'Quando um visitante tocar em WhatsApp ou deixar o contato no widget, ele aparece aqui.'));
  }
  for (const lead of leads) lista.appendChild(cartao(lead, recarregar));
  pagina.appendChild(lista);

  let espera = null;
  busca.addEventListener('input', () => { clearTimeout(espera); espera = setTimeout(() => { filtro.q = busca.value.trim(); recarregar(); }, 450); });
  origem.addEventListener('change', () => { filtro.origem = origem.value; recarregar(); });
  if (filtro.q) { busca.focus(); busca.setSelectionRange(busca.value.length, busca.value.length); }
}
