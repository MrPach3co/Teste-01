// Comparador: até 3 imóveis lado a lado, com os mesmos pontos do pedido.
import { ICONE_STATUS, ROTULO_STATUS, el, fundoFoto, precoDoImovel, reais } from '../comum/util.js';
import { abrirCamada, estado, fecharCamada, registrarEvento } from './estado.js';

const camada = document.getElementById('camada-comparar');

export function abrirComparador({ aoDetalhe }) {
  const imoveis = [...estado.comparar].map((id) => estado.resultados.get(id)).filter(Boolean);
  camada.replaceChildren();
  const topo = el('div', 'camada-topo');
  const voltar = el('button', 'btn btn-ghost btn-sm', '← Voltar');
  voltar.type = 'button';
  voltar.addEventListener('click', fecharCamada);
  topo.append(voltar, el('h2', '', `Comparando ${imoveis.length} imóveis`));

  const tabela = el('table');
  const linha = (rotulo, celulas, destacarMelhor = null) => {
    const tr = el('tr');
    tr.appendChild(el('th', '', rotulo));
    const melhor = destacarMelhor ? destacarMelhor(celulas.map((c) => c.valor)) : -1;
    celulas.forEach((c, i) => {
      const td = el('td', i === melhor ? 'melhor' : '');
      if (c.no) td.appendChild(c.no); else td.textContent = c.texto ?? '—';
      tr.appendChild(td);
    });
    tabela.appendChild(tr);
  };
  const maior = (valores) => {
    const v = valores.map((x) => (typeof x === 'number' ? x : -Infinity));
    const max = Math.max(...v);
    return max === -Infinity || v.filter((x) => x === max).length > 1 ? -1 : v.indexOf(max);
  };
  const menor = (valores) => {
    const v = valores.map((x) => (typeof x === 'number' ? x : Infinity));
    const min = Math.min(...v);
    return min === Infinity || v.filter((x) => x === min).length > 1 ? -1 : v.indexOf(min);
  };

  linha('', imoveis.map((i) => {
    const foto = el('button', 'foto-mini');
    foto.type = 'button';
    foto.style.width = '100%';
    foto.style.border = '0';
    foto.setAttribute('aria-label', `Ver ${i.titulo}`);
    fundoFoto(foto, i.foto, i.id);
    foto.addEventListener('click', () => { fecharCamada(); aoDetalhe(i.id); });
    return { no: foto };
  }));
  linha('Imóvel', imoveis.map((i) => ({ texto: i.titulo })));
  linha('Compatibilidade', imoveis.map((i) => ({ texto: i.match !== null ? `${i.match}%` : '—', valor: i.match })), maior);
  const precos = imoveis.map((i) => precoDoImovel(i, estado.criterios && estado.criterios.finalidade));
  linha('Preço', precos.map((p) => ({ texto: reais(p.valor) + (p.aluguel ? '/mês' : ''), valor: p.valor })), menor);
  linha('Preço por m²', imoveis.map((i, k) => {
    const v = i.area_m2 ? precos[k].valor / i.area_m2 : null;
    return { texto: v ? reais(v) : '—', valor: v };
  }), menor);
  linha('Área', imoveis.map((i) => ({ texto: i.area_m2 ? `${i.area_m2} m²` : 'Não informada', valor: i.area_m2 })), maior);
  linha('Quartos', imoveis.map((i) => ({ texto: i.quartos ?? 'Não informado', valor: i.quartos })), maior);
  linha('Suítes', imoveis.map((i) => ({ texto: i.suites ?? 'Não informado', valor: i.suites })), maior);
  linha('Banheiros', imoveis.map((i) => ({ texto: i.banheiros ?? 'Não informado', valor: i.banheiros })), maior);
  linha('Vagas', imoveis.map((i) => ({ texto: i.vagas ?? 'Não informado', valor: i.vagas })), maior);
  linha('Condomínio', imoveis.map((i) => ({ texto: i.condominio ? reais(i.condominio) : '—', valor: i.condominio })), menor);
  linha('Local', imoveis.map((i) => ({ texto: `${i.bairro}, ${i.cidade}` })));

  const chaves = [];
  for (const i of imoveis) for (const p of i.pontos) if (!chaves.some((c) => c.chave === p.chave)) chaves.push(p);
  for (const ref of chaves) {
    linha(ref.criterio, imoveis.map((i) => {
      const p = i.pontos.find((x) => x.chave === ref.chave);
      if (!p) return { texto: '—' };
      const caixa = el('span', `st-${p.status}`);
      caixa.append(el('strong', '', `${ICONE_STATUS[p.status]} ${ROTULO_STATUS[p.status]}`), el('span', 'prova', p.evidencia));
      caixa.querySelector('.prova').style.display = 'block';
      return { no: caixa };
    }));
  }

  const corpo = el('div', 'camada-corpo');
  const rolagem = el('div', 'tabela-comparar');
  rolagem.appendChild(tabela);
  corpo.append(rolagem, el('p', 'camada-secao fonte', 'Em verde, o melhor valor de cada linha. Os pontos vêm só do que cada anúncio informa.'));
  camada.append(topo, corpo);
  abrirCamada(camada);
  registrarEvento('comparacao', null);
}
