import { STATUS, espelho2D, legenda } from '../../comum/espelho.js';
import { el, reais } from '../../comum/util.js';
import {
  abrirModal, api, avisar, aviso_bloqueado, botao, cabecalho, campo, entrada, enviarArquivo, estado, selecao, temRecurso, vazio,
} from '../nucleo.js';

function linhaTorre(torre = { nome: 'Torre A', andares: 8, unidades_por_andar: 4 }) {
  const l = el('div', 'grade');
  l.append(campo('Torre', entrada('t_nome', { valor: torre.nome, required: '', maxlength: 60 })),
    campo('Andares', entrada('t_andares', { type: 'number', min: 1, max: 80, valor: torre.andares, required: '' })),
    campo('Unidades por andar', entrada('t_unidades', { type: 'number', min: 1, max: 30, valor: torre.unidades_por_andar, required: '' })));
  return l;
}

function abrirCadastro(emp, recarregar) {
  const { conteudo, rodape, fechar } = abrirModal(emp ? 'Editar lançamento' : 'Novo lançamento');
  const f = el('form', 'pilha');
  const g = el('div', 'grade');
  const add = (r, n, cls) => { const c = campo(r, n); if (cls) c.classList.add(cls); g.appendChild(c); };
  add('Nome do empreendimento', entrada('nome', { valor: emp && emp.nome, required: '', minlength: 2 }), 'largo');
  add('Bairro', entrada('bairro', { valor: emp && emp.bairro, required: '' }), 'meio');
  add('Cidade', entrada('cidade', { valor: (emp && emp.cidade) || 'Nova Friburgo', required: '' }));
  add('Previsão de entrega', entrada('previsao_entrega', { valor: emp && emp.previsao_entrega, placeholder: 'Ex.: Dez/2027' }));
  add('Descrição', entrada('descricao', { tag: 'textarea', rows: 3, valor: emp ? emp.descricao : '' }), 'largo');
  f.appendChild(g);
  const torres = el('div', 'pilha');
  for (const t of (emp ? emp.torres : [undefined])) torres.appendChild(linhaTorre(t));
  f.append(el('strong', '', 'Torres'), torres, botao('+ Torre', 'btn-sm', () => torres.appendChild(linhaTorre({ nome: `Torre ${String.fromCharCode(65 + torres.children.length)}`, andares: 8, unidades_por_andar: 4 }))),
    el('p', 'ajuda', 'As unidades são criadas automaticamente (101, 102… 801, 802…). Diminuir a torre remove as unidades que sobram; as outras mantêm status e preço.'));
  conteudo.appendChild(f);
  rodape.append(botao('Cancelar', 'btn-ghost', fechar), botao('Salvar', 'btn-solid', async () => {
    if (!f.reportValidity()) return;
    const v = (n) => f.elements[n].value.trim();
    const dados = {
      nome: v('nome'), bairro: v('bairro'), cidade: v('cidade'), previsao_entrega: v('previsao_entrega') || null,
      descricao: v('descricao'), fotos: emp ? emp.fotos : [], ativo: emp ? emp.ativo : true,
      torres: [...torres.children].map((l) => ({
        nome: l.querySelector('[name=t_nome]').value.trim(), andares: Number(l.querySelector('[name=t_andares]').value),
        unidades_por_andar: Number(l.querySelector('[name=t_unidades]').value),
      })),
    };
    try {
      if (emp) await api(`/api/lancamentos/${emp.id}`, { method: 'PUT', json: dados });
      else await api('/api/lancamentos', { method: 'POST', json: dados });
      fechar(); avisar('Lançamento salvo.'); recarregar();
    } catch (e) { avisar(e.message, 'erro'); }
  }));
}

