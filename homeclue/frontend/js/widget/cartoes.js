// Cartões de resultado com o match explicado, e as abas de ranking.
import { ICONE_STATUS, ROTULO_STATUS, el, fundoFoto, precoDoImovel, reais } from '../comum/util.js';
import { estado, linkWhatsApp } from './estado.js';

export function listaDePontos(pontos, { limite = null, comFonte = false } = {}) {
  const ordem = { atende: 0, parcial: 1, indicio: 2, nao_atende: 3, nao_informado: 4 };
  const ordenados = [...pontos].sort((a, b) => ordem[a.status] - ordem[b.status]);
  const lista = el('ul', 'pontos');
  for (const p of limite ? ordenados.slice(0, limite) : ordenados) {
    const li = el('li', `st-${p.status}`);
    const icone = el('span', 'icone', ICONE_STATUS[p.status]);
    icone.setAttribute('aria-label', ROTULO_STATUS[p.status]);
    icone.title = ROTULO_STATUS[p.status];
    const texto = el('span');
    texto.append(el('strong', '', p.criterio));
    const prova = el('span', 'prova', p.evidencia);
    texto.appendChild(prova);
    if (comFonte && p.foto) {
      const img = el('img', 'prova-foto');
      img.src = p.foto; img.alt = 'Foto do anúncio usada como indício'; img.loading = 'lazy';
      texto.appendChild(img);
    }
    li.append(icone, texto);
    lista.appendChild(li);
  }
  return lista;
}

export function resumoDosPontos(pontos) {
  const n = (s) => pontos.filter((p) => p.status === s).length;
  const partes = [`${n('atende')} de ${pontos.length} pontos atendidos`];
  if (n('nao_informado')) partes.push(`${n('nao_informado')} sem informação no anúncio`);
  return partes.join(' · ');
}

export function cartao(imovel, { motivo, aoDetalhe, aoComparar, aoContato }) {
  const c = el('article', 'cartao imovel');
  c.dataset.id = imovel.id;
  const foto = el('button', 'imovel-foto');
  foto.type = 'button';
  foto.setAttribute('aria-label', `Ver detalhes: ${imovel.titulo}`);
  fundoFoto(foto, imovel.foto, imovel.id);
  foto.addEventListener('click', () => aoDetalhe(imovel.id));
  if (imovel.match !== null && imovel.match !== undefined) {
    const selo = el('span', 'imovel-match', `${imovel.match}%`);
    selo.appendChild(el('small', '', ' compatível'));
    foto.appendChild(selo);
  }
  const selos = el('span', 'imovel-selos');
  selos.appendChild(el('span', '', { aluguel: 'Aluguel', venda_aluguel: 'Venda/aluguel' }[imovel.finalidade] || 'Venda'));
  if (imovel.tem_maquete) selos.appendChild(el('span', '', '3D'));
  else if (imovel.tem_planta) selos.appendChild(el('span', '', 'Planta'));
  if (imovel.tem_video) selos.appendChild(el('span', '', 'Vídeo'));
  foto.appendChild(selos);

  const info = el('div', 'imovel-info');
  const preco = precoDoImovel(imovel, estado.criterios && estado.criterios.finalidade);
  info.append(
    el('div', 'imovel-preco', reais(preco.valor) + (preco.aluguel ? '/mês' : '')),
    el('div', 'imovel-titulo', imovel.titulo),
    el('div', 'imovel-local', `${imovel.bairro}, ${imovel.cidade}`),
  );
  const dados = [
    imovel.area_m2 ? `${imovel.area_m2} m²` : null,
    imovel.quartos ? `${imovel.quartos} quarto${imovel.quartos > 1 ? 's' : ''}` : null,
    imovel.suites ? `${imovel.suites} suíte${imovel.suites > 1 ? 's' : ''}` : null,
    imovel.vagas ? `${imovel.vagas} vaga${imovel.vagas > 1 ? 's' : ''}` : null,
  ].filter(Boolean).join(' · ');
  if (dados) info.appendChild(el('div', 'imovel-dados', dados));
  if (motivo) info.appendChild(el('div', 'imovel-motivo', motivo));

  if (imovel.pontos.length) {
    info.appendChild(listaDePontos(imovel.pontos, { limite: 4 }));
    const mais = el('button', 'ver-mais', imovel.pontos.length > 4
      ? `Ver os ${imovel.pontos.length} pontos e as provas` : 'Ver detalhes e provas');
    mais.type = 'button';
    mais.addEventListener('click', () => aoDetalhe(imovel.id));
    info.appendChild(mais);
  }

  const acoes = el('div', 'imovel-acoes');
  if (estado.config.whatsapp) {
    const wa = el('a', 'btn btn-sm btn-whatsapp', 'WhatsApp');
    wa.href = linkWhatsApp({ imovelId: imovel.id });
    wa.target = '_blank';
    wa.rel = 'noopener';
    acoes.appendChild(wa);
  }
  const contato = el('button', 'btn btn-sm', 'Tenho interesse');
  contato.type = 'button';
  contato.addEventListener('click', () => aoContato(imovel));
  acoes.appendChild(contato);
  info.appendChild(acoes);

  if (estado.config.recursos.comparador) {
    const rotulo = el('label', 'comparar-check');
    const caixa = el('input');
    caixa.type = 'checkbox';
    caixa.checked = estado.comparar.has(imovel.id);
    caixa.addEventListener('change', () => aoComparar(imovel.id, caixa));
    rotulo.append(caixa, document.createTextNode('Comparar'));
    info.appendChild(rotulo);
  }
  c.append(foto, info);
  return c;
}

export function blocoDeResultados(resposta, opcoes) {
  const bloco = el('div', 'bloco-resultados');
  const porId = new Map(resposta.resultados.map((r) => [r.id, r]));
  const grade = el('div', 'resultados');
  const explicacao = el('p', 'ranking-explicacao');

  const mostrar = (ranking) => {
    grade.replaceChildren();
    const ordem = ranking ? ranking.itens : resposta.resultados.map((r) => ({ imovel_id: r.id, motivo: null }));
    explicacao.textContent = ranking && ranking.id !== 'melhor' ? ranking.explicacao : '';
    explicacao.hidden = !explicacao.textContent;
    for (const item of ordem) {
      const imovel = porId.get(item.imovel_id);
      if (imovel) grade.appendChild(cartao(imovel, { ...opcoes, motivo: ranking && ranking.id !== 'melhor' ? item.motivo : null }));
    }
  };

  const rankings = estado.config.recursos.rankings ? resposta.rankings.filter((r) => r.itens.length) : [];
  if (rankings.length > 1) {
    const abas = el('div', 'rankings');
    abas.setAttribute('role', 'group');
    abas.setAttribute('aria-label', 'Ordenar por perfil');
    rankings.forEach((ranking, i) => {
      const b = el('button', '', ranking.titulo);
      b.type = 'button';
      b.setAttribute('aria-pressed', i === 0 ? 'true' : 'false');
      b.addEventListener('click', () => {
        abas.querySelectorAll('button').forEach((x) => x.setAttribute('aria-pressed', 'false'));
        b.setAttribute('aria-pressed', 'true');
        mostrar(ranking);
      });
      abas.appendChild(b);
    });
    bloco.append(abas, explicacao);
  }
  bloco.appendChild(grade);
  mostrar(rankings[0] || null);
  return bloco;
}
