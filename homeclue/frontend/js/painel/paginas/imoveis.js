import { el, fundoFoto, reais } from '../../comum/util.js';
import {
  api, avisar, abrirModal, baixar, botao, cabecalho, campo, ehDono, entrada, enviarArquivo, estado,
  garantirVocabulario, selecao, temRecurso, vazio,
} from '../nucleo.js';
import { abrirEditorPlanta } from './planta_editor.js';

let imoveis = [];
let equipe = [];

const FINALIDADES = [['venda', 'Venda'], ['aluguel', 'Aluguel'], ['venda_aluguel', 'Venda e aluguel']];

function numeroOuNulo(v) {
  if (v === '' || v === null || v === undefined) return null;
  const n = Number(String(v).replace(',', '.'));
  return Number.isFinite(n) ? n : null;
}

function linha(imovel, recarregar) {
  const c = el('article', `cartao linha-imovel${imovel.ativo && !imovel.removido_do_feed_em ? '' : ' pausado'}`);
  const mini = el('div', 'miniatura');
  fundoFoto(mini, imovel.foto, imovel.id);
  const info = el('div');
  const titulo = el('h3', '', imovel.titulo);
  titulo.appendChild(el('span', `etiqueta${imovel.origem === 'feed' ? ' etiqueta-feed' : ''}`, imovel.origem === 'feed' ? 'feed XML' : 'manual'));
  if (imovel.codigo_referencia) titulo.appendChild(el('span', 'etiqueta', imovel.codigo_referencia));
  if (imovel.removido_do_feed_em) titulo.appendChild(el('span', 'etiqueta etiqueta-alerta', 'saiu do feed'));
  else if (!imovel.ativo) titulo.appendChild(el('span', 'etiqueta etiqueta-alerta', 'pausado'));
  if (imovel.tem_planta) titulo.appendChild(el('span', 'etiqueta', 'planta/3D'));
  const tipo = estado.vocabulario.tipos[imovel.tipo] || imovel.tipo;
  const partes = [tipo, `${imovel.bairro}, ${imovel.cidade}`, imovel.quartos !== null ? `${imovel.quartos} qts` : null,
    imovel.area_m2 ? `${imovel.area_m2} m²` : null, `${imovel.visualizacoes} aberturas (30 dias)`, `${imovel.total_leads} leads`];
  info.append(titulo, el('div', 'meta', partes.filter(Boolean).join(' · ')));
  const preco = el('div', 'preco', reais(imovel.preco));
  preco.appendChild(el('small', '', { aluguel: 'aluguel/mês', venda_aluguel: 'venda e aluguel', venda: 'venda' }[imovel.finalidade]));
  const acoes = el('div', 'acoes');
  acoes.append(botao('Editar', 'btn-sm', () => abrirEditor(imovel, recarregar)));
  if (imovel.origem === 'manual') {
    acoes.append(botao('Excluir', 'btn-sm btn-ghost btn-perigo', async () => {
      if (!confirm(`Excluir "${imovel.titulo}"? Isso não pode ser desfeito.`)) return;
      try { await api(`/api/imoveis/${imovel.id}`, { method: 'DELETE' }); avisar('Imóvel excluído.'); recarregar(); }
      catch (e) { avisar(e.message, 'erro'); }
    }));
  }
  c.append(mini, info, preco, acoes);
  return c;
}