function editorEspelho(emp, recarregar) {
  const caixa = el('div', 'cartao bloco');
  const cab = el('div', 'cab-acoes');
  const titulo = el('div');
  titulo.append(el('h2', '', emp.nome), el('p', 'ajuda', `${emp.bairro}, ${emp.cidade}${emp.previsao_entrega ? ` · entrega ${emp.previsao_entrega}` : ''}`));
  const csv = el('input');
  csv.type = 'file'; csv.accept = '.csv,text/csv'; csv.hidden = true;
  csv.addEventListener('change', async () => {
    if (!csv.files[0]) return;
    try { await enviarArquivo(`/api/lancamentos/${emp.id}/unidades/importar`, csv.files[0]); avisar('Unidades atualizadas pela planilha.'); recarregar(); }
    catch (e) { avisar(e.message, 'erro'); }
  });
  const previa = el('a', 'btn btn-sm', 'Ver como o cliente vê');
  previa.href = `embed.html?k=${encodeURIComponent(estado.sessao.imobiliaria.chave_publica)}&abrir=lancamentos`;
  previa.target = '_blank';
  const acoes = el('div', 'acoes');
  acoes.append(previa, botao('Editar dados e torres', 'btn-sm', () => abrirCadastro(emp, recarregar)),
    botao('Importar planilha', 'btn-sm', () => csv.click()), csv,
    botao('Excluir', 'btn-sm btn-ghost btn-perigo', async () => {
      if (!confirm(`Excluir “${emp.nome}” e todas as unidades?`)) return;
      await api(`/api/lancamentos/${emp.id}`, { method: 'DELETE' }); recarregar();
    }));
  cab.append(titulo, acoes);
  caixa.append(cab, legenda());

  const selecionadas = new Set();
  const editor = el('div', 'editor-espelho');
  const palco = el('div');
  const lado = el('div', 'pilha');
  editor.append(palco, lado);
  caixa.append(el('p', 'ajuda', 'Clique nas unidades para selecionar (pode selecionar várias) e altere ao lado. Planilha: torre;unidade;status;preco;area_m2;quartos;suites;vagas;tipologia.'), editor);

  const desenhar = () => {
    espelho2D(palco, emp, {
      aoClicar: (u) => { if (selecionadas.has(u.id)) selecionadas.delete(u.id); else selecionadas.add(u.id); desenhar(); },
      marcada: (u) => selecionadas.has(u.id),
    });
    lado.replaceChildren();
    if (!selecionadas.size) { lado.appendChild(el('p', 'ajuda', 'Nenhuma unidade selecionada.')); return; }
    const alvo = emp.unidades.filter((u) => selecionadas.has(u.id));
    const um = alvo.length === 1 ? alvo[0] : {};
    lado.appendChild(el('strong', '', alvo.length === 1 ? `Unidade ${um.codigo} (${um.torre})` : `${alvo.length} unidades selecionadas`));
    const status = selecao('status', [['', '— manter —'], ...Object.entries(STATUS).map(([k, s]) => [k, s.rotulo])], um.status || '');
    const preco = entrada('preco', { type: 'number', min: 1, valor: um.preco, placeholder: 'manter' });
    const area = entrada('area', { type: 'number', min: 1, step: 0.1, valor: um.area_m2, placeholder: 'manter' });
    const quartos = entrada('quartos', { type: 'number', min: 0, valor: um.quartos, placeholder: 'manter' });
    const tipologia = entrada('tipologia', { valor: um.tipologia, placeholder: 'Ex.: 2 quartos com varanda' });
    lado.append(campo('Status', status), campo('Preço (R$)', preco), campo('Área (m²)', area), campo('Quartos', quartos), campo('Tipologia', tipologia));
    lado.append(botao('Aplicar', 'btn-solid btn-sm', async () => {
      const mudancas = {};
      if (status.value) mudancas.status = status.value;
      if (preco.value) mudancas.preco = Number(preco.value);
      if (area.value) mudancas.area_m2 = Number(area.value);
      if (quartos.value) mudancas.quartos = Number(quartos.value);
      if (tipologia.value.trim()) mudancas.tipologia = tipologia.value.trim();
      try {
        const novo = await api(`/api/lancamentos/${emp.id}/unidades`, { method: 'PUT', json: alvo.map((u) => ({ id: u.id, ...mudancas })) });
        emp.unidades = novo.unidades;
        selecionadas.clear();
        avisar('Unidades atualizadas.');
        desenhar();
      } catch (e) { avisar(e.message, 'erro'); }
    }), botao('Limpar seleção', 'btn-sm btn-ghost', () => { selecionadas.clear(); desenhar(); }));
    if (alvo.length === 1 && um.preco) lado.appendChild(el('p', 'ajuda', `Preço atual: ${reais(um.preco)}`));
  };
  desenhar();
  return caixa;
}

export async function render(pagina) {
  const recarregar = () => window.dispatchEvent(new HashChangeEvent('hashchange'));
  const pode = temRecurso('lancamentos');
  pagina.appendChild(cabecalho('Lançamentos', 'Espelho de vendas com prédio em 3D: o cliente vê as unidades disponíveis, reservadas e vendidas e chama o corretor na unidade que quer.',
    ...(pode ? [botao('+ Novo lançamento', 'btn-solid', () => abrirCadastro(null, recarregar))] : [])));
  if (!pode) { pagina.appendChild(aviso_bloqueado('O espelho 3D de lançamentos faz parte do plano Premium.')); return; }
  const lista = await api('/api/lancamentos');
  if (!lista.length) {
    pagina.appendChild(vazio('Nenhum lançamento', 'Cadastre o empreendimento e as torres; as unidades são criadas sozinhas.',
      botao('+ Novo lançamento', 'btn-solid', () => abrirCadastro(null, recarregar))));
    return;
  }
  for (const emp of lista) pagina.appendChild(editorEspelho(emp, recarregar));
}
