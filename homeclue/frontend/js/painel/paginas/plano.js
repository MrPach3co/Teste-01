import { el } from '../../comum/util.js';
import { api, avisar, botao, cabecalho, ehDono, estado } from '../nucleo.js';

const numero = (v) => (v === null || v === undefined ? '∞' : v.toLocaleString('pt-BR'));

function uso(rotulo, atual, limite) {
  const c = el('div', 'cartao kpi');
  c.append(el('span', 'kpi-rotulo', rotulo), el('span', 'kpi-valor', `${numero(atual)} / ${numero(limite)}`));
  if (limite) {
    const m = el('div', `medidor${atual / limite >= 0.85 ? ' alerta' : ''}`);
    const i = el('i');
    i.style.width = `${Math.min(100, (100 * atual) / limite)}%`;
    m.appendChild(i);
    c.appendChild(m);
  }
  return c;
}

export async function render(pagina) {
  const [catalogo, m] = await Promise.all([api('/api/assinatura/planos'), api('/api/painel/metricas')]);
  const atual = estado.sessao.imobiliaria.plano;
  const plano = catalogo.planos.find((p) => p.id === atual) || catalogo.planos[0];
  pagina.appendChild(cabecalho('Plano', `Você está no plano ${plano.nome}.`));
  const usos = el('div', 'uso');
  usos.append(uso('Buscas com IA neste mês', m.buscas_mes, plano.limite_buscas_mes), uso('Imóveis', m.imoveis_total, plano.limite_imoveis),
    uso('Usuários', m.usuarios_total, plano.limite_usuarios));
  pagina.appendChild(usos);

  const grade = el('div', 'planos');
  for (const p of catalogo.planos) {
    const c = el('article', `cartao plano${p.id === atual ? ' atual' : ''}`);
    const valor = el('div', 'valor', p.preco_mensal ? `R$ ${p.preco_mensal.toLocaleString('pt-BR')}` : 'Grátis');
    if (p.preco_mensal) valor.appendChild(el('small', '', ' /mês'));
    const itens = el('ul');
    for (const t of [`${numero(p.limite_imoveis)} imóveis`, `${numero(p.limite_buscas_mes)} buscas com IA/mês`, `${p.limite_usuarios} usuário(s)`,
      ...p.recursos.map((r) => catalogo.nomes_recursos[r]).filter(Boolean)]) itens.appendChild(el('li', '', t));
    c.append(el('h3', '', p.nome), el('p', 'ajuda', p.destaque), valor, itens);
    if (p.id === atual) c.appendChild(el('span', 'selo', 'SEU PLANO'));
    else if (p.preco_mensal && catalogo.pagamento_online && ehDono()) {
      c.appendChild(botao(`Assinar ${p.nome}`, 'btn-solid', async (e) => {
        e.currentTarget.disabled = true;
        try { location.href = (await api(`/api/assinatura/checkout?plano=${p.id}`, { method: 'POST' })).url; }
        catch (err) { avisar(err.message, 'erro'); e.currentTarget.disabled = false; }
      }));
    }
    grade.appendChild(c);
  }
  pagina.appendChild(grade);
  if (catalogo.cobranca_por_lead) pagina.appendChild(el('p', 'aviso aviso-info', 'Além da mensalidade, cada lead entregue (contato pelo WhatsApp ou formulário) é cobrado por uso, conforme o seu contrato. Cliques repetidos da mesma pessoa no mesmo imóvel contam uma vez só.'));
  if (!catalogo.pagamento_online) pagina.appendChild(el('p', 'aviso aviso-info', 'O pagamento online ainda não está ativo nesta instalação. Para mudar de plano, fale com a Homeclue.'));
  if (catalogo.pagamento_online && atual !== 'gratis' && ehDono()) {
    pagina.appendChild(botao('Gerenciar assinatura e faturas', '', async () => {
      try { location.href = (await api('/api/assinatura/portal', { method: 'POST' })).url; } catch (e) { avisar(e.message, 'erro'); }
    }));
  }
}