function dadosDoFormulario(f, fotos) {
  const val = (n) => f.elements[n].value.trim();
  return {
    titulo: val('titulo'), tipo: val('tipo'), finalidade: val('finalidade'), preco: numeroOuNulo(val('preco')),
    preco_aluguel: numeroOuNulo(val('preco_aluguel')), condominio: numeroOuNulo(val('condominio')),
    iptu: numeroOuNulo(val('iptu')), bairro: val('bairro'), cidade: val('cidade'), uf: val('uf') || null,
    endereco: val('endereco') || null, mostrar_endereco: f.elements.mostrar_endereco.checked,
    latitude: numeroOuNulo(val('latitude')), longitude: numeroOuNulo(val('longitude')),
    quartos: numeroOuNulo(val('quartos')), suites: numeroOuNulo(val('suites')), banheiros: numeroOuNulo(val('banheiros')),
    vagas: numeroOuNulo(val('vagas')), area_m2: numeroOuNulo(val('area_m2')), area_terreno: numeroOuNulo(val('area_terreno')),
    descricao: val('descricao'), codigo_referencia: val('codigo_referencia') || null,
    caracteristicas: [...f.querySelectorAll('[name=caracteristicas]:checked')].map((c) => c.value),
    comodidades: val('comodidades').split('\n').map((x) => x.trim()).filter(Boolean),
    fotos, video_url: val('video_url') || null, video_drone_url: val('video_drone_url') || null,
    url_anuncio: val('url_anuncio') || null, corretor_id: numeroOuNulo(val('corretor_id')),
    ativo: f.elements.ativo.checked,
  };
}

