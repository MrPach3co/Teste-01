// Painel da imobiliária. JavaScript puro, sem build. Texto vindo da API é
// sempre inserido com textContent (função el) — nunca innerHTML.
(function () {
  'use strict';

  const token = localStorage.getItem('kp_token');
  if (!token) { location.replace('entrar.html'); return; }

  const $ = (id) => document.getElementById(id);
  const estado = { sessao: null, vocabulario: null, imoveis: [], filtroStatus: '' };

  const STATUS = {
    novo: 'Novo', em_contato: 'Em contato', visita: 'Visita marcada',
    proposta: 'Proposta', fechado: 'Fechado', perdido: 'Perdido',
  };

  // ---------- utilitários ----------

  function el(tag, classe, texto) {
    const n = document.createElement(tag);
    if (classe) n.className = classe;
    if (texto !== undefined && texto !== null) n.textContent = texto;
    return n;
  }

  const reais = (v) => v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 });
  const numero = (v) => (v === null || v === undefined ? '∞' : v.toLocaleString('pt-BR'));
  const dataCurta = (iso) => new Date(iso + (iso.endsWith('Z') ? '' : 'Z')).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
  const ehDono = () => estado.sessao && estado.sessao.usuario.papel === 'dono';

  function sair() {
    localStorage.removeItem('kp_token');
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

  async function api(caminho, opcoes = {}) {
    const headers = { Authorization: `Bearer ${token}`, ...(opcoes.headers || {}) };
    if (opcoes.json !== undefined) {
      headers['Content-Type'] = 'application/json';
      opcoes.body = JSON.stringify(opcoes.json);
    }
    const r = await fetch(caminho, { ...opcoes, headers });
    if (r.status === 401) { sair(); throw new Error('Sessão expirada.'); }
    if (r.status === 204) return null;
    const tipo = r.headers.get('content-type') || '';
    const dados = tipo.includes('json') ? await r.json() : await r.blob();
    if (!r.ok) throw new Error(erroDaApi(dados));
    return dados;
  }

  function avisar(texto, tipo = 'ok') {
    const a = $('aviso-global');
    a.className = `aviso aviso-${tipo}`;
    a.textContent = texto;
    a.hidden = false;
    clearTimeout(avisar.t);
    avisar.t = setTimeout(() => { a.hidden = true; }, 5000);
  }

  function baixar(blob, nome) {
    const url = URL.createObjectURL(blob);
    const a = el('a');
    a.href = url; a.download = nome;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  function vazio(titulo, texto, botao) {
    const v = el('div', 'cartao vazio');
    v.append(el('strong', '', titulo), el('span', '', texto));
    if (botao) v.appendChild(botao);
    return v;
  }

  const GRADIENTES = [['#2E5741', '#9DB8A4'], ['#9C4A26', '#E2B59A'], ['#3B4A5E', '#A9B8C9'], ['#6B5B3E', '#D9C9A3']];
  function fundoImovel(imovel) {
    if (imovel.foto_url) return `url("${encodeURI(imovel.foto_url)}")`;
    const [a, b] = GRADIENTES[imovel.id % GRADIENTES.length];
    return `linear-gradient(135deg, ${a}, ${b})`;
  }

  // ---------- roteamento ----------

  const PAGINAS = { inicio: carregarInicio, imoveis: carregarImoveis, leads: carregarLeads, widget: carregarWidget, equipe: carregarEquipe, plano: carregarPlano, conta: () => {} };

  function navegar() {
    const [nome, query] = location.hash.slice(1).split('?');
    const pagina = PAGINAS[nome] ? nome : 'inicio';
    document.querySelectorAll('[data-pagina]').forEach((s) => { s.hidden = s.dataset.pagina !== pagina; });
    document.querySelectorAll('.menu a').forEach((a) => a.classList.toggle('ativo', a.dataset.secao === pagina));
    if (query && query.includes('pagamento=ok')) {
      avisar('Pagamento recebido! Seu plano é atualizado em instantes, assim que o Stripe confirmar.');
    }
    PAGINAS[pagina]().catch((e) => avisar(e.message, 'erro'));
  }

  // ---------- visão geral ----------

  function kpi(rotulo, valor, detalhe, uso) {
    const c = el('div', 'cartao kpi');
    c.append(el('span', 'kpi-rotulo', rotulo), el('span', 'kpi-valor', valor));
    if (detalhe) c.appendChild(el('span', 'kpi-detalhe', detalhe));
    if (uso !== undefined) {
      const m = el('div', 'medidor' + (uso >= 0.85 ? ' alerta' : ''));
      m.setAttribute('role', 'meter');
      m.setAttribute('aria-valuenow', Math.round(uso * 100));
      m.setAttribute('aria-valuemin', '0');
      m.setAttribute('aria-valuemax', '100');
      m.setAttribute('aria-label', rotulo);
      const i = el('i');
      i.style.width = `${Math.min(100, uso * 100)}%`;
      m.appendChild(i);
      c.appendChild(m);
    }
    return c;
  }

  // Gráfico de barras diárias, uma série por gráfico (buscas e leads têm
  // escalas muito diferentes — nunca no mesmo eixo).
  function graficoBarras(alvo, serie, campo, cor, rotulo) {
    const NS = 'http://www.w3.org/2000/svg';
    const L = 600, A = 130, base = A - 1, topo = 6;
    const max = Math.max(1, ...serie.map((d) => d[campo]));
    const passo = L / serie.length;
    const largura = Math.max(2, passo - 2); // 2px de respiro entre barras

    const svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('viewBox', `0 0 ${L} ${A}`);
    svg.setAttribute('preserveAspectRatio', 'none');
    svg.setAttribute('role', 'img');
    const total = serie.reduce((s, d) => s + d[campo], 0);
    svg.setAttribute('aria-label', `${rotulo}: ${total} nos últimos 30 dias, máximo de ${max} em um dia.`);

    const linhaBase = document.createElementNS(NS, 'line');
    linhaBase.setAttribute('x1', 0); linhaBase.setAttribute('x2', L);
    linhaBase.setAttribute('y1', base); linhaBase.setAttribute('y2', base);
    linhaBase.setAttribute('class', 'grade-linha');
    svg.appendChild(linhaBase);

    const dica = $('dica');
    serie.forEach((d, i) => {
      const h = d[campo] ? Math.max(3, ((base - topo) * d[campo]) / max) : 0;
      const x = i * passo + 1;
      const r = Math.min(4, largura / 2, h);
      if (h) {
        // Topo arredondado de 4px, base reta apoiada no eixo.
        const p = document.createElementNS(NS, 'path');
        p.setAttribute('d', `M${x},${base} V${base - h + r} Q${x},${base - h} ${x + r},${base - h} H${x + largura - r} Q${x + largura},${base - h} ${x + largura},${base - h + r} V${base} Z`);
        p.setAttribute('fill', cor);
        p.setAttribute('class', 'barra');
        p.dataset.i = i;
        svg.appendChild(p);
      }
      const alvoHover = document.createElementNS(NS, 'rect');
      alvoHover.setAttribute('x', i * passo); alvoHover.setAttribute('y', 0);
      alvoHover.setAttribute('width', passo); alvoHover.setAttribute('height', A);
      alvoHover.setAttribute('class', 'alvo');
      alvoHover.addEventListener('mousemove', (e) => {
        const [, mes, dia] = d.dia.split('-');
        dica.textContent = `${dia}/${mes} · ${d[campo]} ${rotulo.toLowerCase()}`;
        dica.hidden = false;
        dica.style.left = `${e.clientX + 12}px`;
        dica.style.top = `${e.clientY - 34}px`;
        svg.querySelectorAll('.barra').forEach((b) => b.classList.toggle('foco', b.dataset.i === String(i)));
      });
      alvoHover.addEventListener('mouseleave', () => {
        dica.hidden = true;
        svg.querySelectorAll('.barra.foco').forEach((b) => b.classList.remove('foco'));
      });
      svg.appendChild(alvoHover);
    });

    // Rótulos do eixo em HTML: o SVG estica na horizontal e distorceria texto.
    const eixo = el('div', 'grafico-eixo');
    [serie[0].dia, serie.at(-1).dia].forEach((dia) => {
      const [, mes, d] = dia.split('-');
      eixo.appendChild(el('span', '', `${d}/${mes}`));
    });

    alvo.replaceChildren(svg, eixo);
  }

  async function carregarInicio() {
    const m = await api('/api/painel/metricas');
    const p = m.plano;
    const usoBuscas = p.limite_buscas_mes ? m.buscas_mes / p.limite_buscas_mes : undefined;

    $('kpis').replaceChildren(
      kpi('Buscas no mês', numero(m.buscas_mes), p.limite_buscas_mes ? `de ${numero(p.limite_buscas_mes)} do plano ${p.nome}` : 'sem limite', usoBuscas),
      kpi('Leads no mês', numero(m.leads_mes), `${m.leads_novos} aguardando primeiro contato`),
      kpi('Conversão', `${m.conversao_mes.toLocaleString('pt-BR')}%`, 'buscas que viraram lead'),
      kpi('Imóveis ativos', numero(m.imoveis_ativos), p.limite_imoveis ? `${m.imoveis_total} de ${p.limite_imoveis} cadastrados` : `${m.imoveis_total} cadastrados`,
        p.limite_imoveis ? m.imoveis_total / p.limite_imoveis : undefined),
    );

    graficoBarras($('grafico-buscas'), m.serie, 'buscas', getComputedStyle(document.documentElement).getPropertyValue('--serie-buscas').trim(), 'Buscas');
    graficoBarras($('grafico-leads'), m.serie, 'leads', getComputedStyle(document.documentElement).getPropertyValue('--serie-leads').trim(), 'Leads');

    const termos = $('termos');
    termos.replaceChildren();
    if (!m.termos_populares.length) termos.appendChild(el('p', 'ajuda', 'Assim que as buscas começarem, os termos mais usados aparecem aqui.'));
    m.termos_populares.forEach((t) => {
      const s = el('span', '', t.termo);
      s.appendChild(el('b', '', t.total));
      termos.appendChild(s);
    });

    const recentes = $('recentes');
    recentes.replaceChildren();
    if (!m.buscas_recentes.length) recentes.appendChild(el('li', 'ajuda', 'Nenhuma busca ainda. Instale o widget no seu site na aba "Widget no site".'));
    m.buscas_recentes.forEach((t) => recentes.appendChild(el('li', '', `"${t}"`)));

    atualizarContadorLeads(m.leads_novos);
  }

  function atualizarContadorLeads(n) {
    const c = $('contador-leads');
    c.textContent = n;
    c.hidden = !n;
  }

  // ---------- imóveis ----------

  async function garantirVocabulario() {
    if (estado.vocabulario) return;
    estado.vocabulario = await api('/api/imoveis/vocabulario');
    const select = $('form-imovel').elements.tipo;
    Object.entries(estado.vocabulario.tipos).forEach(([v, rotulo]) => {
      const o = el('option', '', rotulo); o.value = v; select.appendChild(o);
    });
    const caixa = $('caixa-caracteristicas');
    Object.entries(estado.vocabulario.caracteristicas).forEach(([slug, rotulo]) => {
      const l = el('label');
      const c = el('input'); c.type = 'checkbox'; c.name = 'caracteristicas'; c.value = slug;
      l.append(c, el('span', '', rotulo));
      caixa.appendChild(l);
    });
  }

  async function carregarImoveis() {
    await garantirVocabulario();
    estado.imoveis = await api('/api/imoveis');
    desenharImoveis();
  }

  function desenharImoveis() {
    const termo = $('filtro-imoveis').value.trim().toLowerCase();
    const lista = $('lista-imoveis');
    const ativos = estado.imoveis.filter((i) => i.ativo).length;
    $('resumo-imoveis').textContent = `${estado.imoveis.length} cadastrados · ${ativos} disponíveis nas buscas`;

    const datalist = $('bairros-conhecidos');
    datalist.replaceChildren(...[...new Set(estado.imoveis.map((i) => i.bairro))].map((b) => { const o = el('option'); o.value = b; return o; }));

    if (!estado.imoveis.length) {
      const b = el('button', 'btn btn-solid', '+ Cadastrar primeiro imóvel');
      b.type = 'button';
      b.addEventListener('click', () => abrirImovel(null));
      lista.replaceChildren(vazio('Nenhum imóvel ainda', 'Cadastre um a um ou importe sua planilha — a busca do site usa exatamente estes imóveis.', b));
      return;
    }

    const filtrados = estado.imoveis.filter((i) =>
      !termo || [i.titulo, i.bairro, i.cidade, i.codigo_referencia || ''].some((t) => t.toLowerCase().includes(termo)));

    lista.replaceChildren(...filtrados.map((i) => {
      const c = el('article', 'cartao linha-imovel' + (i.ativo ? '' : ' pausado'));
      const mini = el('div', 'miniatura');
      mini.style.backgroundImage = fundoImovel(i);

      const info = el('div');
      const h = el('h3', '', i.titulo);
      if (!i.ativo) h.appendChild(el('span', 'etiqueta', 'pausado'));
      if (i.codigo_referencia) h.appendChild(el('span', 'etiqueta', i.codigo_referencia));
      const tipo = estado.vocabulario.tipos[i.tipo] || i.tipo;
      info.append(h, el('div', 'meta', `${tipo} · ${i.bairro}, ${i.cidade} · ${i.quartos} qts · ${i.area_m2} m² · ${i.total_leads} lead${i.total_leads === 1 ? '' : 's'}`));

      const preco = el('div', 'preco', reais(i.preco));
      preco.appendChild(el('small', '', i.finalidade === 'aluguel' ? 'aluguel/mês' : 'venda'));

      const acoes = el('div', 'acoes');
      const editar = el('button', 'btn btn-sm', 'Editar'); editar.type = 'button';
      editar.addEventListener('click', () => abrirImovel(i));
      const excluir = el('button', 'btn btn-sm btn-ghost btn-perigo', 'Excluir'); excluir.type = 'button';
      excluir.addEventListener('click', async () => {
        if (!confirm(`Excluir "${i.titulo}"? Isso não pode ser desfeito.`)) return;
        try { await api(`/api/imoveis/${i.id}`, { method: 'DELETE' }); avisar('Imóvel excluído.'); carregarImoveis(); }
        catch (e) { avisar(e.message, 'erro'); }
      });
      acoes.append(editar, excluir);

      c.append(mini, info, preco, acoes);
      return c;
    }));
    if (!filtrados.length) lista.appendChild(el('p', 'ajuda', 'Nenhum imóvel com esse filtro.'));
  }

  let imovelEditando = null;

  function abrirImovel(imovel) {
    imovelEditando = imovel;
    const f = $('form-imovel');
    f.reset();
    $('erro-imovel').hidden = true;
    $('titulo-modal-imovel').textContent = imovel ? 'Editar imóvel' : 'Novo imóvel';
    if (imovel) {
      ['titulo', 'tipo', 'finalidade', 'preco', 'codigo_referencia', 'bairro', 'cidade', 'quartos', 'banheiros', 'vagas', 'area_m2', 'foto_url', 'descricao']
        .forEach((campo) => { f.elements[campo].value = imovel[campo] ?? ''; });
      f.elements.ativo.checked = imovel.ativo;
      f.querySelectorAll('[name=caracteristicas]').forEach((c) => { c.checked = imovel.caracteristicas.includes(c.value); });
    } else if (estado.imoveis.length) {
      f.elements.cidade.value = estado.imoveis[0].cidade;
    }
    $('modal-imovel').showModal();
  }

  function dadosDoFormImovel() {
    const f = $('form-imovel').elements;
    return {
      titulo: f.titulo.value.trim(),
      tipo: f.tipo.value,
      finalidade: f.finalidade.value,
      preco: Number(f.preco.value),
      codigo_referencia: f.codigo_referencia.value.trim() || null,
      bairro: f.bairro.value.trim(),
      cidade: f.cidade.value.trim(),
      quartos: Number(f.quartos.value || 0),
      banheiros: Number(f.banheiros.value || 0),
      vagas: Number(f.vagas.value || 0),
      area_m2: Number(f.area_m2.value || 0),
      foto_url: f.foto_url.value.trim() || null,
      descricao: f.descricao.value.trim(),
      caracteristicas: [...$('form-imovel').querySelectorAll('[name=caracteristicas]:checked')].map((c) => c.value),
      ativo: f.ativo.checked,
    };
  }

  $('form-imovel').addEventListener('submit', async (e) => {
    if (e.submitter && e.submitter.value === 'cancelar') return;
    e.preventDefault();
    const erro = $('erro-imovel');
    erro.hidden = true;
    try {
      const dados = dadosDoFormImovel();
      if (imovelEditando) await api(`/api/imoveis/${imovelEditando.id}`, { method: 'PUT', json: dados });
      else await api('/api/imoveis', { method: 'POST', json: dados });
      $('modal-imovel').close();
      avisar(imovelEditando ? 'Imóvel atualizado.' : 'Imóvel cadastrado — já aparece nas buscas do seu site.');
      carregarImoveis();
    } catch (err) {
      erro.textContent = err.message;
      erro.hidden = false;
    }
  });

  $('btn-gerar-descricao').addEventListener('click', async (e) => {
    const botao = e.currentTarget;
    const dados = dadosDoFormImovel();
    if (!dados.bairro || !dados.tipo) { avisar('Preencha pelo menos tipo e bairro antes de gerar a descrição.', 'info'); return; }
    const textoOriginal = botao.textContent;
    botao.disabled = true;
    botao.textContent = 'Escrevendo…';
    try {
      const r = await api('/api/imoveis/gerar-descricao', { method: 'POST', json: { ...dados, observacoes: dados.descricao } });
      $('form-imovel').elements.descricao.value = r.descricao;
    } catch (err) {
      $('erro-imovel').textContent = err.message;
      $('erro-imovel').hidden = false;
    } finally {
      botao.disabled = false;
      botao.textContent = textoOriginal;
    }
  });

  $('btn-novo-imovel').addEventListener('click', () => abrirImovel(null));
  $('filtro-imoveis').addEventListener('input', desenharImoveis);

  $('btn-importar').addEventListener('click', () => {
    $('form-importar').reset();
    $('resultado-importacao').hidden = true;
    $('modal-importar').showModal();
  });

  $('btn-modelo-csv').addEventListener('click', () => {
    const csv = 'titulo;tipo;finalidade;bairro;cidade;preco;quartos;banheiros;vagas;area_m2;caracteristicas;descricao;foto_url;codigo_referencia\n'
      + 'Apartamento com varanda;apartamento;venda;Centro;São Paulo;650000;2;1;1;68;varanda|elevador|portaria-24h;;;AP-001\n'
      + 'Casa com quintal;casa;aluguel;Jardim América;São Paulo;4500;3;2;2;150;jardim|churrasqueira|pet-friendly;;;CA-002\n';
    baixar(new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' }), 'modelo-imoveis-kaza-pro.csv');
  });

  $('form-importar').addEventListener('submit', async (e) => {
    if (e.submitter && e.submitter.value === 'cancelar') return;
    e.preventDefault();
    const arquivo = e.target.elements.arquivo.files[0];
    if (!arquivo) return;
    const corpo = new FormData();
    corpo.append('arquivo', arquivo);
    const saida = $('resultado-importacao');
    try {
      const r = await api('/api/imoveis/importar', { method: 'POST', body: corpo });
      saida.className = 'aviso ' + (r.erros.length ? 'aviso-info' : 'aviso-ok');
      saida.replaceChildren(el('div', '', `${r.importados} imóve${r.importados === 1 ? 'l importado' : 'is importados'}.`));
      r.erros.forEach((t) => saida.appendChild(el('div', '', t)));
      carregarImoveis();
    } catch (err) {
      saida.className = 'aviso aviso-erro';
      saida.textContent = err.message;
    }
    saida.hidden = false;
  });

  // ---------- leads ----------

  function desenharFiltroStatus() {
    const caixa = $('filtro-status');
    caixa.replaceChildren(...[['', 'Todos'], ...Object.entries(STATUS)].map(([v, rotulo]) => {
      const b = el('button', estado.filtroStatus === v ? 'ativo' : '', rotulo);
      b.type = 'button';
      b.addEventListener('click', () => { estado.filtroStatus = v; carregarLeads(); });
      return b;
    }));
  }

  async function carregarLeads() {
    desenharFiltroStatus();
    const consulta = estado.filtroStatus ? `?status_lead=${estado.filtroStatus}` : '';
    const leads = await api(`/api/leads${consulta}`);
    const lista = $('lista-leads');

    if (!leads.length) {
      lista.replaceChildren(vazio(
        estado.filtroStatus ? 'Nenhum lead nesta etapa' : 'Nenhum lead ainda',
        estado.filtroStatus ? 'Mude o filtro acima para ver os outros.' : 'Quando um visitante clicar em "Tenho interesse" no seu site, ele aparece aqui.',
      ));
      return;
    }

    lista.replaceChildren(...leads.map((lead) => {
      const c = el('article', 'cartao lead');
      const principal = el('div');
      principal.append(el('h3', '', lead.nome), el('div', 'meta', `Chegou em ${dataCurta(lead.criado_em)}${lead.imovel_titulo ? ' · interessado em ' + lead.imovel_titulo : ''}`));

      const contatos = el('div', 'contatos');
      if (lead.telefone) {
        const wa = el('a', 'btn btn-sm btn-solid', 'WhatsApp');
        const numeroLimpo = lead.telefone.replace(/\D/g, '');
        wa.href = `https://wa.me/${numeroLimpo.length <= 11 ? '55' + numeroLimpo : numeroLimpo}`;
        wa.target = '_blank'; wa.rel = 'noopener';
        const tel = el('a', 'btn btn-sm', lead.telefone);
        tel.href = `tel:${numeroLimpo}`;
        contatos.append(wa, tel);
      }
      if (lead.email) {
        const mail = el('a', 'btn btn-sm', lead.email);
        mail.href = `mailto:${lead.email}`;
        contatos.appendChild(mail);
      }
      principal.appendChild(contatos);

      if (lead.busca_texto) {
        const q = el('div', 'citacao');
        q.append(el('b', '', 'Buscou: '), document.createTextNode(`"${lead.busca_texto}"`));
        principal.appendChild(q);
      }
      if (lead.mensagem) {
        const q = el('div', 'citacao');
        q.append(el('b', '', 'Mensagem: '), document.createTextNode(lead.mensagem));
        principal.appendChild(q);
      }

      const lado = el('div', 'lead-lado');
      const select = el('select');
      select.setAttribute('aria-label', 'Etapa do lead');
      Object.entries(STATUS).forEach(([v, rotulo]) => { const o = el('option', '', rotulo); o.value = v; select.appendChild(o); });
      select.value = lead.status;
      select.addEventListener('change', async () => {
        try { await api(`/api/leads/${lead.id}`, { method: 'PATCH', json: { status: select.value } }); avisar(`${lead.nome}: ${STATUS[select.value]}.`); }
        catch (e) { avisar(e.message, 'erro'); }
      });

      const notas = el('textarea');
      notas.placeholder = 'Anotações (salva ao sair do campo)';
      notas.value = lead.notas;
      notas.maxLength = 5000;
      notas.addEventListener('change', async () => {
        try { await api(`/api/leads/${lead.id}`, { method: 'PATCH', json: { notas: notas.value } }); avisar('Anotação salva.'); }
        catch (e) { avisar(e.message, 'erro'); }
      });

      const excluir = el('button', 'btn btn-sm btn-ghost btn-perigo', 'Excluir lead');
      excluir.type = 'button';
      excluir.addEventListener('click', async () => {
        if (!confirm(`Excluir os dados de ${lead.nome}? Use isto quando o cliente pedir a exclusão (LGPD).`)) return;
        try { await api(`/api/leads/${lead.id}`, { method: 'DELETE' }); avisar('Lead excluído.'); carregarLeads(); }
        catch (e) { avisar(e.message, 'erro'); }
      });

      lado.append(select, notas, excluir);
      c.append(principal, lado);
      return c;
    }));
  }

  $('btn-exportar-leads').addEventListener('click', async () => {
    try { baixar(await api('/api/leads/exportar.csv'), `leads-${new Date().toISOString().slice(0, 10)}.csv`); }
    catch (e) { avisar(e.message, 'erro'); }
  });

  // ---------- widget ----------

  async function carregarWidget() {
    const imob = estado.sessao.imobiliaria;
    const origem = location.origin;
    $('codigo-flutuante').textContent = `<script src="${origem}/widget.js" data-chave="${imob.chave_publica}" async></script>`;
    $('codigo-inline').textContent = `<div id="busca-imoveis"></div>\n<script src="${origem}/widget.js" data-chave="${imob.chave_publica}" data-modo="inline" data-alvo="#busca-imoveis" async></script>`;
    const link = `${origem}/embed.html?k=${encodeURIComponent(imob.chave_publica)}`;
    $('link-direto').textContent = link;
    $('abrir-link').href = link;
    const previa = $('previa');
    if (previa.dataset.src !== link) { previa.src = link; previa.dataset.src = link; }

    const f = $('form-marca').elements;
    f.nome.value = imob.nome;
    f.cor_primaria.value = imob.cor_primaria;
    f.whatsapp.value = imob.whatsapp || '';
  }

  document.querySelectorAll('[data-copiar]').forEach((b) => b.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText($(b.dataset.copiar).textContent);
      const original = b.textContent;
      b.textContent = 'Copiado ✓';
      setTimeout(() => { b.textContent = original; }, 1600);
    } catch {
      avisar('Não foi possível copiar automaticamente — selecione o texto e copie.', 'info');
    }
  }));

  async function recarregarSessao() {
    estado.sessao = await api('/api/auth/sessao');
    desenharSessao();
  }

  $('form-marca').addEventListener('submit', async (e) => {
    e.preventDefault();
    const f = e.target.elements;
    try {
      await api('/api/imobiliaria', { method: 'PATCH', json: { nome: f.nome.value.trim(), cor_primaria: f.cor_primaria.value, whatsapp: f.whatsapp.value.trim() } });
      await recarregarSessao();
      $('previa').dataset.src = '';
      carregarWidget();
      avisar('Aparência salva.');
    } catch (err) { avisar(err.message, 'erro'); }
  });

  $('btn-regenerar').addEventListener('click', async () => {
    if (!confirm('Gerar uma nova chave? O código instalado no seu site vai parar de funcionar até você trocar pelo novo.')) return;
    try { await api('/api/imobiliaria/regenerar-chave', { method: 'POST' }); await recarregarSessao(); carregarWidget(); avisar('Nova chave gerada. Atualize o código no seu site.'); }
    catch (e) { avisar(e.message, 'erro'); }
  });

  // ---------- equipe ----------

  async function carregarEquipe() {
    const pessoas = await api('/api/equipe');
    $('lista-equipe').replaceChildren(...pessoas.map((p) => {
      const li = el('li');
      const info = el('div', '', p.nome);
      info.appendChild(el('small', '', `${p.email} · ${p.papel === 'dono' ? 'Dono da conta' : 'Corretor'}`));
      li.appendChild(info);
      if (ehDono() && p.papel !== 'dono') {
        const remover = el('button', 'btn btn-sm btn-ghost btn-perigo', 'Remover');
        remover.type = 'button';
        remover.addEventListener('click', async () => {
          if (!confirm(`Remover ${p.nome} da equipe?`)) return;
          try { await api(`/api/equipe/${p.id}`, { method: 'DELETE' }); carregarEquipe(); }
          catch (e) { avisar(e.message, 'erro'); }
        });
        li.appendChild(remover);
      }
      return li;
    }));
  }

  $('form-equipe').addEventListener('submit', async (e) => {
    e.preventDefault();
    const f = e.target;
    const [erro, ok] = f.querySelectorAll('.aviso');
    erro.hidden = ok.hidden = true;
    try {
      const r = await api('/api/equipe', { method: 'POST', json: { nome: f.elements.nome.value.trim(), email: f.elements.email.value.trim() } });
      ok.replaceChildren(
        document.createTextNode(`${r.usuario.nome} foi adicionado. Envie a senha temporária para ele: `),
        el('span', 'senha-temp', r.senha_temporaria),
        document.createTextNode(' — ela não será mostrada de novo. Peça para trocar em "Minha conta".'),
      );
      ok.hidden = false;
      f.reset();
      carregarEquipe();
    } catch (err) {
      erro.textContent = err.message;
      erro.hidden = false;
    }
  });

  // ---------- plano ----------

  async function carregarPlano() {
    const [catalogo, m] = await Promise.all([api('/api/assinatura/planos'), api('/api/painel/metricas')]);
    const atual = estado.sessao.imobiliaria.plano;
    const planoAtual = catalogo.planos.find((p) => p.id === atual);
    $('plano-atual').textContent = `Você está no plano ${planoAtual.nome}.`;

    $('uso').replaceChildren(
      kpi('Buscas neste mês', `${numero(m.buscas_mes)} / ${numero(planoAtual.limite_buscas_mes)}`, null,
        planoAtual.limite_buscas_mes ? m.buscas_mes / planoAtual.limite_buscas_mes : undefined),
      kpi('Imóveis', `${numero(m.imoveis_total)} / ${numero(planoAtual.limite_imoveis)}`, null,
        planoAtual.limite_imoveis ? m.imoveis_total / planoAtual.limite_imoveis : undefined),
      kpi('Usuários', `${m.usuarios_total} / ${planoAtual.limite_usuarios}`, null, m.usuarios_total / planoAtual.limite_usuarios),
    );

    $('lista-planos').replaceChildren(...catalogo.planos.map((p) => {
      const c = el('article', 'cartao plano' + (p.id === atual ? ' atual' : ''));
      const valor = el('div', 'valor', p.preco_mensal ? `R$ ${p.preco_mensal}` : 'Grátis');
      if (p.preco_mensal) valor.appendChild(el('small', '', ' /mês'));
      const itens = el('ul');
      [`${numero(p.limite_imoveis)} imóveis`, `${numero(p.limite_buscas_mes)} buscas/mês`, `${p.limite_usuarios} usuário(s)`,
        p.marca_kaza_no_widget ? 'Selo Kaza Pro no widget' : 'Widget sem nossa marca'].forEach((t) => itens.appendChild(el('li', '', t)));
      c.append(el('h3', '', p.nome), el('p', 'ajuda', p.destaque), valor, itens);

      if (p.id === atual) {
        c.appendChild(el('span', 'selo', 'SEU PLANO ATUAL'));
      } else if (p.preco_mensal && catalogo.pagamento_online && ehDono()) {
        const b = el('button', 'btn btn-solid', `Assinar ${p.nome}`);
        b.type = 'button';
        b.addEventListener('click', async () => {
          b.disabled = true;
          try { location.href = (await api(`/api/assinatura/checkout?plano=${p.id}`, { method: 'POST' })).url; }
          catch (e) { avisar(e.message, 'erro'); b.disabled = false; }
        });
        c.appendChild(b);
      }
      return c;
    }));

    $('sem-pagamento').hidden = catalogo.pagamento_online;
    $('area-portal').hidden = !(catalogo.pagamento_online && atual !== 'gratis' && ehDono());
  }

  $('btn-portal').addEventListener('click', async () => {
    try { location.href = (await api('/api/assinatura/portal', { method: 'POST' })).url; }
    catch (e) { avisar(e.message, 'erro'); }
  });

  // ---------- conta ----------

  $('form-senha').addEventListener('submit', async (e) => {
    e.preventDefault();
    const f = e.target;
    const erro = f.querySelector('.aviso-erro');
    erro.hidden = true;
    try {
      await api('/api/auth/trocar-senha', { method: 'POST', json: { senha_atual: f.elements.senha_atual.value, nova_senha: f.elements.nova_senha.value } });
      f.reset();
      avisar('Senha alterada.');
    } catch (err) { erro.textContent = err.message; erro.hidden = false; }
  });

  $('btn-meus-dados').addEventListener('click', async () => {
    try {
      const dados = await api('/api/auth/meus-dados');
      baixar(new Blob([JSON.stringify(dados, null, 2)], { type: 'application/json' }), 'meus-dados-kaza-pro.json');
    } catch (e) { avisar(e.message, 'erro'); }
  });

  $('btn-excluir-conta').addEventListener('click', async () => {
    const msg = ehDono()
      ? 'ATENÇÃO: você é o dono. Excluir sua conta apaga a imobiliária inteira — imóveis, leads e equipe. Digite EXCLUIR para confirmar.'
      : 'Excluir sua conta de acesso? Digite EXCLUIR para confirmar.';
    if (prompt(msg) !== 'EXCLUIR') return;
    try { await api('/api/auth/minha-conta', { method: 'DELETE' }); sair(); }
    catch (e) { avisar(e.message, 'erro'); }
  });

  // ---------- inicialização ----------

  function desenharSessao() {
    const { usuario, imobiliaria } = estado.sessao;
    $('nome-imob').textContent = imobiliaria.nome;
    $('nome-usuario').textContent = usuario.nome;
    document.querySelectorAll('[data-dono]').forEach((n) => { n.hidden = !ehDono(); });
    $('aviso-exclusao').textContent = ehDono() ? 'Como dono, excluir a conta apaga a imobiliária inteira.' : '';
  }

  $('sair').addEventListener('click', sair);
  window.addEventListener('hashchange', navegar);

  (async function iniciar() {
    try {
      await recarregarSessao();
    } catch (e) {
      // Se a sessão expirou, api() já redirecionou para o login. Senão, é rede.
      document.body.appendChild(el('p', 'vazio', `Não foi possível abrir o painel: ${e.message} Recarregue a página.`));
      return;
    }
    $('painel').hidden = false;
    navegar();
    if (location.hash.split('?')[0] !== '#inicio') {
      api('/api/painel/metricas').then((m) => atualizarContadorLeads(m.leads_novos)).catch(() => {});
    }
  })();
})();
