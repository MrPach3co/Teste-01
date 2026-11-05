import { el } from '../../comum/util.js';
import { api, avisar, botao, cabecalho, entrada, selecao, vazio } from '../nucleo.js';

export async function render(pagina) {
  pagina.appendChild(cabecalho('Bairros', 'O que você quer que o comprador saiba de cada bairro. Aparece na página do imóvel e no ranking de valorização, sempre como “segundo a imobiliária”.'));
  const bairros = await api('/api/bairros');
  if (!bairros.length) { pagina.appendChild(vazio('Nenhum bairro ainda', 'Os bairros aparecem aqui quando houver imóveis cadastrados.')); return; }
  for (const b of bairros) {
    const c = el('form', 'cartao bloco');
    c.appendChild(el('h2', '', `${b.nome} · ${b.imoveis} imóve${b.imoveis === 1 ? 'l' : 'is'}`));
    const descricao = entrada('descricao', { tag: 'textarea', rows: 2, valor: b.descricao, maxlength: 2000, placeholder: 'Ex.: bairro residencial, perto do centro, com comércio e escolas.' });
    const valorizacao = selecao('valorizacao', [['', 'Não informar'], ['baixa', 'Potencial baixo'], ['media', 'Potencial médio'], ['alta', 'Potencial alto']], b.valorizacao || '');
    const justificativa = entrada('justificativa', { valor: b.valorizacao_justificativa, maxlength: 500, placeholder: 'Por quê? Ex.: obras do novo acesso, pouca oferta de terrenos' });
    const linha = el('div', 'grade');
    const cv = el('label', 'campo');
    cv.append(el('span', '', 'Valorização (na sua avaliação)'), valorizacao);
    const cj = el('label', 'campo meio');
    cj.append(el('span', '', 'Justificativa'), justificativa);
    linha.append(cv, cj);
    const cd = el('label', 'campo');
    cd.append(el('span', '', 'Descrição para o comprador'), descricao);
    const salvar = botao('Salvar', 'btn-sm btn-solid');
    salvar.type = 'submit';
    c.append(cd, linha, salvar);
    c.addEventListener('submit', async (e) => {
      e.preventDefault();
      try {
        await api(`/api/bairros/${encodeURIComponent(b.nome)}`, { method: 'PUT', json: {
          descricao: descricao.value.trim(), valorizacao: valorizacao.value || null, valorizacao_justificativa: justificativa.value.trim() } });
        avisar(`${b.nome} salvo.`);
      } catch (err) { avisar(err.message, 'erro'); }
    });
    pagina.appendChild(c);
  }
}