function editorDeFotos(fotos, imovelId, somenteLeitura) {
  const caixa = el('div', 'pilha');
  const grade = el('div', 'fotos-editor');
  const desenhar = () => {
    grade.replaceChildren();
    fotos.forEach((f, i) => {
      const item = el('div', 'foto-item');
      const img = el('div', 'img');
      img.style.backgroundImage = `url("${encodeURI(f.url)}")`;
      item.appendChild(img);
      if (!somenteLeitura) {
        const acoes = el('div', 'acoes');
        acoes.append(
          botao('←', 'btn-sm', () => { if (i > 0) { [fotos[i - 1], fotos[i]] = [fotos[i], fotos[i - 1]]; desenhar(); } }),
          botao('Remover', 'btn-sm btn-perigo', () => { fotos.splice(i, 1); desenhar(); }),
        );
        item.appendChild(acoes);
      }
      grade.appendChild(item);
    });
    if (!fotos.length) grade.appendChild(el('p', 'ajuda', 'Nenhuma foto. A primeira foto é a capa.'));
  };
  desenhar();
  caixa.appendChild(grade);
  if (somenteLeitura) {
    caixa.appendChild(el('p', 'ajuda', 'As fotos deste imóvel vêm do feed XML — altere no seu sistema.'));
    return caixa;
  }
  const linhaUrl = el('div', 'acoes');
  const url = entrada('nova_foto', { type: 'url', placeholder: 'https://… (link de uma foto)' });
  url.style.flex = '1';
  linhaUrl.append(url, botao('Adicionar link', 'btn-sm', () => {
    if (!/^https:\/\//.test(url.value.trim())) { avisar('Use um link começando com https://', 'info'); return; }
    fotos.push({ url: url.value.trim(), legenda: '' }); url.value = ''; desenhar();
  }));
  const arquivo = el('input');
  arquivo.type = 'file'; arquivo.accept = 'image/*'; arquivo.multiple = true; arquivo.hidden = true;
  arquivo.addEventListener('change', async () => {
    if (!imovelId) { avisar('Salve o imóvel antes de enviar fotos do computador.', 'info'); return; }
    for (const a of arquivo.files) {
      try { const r = await enviarArquivo(`/api/imoveis/${imovelId}/fotos`, a); fotos.push({ url: r.url, legenda: '' }); desenhar(); }
      catch (e) { avisar(e.message, 'erro'); }
    }
    arquivo.value = '';
  });
  linhaUrl.append(botao('Enviar do computador', 'btn-sm', () => arquivo.click()), arquivo);
  caixa.appendChild(linhaUrl);
  return caixa;
}

function abaContexto(imovel) {
  const caixa = el('div', 'pilha');
  if (!imovel) { caixa.appendChild(el('p', 'ajuda', 'Salve o imóvel primeiro.')); return caixa; }
  const ctx = imovel.contexto;
  caixa.appendChild(el('h3', '', 'Contexto do bairro (OpenStreetMap)'));
  if (ctx && ctx.categorias) {
    const lista = el('ul', 'lista-simples');
    for (const cat of Object.values(ctx.categorias)) {
      const li = el('li');
      li.append(el('span', '', cat.rotulo), el('small', '', cat.mais_proximos.length
        ? cat.mais_proximos.map((p) => `${p.nome} (${p.distancia_m} m)`).join(' · ') : 'nada mapeado por perto'));
      lista.appendChild(li);
    }
    caixa.append(lista, el('p', 'ajuda', ctx.aproximado ? 'Calculado a partir do centro do bairro (o anúncio não tem coordenadas exatas).' : 'Calculado a partir das coordenadas do anúncio.'));
  } else if (ctx && ctx.erro) {
    caixa.appendChild(el('p', 'aviso aviso-info', ctx.erro));
  } else {
    caixa.appendChild(el('p', 'ajuda', 'Ainda não calculado — leva alguns minutos depois de salvar.'));
  }
  caixa.appendChild(botao('Recalcular contexto', 'btn-sm', async () => {
    try { avisar((await api(`/api/imoveis/${imovel.id}/contexto`, { method: 'POST' })).mensagem); } catch (e) { avisar(e.message, 'erro'); }
  }));

  caixa.appendChild(el('h3', '', 'O que a IA viu nas fotos'));
  if (!temRecurso('analise_fotos')) {
    caixa.appendChild(el('p', 'ajuda', 'A análise das fotos faz parte do plano Premium.'));
  } else if (imovel.analise_fotos && imovel.analise_fotos.fotos) {
    const lista = el('ul', 'lista-simples');
    for (const f of imovel.analise_fotos.fotos) {
      const li = el('li');
      li.append(el('span', '', f.descricao), el('small', '', f.caracteristicas.map((c) => estado.vocabulario.caracteristicas[c] || c).join(', ') || '—'));
      lista.appendChild(li);
    }
    caixa.appendChild(lista);
  } else {
    caixa.appendChild(el('p', 'ajuda', estado.sessao.imobiliaria.analisar_fotos
      ? 'Ainda não analisadas.' : 'Desligada. Ative em Widget no site → Inteligência das fotos.'));
  }
  if (temRecurso('analise_fotos') && estado.sessao.imobiliaria.analisar_fotos) {
    caixa.appendChild(botao('Analisar fotos agora', 'btn-sm', async () => {
      try { avisar((await api(`/api/imoveis/${imovel.id}/analisar-fotos`, { method: 'POST' })).mensagem); } catch (e) { avisar(e.message, 'erro'); }
    }));
  }
  return caixa;
}

async function abrirEditor(imovel, recarregar) {
  const v = await garantirVocabulario();
  // A lista traz só o resumo; o formulário precisa do imóvel completo.
  if (imovel) {
    try { imovel = await api(`/api/imoveis/${imovel.id}`); } catch (e) { avisar(e.message, 'erro'); return; }
  }
  const doFeed = imovel && imovel.origem === 'feed';
  const { conteudo, rodape, fechar } = abrirModal(imovel ? 'Editar imóvel' : 'Novo imóvel', { largo: true });
  if (doFeed) conteudo.appendChild(el('p', 'aviso aviso-info', 'Este imóvel vem do feed XML: os dados do anúncio são atualizados pelo seu sistema. Aqui você pode pausar, escolher o corretor responsável, adicionar o vídeo de drone e desenhar a planta.'));

  const abas = el('div', 'abas');
  abas.setAttribute('role', 'tablist');
  const f = el('form', 'pilha');
  f.noValidate = false;
  const paineis = {};
  const nomesAbas = [['anuncio', 'Anúncio'], ['midia', 'Fotos e vídeo'], ['inteligencia', 'Contexto e IA'], ['planta', 'Planta e 3D']];
  for (const [chave, rotulo] of nomesAbas) {
    const b = botao(rotulo, '', () => mostrarAba(chave));
    b.setAttribute('role', 'tab');
    b.dataset.aba = chave;
    abas.appendChild(b);
    paineis[chave] = el('div', 'pilha');
    paineis[chave].setAttribute('role', 'tabpanel');
    f.appendChild(paineis[chave]);
  }
  function mostrarAba(chave) {
    abas.querySelectorAll('button').forEach((b) => b.setAttribute('aria-selected', b.dataset.aba === chave ? 'true' : 'false'));
    for (const [k, p] of Object.entries(paineis)) p.hidden = k !== chave;
  }

  const i = imovel || {};
  const g = el('div', 'grade');
  const ro = doFeed ? { disabled: '' } : {};
  const add = (rotulo, n, cls) => { const c = campo(rotulo, n); if (cls) c.classList.add(cls); g.appendChild(c); };
  add('Título do anúncio', entrada('titulo', { valor: i.titulo, required: '', minlength: 3, maxlength: 200, ...ro }), 'largo');
  add('Tipo', Object.assign(selecao('tipo', Object.entries(v.tipos), i.tipo), doFeed ? { disabled: true } : {}));
  add('Finalidade', Object.assign(selecao('finalidade', FINALIDADES, i.finalidade || 'venda'), doFeed ? { disabled: true } : {}));
  add('Preço (R$; aluguel = mensal)', entrada('preco', { type: 'number', min: 1, step: 1, valor: i.preco, required: '', ...ro }));
  add('Aluguel (se venda e aluguel)', entrada('preco_aluguel', { type: 'number', min: 1, step: 1, valor: i.preco_aluguel, ...ro }));
  add('Bairro', entrada('bairro', { valor: i.bairro, required: '', minlength: 2, list: 'bairros-carteira', ...ro }));
  add('Cidade', entrada('cidade', { valor: i.cidade || (imoveis[0] && imoveis[0].cidade), required: '', minlength: 2, ...ro }));
  add('UF', entrada('uf', { valor: i.uf || 'RJ', maxlength: 2, ...ro }));
  add('Código de referência', entrada('codigo_referencia', { valor: i.codigo_referencia, maxlength: 80, ...ro }));
  for (const [rot, n] of [['Quartos', 'quartos'], ['Suítes', 'suites'], ['Banheiros', 'banheiros'], ['Vagas', 'vagas']]) {
    add(rot, entrada(n, { type: 'number', min: 0, max: 50, valor: i[n], placeholder: 'não informado', ...ro }));
  }
  add('Área útil (m²)', entrada('area_m2', { type: 'number', min: 1, step: 0.1, valor: i.area_m2, ...ro }));
  add('Área do terreno (m²)', entrada('area_terreno', { type: 'number', min: 1, step: 0.1, valor: i.area_terreno, ...ro }));
  add('Condomínio (R$/mês)', entrada('condominio', { type: 'number', min: 0, valor: i.condominio, ...ro }));
  add('IPTU (R$/ano)', entrada('iptu', { type: 'number', min: 0, valor: i.iptu, ...ro }));
  add('Endereço (opcional)', entrada('endereco', { valor: i.endereco, maxlength: 300, ...ro }), 'meio');
  add('Latitude', entrada('latitude', { type: 'number', step: 'any', valor: i.latitude, ...ro }));
  add('Longitude', entrada('longitude', { type: 'number', step: 'any', valor: i.longitude, ...ro }));
  const mostrar = el('label', 'check largo');
  const cxMostrar = entrada('mostrar_endereco', { type: 'checkbox', ...ro });
  cxMostrar.checked = !!i.mostrar_endereco;
  mostrar.append(cxMostrar, el('span', '', 'Mostrar o endereço para o comprador (senão, só o bairro)'));
  g.appendChild(mostrar);
  const listaBairros = el('datalist');
  listaBairros.id = 'bairros-carteira';
  for (const b of [...new Set(imoveis.map((x) => x.bairro))]) { const o = el('option'); o.value = b; listaBairros.appendChild(o); }
  g.appendChild(listaBairros);

  const conjunto = el('fieldset', 'largo');
  conjunto.appendChild(el('legend', '', 'Características (a busca só afirma o que estiver marcado aqui ou escrito na descrição)'));
  const caixaCar = el('div', 'caracteristicas');
  for (const [slug, rotulo] of Object.entries(v.caracteristicas)) {
    const l = el('label');
    const c = entrada('caracteristicas', { type: 'checkbox', value: slug, ...ro });
    c.checked = (i.caracteristicas || []).includes(slug);
    l.append(c, el('span', '', rotulo));
    caixaCar.appendChild(l);
  }
  conjunto.appendChild(caixaCar);
  g.appendChild(conjunto);
  add('Outros itens (um por linha, ex.: “Fogão a lenha”)', entrada('comodidades', { tag: 'textarea', rows: 3, valor: (i.comodidades || []).join('\n'), ...ro }), 'largo');

  const desc = entrada('descricao', { tag: 'textarea', rows: 6, valor: i.descricao || '', maxlength: 8000, ...ro });
  const rotuloDesc = el('span', 'rotulo-com-acao', 'Descrição');
  if (!doFeed) {
    rotuloDesc.appendChild(botao('✦ Escrever com IA', 'btn-sm', async (e) => {
      const b = e.currentTarget;
      const dados = dadosDoFormulario(f, []);
      if (!dados.bairro || !dados.tipo) { avisar('Preencha pelo menos tipo e bairro.', 'info'); return; }
      b.disabled = true; b.textContent = 'Escrevendo…';
      try {
        const r = await api('/api/imoveis/gerar-descricao', { method: 'POST', json: { ...dados, observacoes: dados.descricao } });
        desc.value = r.descricao;
        if (r.fonte !== 'ia') avisar('IA não configurada: usamos um modelo de texto. Revise antes de salvar.', 'info');
      } catch (err) { avisar(err.message, 'erro'); }
      b.disabled = false; b.textContent = '✦ Escrever com IA';
    }));
  }
  const campoDesc = el('label', 'campo largo');
  campoDesc.append(rotuloDesc, desc, el('span', 'ajuda', 'Escreva só o que é verdade sobre o imóvel: a busca mostra ao comprador o trecho exato da descrição como prova.'));
  g.appendChild(campoDesc);

  const corretores = [['', 'Ninguém (vai para o WhatsApp da imobiliária)'], ...equipe.map((u) => [String(u.id), `${u.nome}${u.whatsapp ? '' : ' (sem WhatsApp)'}`])];
  add('Corretor responsável (recebe os leads deste imóvel)', selecao('corretor_id', corretores, i.corretor_id ?? ''), 'meio');
  const ativo = el('label', 'check meio');
  const cxAtivo = entrada('ativo', { type: 'checkbox' });
  cxAtivo.checked = imovel ? imovel.ativo : true;
  ativo.append(cxAtivo, el('span', '', 'Disponível — aparece nas buscas do site'));
  g.appendChild(ativo);
  paineis.anuncio.appendChild(g);

  const fotos = (i.fotos || []).map((x) => ({ url: x.url, legenda: x.legenda || '' }));
  paineis.midia.appendChild(editorDeFotos(fotos, i.id, doFeed));
  const gm = el('div', 'grade');
  const cv = campo('Vídeo (YouTube ou Vimeo)', entrada('video_url', { type: 'url', valor: i.video_url, placeholder: 'https://youtube.com/…', ...ro }));
  cv.classList.add('meio');
  const cd = campo(`Vídeo de drone${temRecurso('midia_drone') ? '' : ' (planos Profissional e Premium)'}`, entrada('video_drone_url', { type: 'url', valor: i.video_drone_url, placeholder: 'https://youtube.com/…' }));
  cd.classList.add('meio');
  const cu = campo('Link do anúncio no seu site', entrada('url_anuncio', { type: 'url', valor: i.url_anuncio, ...ro }));
  cu.classList.add('largo');
  gm.append(cv, cd, cu);
  paineis.midia.appendChild(gm);

  paineis.inteligencia.appendChild(abaContexto(imovel));

  if (!imovel) {
    paineis.planta.appendChild(el('p', 'ajuda', 'Salve o imóvel primeiro para desenhar a planta.'));
  } else if (!temRecurso('planta_interativa') && !imovel.maquete_liberada) {
    paineis.planta.appendChild(el('p', 'ajuda', 'Planta interativa e maquete 3D fazem parte do plano Premium.'));
    if (ehDono()) {
      paineis.planta.appendChild(botao('Comprar maquete 3D só para este imóvel', 'btn-sm', async () => {
        try { location.href = (await api(`/api/imoveis/${imovel.id}/maquete-avulsa`, { method: 'POST' })).url; }
        catch (e) { avisar(e.message, 'erro'); }
      }));
    }
  } else {
    const n = (imovel.planta && imovel.planta.comodos) ? imovel.planta.comodos.length : 0;
    paineis.planta.append(
      el('p', 'ajuda', n ? `Planta com ${n} cômodos desenhados.` : 'Envie a imagem da planta e desenhe os cômodos por cima. A maquete 3D é gerada a partir deles.'),
      botao(n ? 'Abrir o editor de planta' : 'Desenhar a planta', 'btn-solid', () => { fechar(); abrirEditorPlanta(imovel, recarregar); }),
    );
  }

  conteudo.append(abas, f);
  mostrarAba('anuncio');
  const erro = el('div', 'aviso aviso-erro');
  erro.hidden = true;
  conteudo.appendChild(erro);

  rodape.append(botao('Cancelar', 'btn-ghost', fechar), botao('Salvar imóvel', 'btn-solid', async () => {
    erro.hidden = true;
    if (!doFeed && !f.reportValidity()) { mostrarAba('anuncio'); f.reportValidity(); return; }
    const dados = dadosDoFormulario(f, fotos);
    if (doFeed) {
      // Campos do feed são ignorados pelo servidor; não os reenviamos para não esbarrar em validação.
      Object.assign(dados, { fotos: [], video_url: null, url_anuncio: null });
    }
    try {
      if (imovel) await api(`/api/imoveis/${imovel.id}`, { method: 'PUT', json: dados });
      else await api('/api/imoveis', { method: 'POST', json: dados });
      fechar();
      avisar(imovel ? 'Imóvel atualizado.' : 'Imóvel cadastrado — já aparece nas buscas do seu site.');
      recarregar();
    } catch (e) {
      erro.textContent = e.message;
      erro.hidden = false;
    }
  }));
}

function abrirImportacao(recarregar) {
  const { conteudo, rodape, fechar } = abrirModal('Importar planilha');
  conteudo.append(el('p', 'ajuda', 'Salve a planilha como CSV (Excel: Arquivo → Salvar como → CSV). Use o modelo para ver as colunas. Se o seu sistema gera feed XML, prefira a Integração XML: ela mantém tudo atualizado sozinha.'));
  const arquivo = entrada('arquivo', { type: 'file', accept: '.csv,text/csv' });
  const resultado = el('div', 'aviso');
  resultado.hidden = true;
  conteudo.append(botao('Baixar modelo', 'btn-sm', () => {
    const csv = 'titulo;tipo;finalidade;bairro;cidade;preco;quartos;suites;banheiros;vagas;area_m2;caracteristicas;descricao;foto_url;codigo_referencia\n'
      + 'Casa com quintal;casa;venda;Olaria;Nova Friburgo;650000;3;1;2;2;140;jardim|lareira|churrasqueira;Casa térrea com quintal gramado.;;CA-001\n'
      + 'Apartamento no Centro;apartamento;aluguel;Centro;Nova Friburgo;1800;2;0;1;1;68;elevador|portaria-24h;Perto do comércio.;;AP-002\n';
    baixar(new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' }), 'modelo-imoveis-homeclue.csv');
  }), arquivo, resultado);
  rodape.append(botao('Fechar', 'btn-ghost', fechar), botao('Importar', 'btn-solid', async () => {
    if (!arquivo.files[0]) return;
    try {
      const r = await enviarArquivo('/api/imoveis/importar', arquivo.files[0]);
      resultado.className = `aviso ${r.erros.length ? 'aviso-info' : 'aviso-ok'}`;
      resultado.replaceChildren(el('div', '', `${r.importados} imóve${r.importados === 1 ? 'l importado' : 'is importados'}.`));
      for (const t of r.erros) resultado.appendChild(el('div', '', t));
      recarregar();
    } catch (e) { resultado.className = 'aviso aviso-erro'; resultado.textContent = e.message; }
    resultado.hidden = false;
  }));
}

export async function render(pagina) {
  await garantirVocabulario();
  const [lista, pessoas] = await Promise.all([api('/api/imoveis'), api('/api/equipe')]);
  imoveis = lista;
  equipe = pessoas;
  const recarregar = () => { location.hash = '#imoveis'; window.dispatchEvent(new HashChangeEvent('hashchange')); };

  const noAr = imoveis.filter((x) => x.ativo && !x.removido_do_feed_em).length;
  pagina.appendChild(cabecalho('Imóveis', `${imoveis.length} cadastrados · ${noAr} aparecendo nas buscas`,
    botao('Importar planilha', '', () => abrirImportacao(recarregar)),
    botao('+ Novo imóvel', 'btn-solid', () => abrirEditor(null, recarregar))));

  const filtros = el('div', 'filtros');
  const busca = entrada('filtro', { placeholder: 'Filtrar por título, bairro ou código…' });
  const origem = selecao('origem', [['', 'Todas as origens'], ['feed', 'Do feed XML'], ['manual', 'Cadastrados aqui']]);
  filtros.append(busca, origem);
  pagina.appendChild(filtros);
  const caixa = el('div', 'lista-imoveis');
  pagina.appendChild(caixa);

  // Estoque grande (1.000+ imóveis): desenha aos poucos, para a página não
  // criar milhares de cartões e baixar milhares de fotos de uma vez.
  const POR_VEZ = 60;
  let mostrando = POR_VEZ;
  const desenhar = () => {
    const termo = busca.value.trim().toLowerCase();
    const filtrados = imoveis.filter((x) => (!origem.value || x.origem === origem.value)
      && (!termo || [x.titulo, x.bairro, x.cidade, x.codigo_referencia || ''].some((t) => t.toLowerCase().includes(termo))));
    if (!imoveis.length) {
      caixa.replaceChildren(vazio('Nenhum imóvel ainda', 'Conecte o feed XML do seu sistema (recomendado), importe uma planilha ou cadastre um a um.',
        Object.assign(el('a', 'btn btn-solid', 'Conectar o feed XML'), { href: '#integracao' })));
      return;
    }
    caixa.replaceChildren(...filtrados.slice(0, mostrando).map((x) => linha(x, recarregar)));
    if (!filtrados.length) caixa.appendChild(el('p', 'ajuda', 'Nenhum imóvel com esse filtro.'));
    if (filtrados.length > mostrando) {
      caixa.appendChild(botao(`Mostrar mais (${filtrados.length - mostrando} restantes)`, 'mais-imoveis', () => {
        mostrando += POR_VEZ;
        desenhar();
      }));
    }
  };
  busca.addEventListener('input', () => { mostrando = POR_VEZ; desenhar(); });
  origem.addEventListener('change', () => { mostrando = POR_VEZ; desenhar(); });
  desenhar();
}
