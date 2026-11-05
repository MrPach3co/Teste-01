// Planos vêm da API para nunca divergirem do que o painel cobra.
(function () {
  const lista = document.getElementById('precos-lista');
  const numero = (n) => (n === null ? 'Ilimitados' : n.toLocaleString('pt-BR'));

  function item(texto) {
    const li = document.createElement('li');
    li.textContent = texto;
    return li;
  }

  function cartao(p, nomesRecursos) {
    const c = document.createElement('article');
    c.className = 'cartao preco' + (p.id === 'profissional' ? ' destaque' : '');
    if (p.id === 'profissional') {
      const selo = document.createElement('span');
      selo.className = 'preco-selo';
      selo.textContent = 'MAIS ESCOLHIDO';
      c.appendChild(selo);
    }
    const titulo = document.createElement('h3');
    titulo.textContent = p.nome;
    const sub = document.createElement('p');
    sub.className = 'preco-sub';
    sub.textContent = p.destaque;
    const valor = document.createElement('div');
    valor.className = 'preco-valor';
    valor.textContent = p.preco_mensal ? `R$ ${p.preco_mensal.toLocaleString('pt-BR')}` : 'R$ 0';
    const mes = document.createElement('small');
    mes.textContent = ' /mês';
    valor.appendChild(mes);
    const itens = document.createElement('ul');
    itens.append(item(`Até ${numero(p.limite_imoveis)} imóveis`), item(`${numero(p.limite_buscas_mes)} buscas com IA por mês`),
      item(`${p.limite_usuarios} usuário${p.limite_usuarios > 1 ? 's' : ''}`), item('Feed XML, match explicado e leads no WhatsApp'));
    for (const r of p.recursos) if (nomesRecursos[r]) itens.appendChild(item(nomesRecursos[r]));
    const cta = document.createElement('a');
    cta.className = 'btn ' + (p.id === 'profissional' ? 'btn-solid' : '');
    cta.href = 'entrar.html#cadastro';
    cta.textContent = p.preco_mensal ? `Assinar ${p.nome}` : 'Começar grátis';
    c.append(titulo, sub, valor, itens, cta);
    return c;
  }

  fetch('/api/assinatura/planos')
    .then((r) => r.json())
    .then((d) => d.planos.forEach((p) => lista.appendChild(cartao(p, d.nomes_recursos))))
    .catch(() => { lista.textContent = 'Não foi possível carregar os planos agora.'; });
})();
