// Preços vêm da API para nunca divergirem do que o painel cobra.
(function () {
  const lista = document.getElementById('precos-lista');
  const numero = (n) => (n === null ? 'Ilimitados' : n.toLocaleString('pt-BR'));

  function cartao(p) {
    const c = document.createElement('article');
    c.className = 'cartao preco' + (p.id === 'pro' ? ' destaque' : '');
    if (p.id === 'pro') {
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
    valor.textContent = p.preco_mensal ? `R$ ${p.preco_mensal}` : 'R$ 0';
    const mes = document.createElement('small');
    mes.textContent = ' /mês';
    valor.appendChild(mes);

    const itens = document.createElement('ul');
    [
      `${numero(p.limite_imoveis)} imóveis`,
      `${numero(p.limite_buscas_mes)} buscas com IA por mês`,
      `${p.limite_usuarios} usuário${p.limite_usuarios > 1 ? 's' : ''}`,
      'Leads ilimitados e funil de vendas',
      p.marca_kaza_no_widget ? 'Selo "Kaza Pro" no widget' : 'Widget sem a nossa marca',
    ].forEach((t) => {
      const li = document.createElement('li');
      li.textContent = t;
      itens.appendChild(li);
    });

    const cta = document.createElement('a');
    cta.className = 'btn ' + (p.id === 'pro' ? 'btn-solid' : '');
    cta.href = 'entrar.html#cadastro';
    cta.textContent = p.preco_mensal ? `Assinar ${p.nome}` : 'Começar grátis';

    c.append(titulo, sub, valor, itens, cta);
    return c;
  }

  fetch('/api/assinatura/planos')
    .then((r) => r.json())
    .then((d) => d.planos.forEach((p) => lista.appendChild(cartao(p))))
    .catch(() => { lista.textContent = 'Não foi possível carregar os preços agora.'; });
})();
