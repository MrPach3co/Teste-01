// Experiência de busca que roda dentro do iframe do widget (ou sozinha,
// como página: /embed.html?k=CHAVE). Todo texto vindo da API é inserido
// com textContent — nunca innerHTML — para não abrir brecha de XSS.
(function () {
  const params = new URLSearchParams(location.search);
  const chave = params.get('k') || '';
  const dentroDeIframe = window.parent !== window;
  const api = (caminho) => `/api/publico/${encodeURIComponent(chave)}${caminho}`;

  const $ = (id) => document.getElementById(id);
  const corpo = $('corpo');
  const form = $('form-busca');
  const input = $('texto');
  const botao = $('enviar');

  let config = { whatsapp: null };
  let ultimaBusca = '';
  let imovelDoLead = null;

  const GRADIENTES = [
    ['#2E5741', '#9DB8A4'], ['#9C4A26', '#E2B59A'], ['#3B4A5E', '#A9B8C9'],
    ['#6B5B3E', '#D9C9A3'], ['#1F3B2C', '#C9D6C2'], ['#5E3B4A', '#D4AFC0'],
  ];

  function el(tag, classe, texto) {
    const n = document.createElement(tag);
    if (classe) n.className = classe;
    if (texto !== undefined) n.textContent = texto;
    return n;
  }

  function reais(v) {
    return v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 });
  }

  function rolarParaBaixo() { corpo.scrollTop = corpo.scrollHeight; }

  function balao(texto, quem) {
    const b = el('div', `balao balao-${quem}`, texto);
    corpo.appendChild(b);
    rolarParaBaixo();
    return b;
  }

  function digitando() {
    const b = el('div', 'balao balao-ia');
    const d = el('span', 'digitando');
    d.append(el('i'), el('i'), el('i'));
    b.appendChild(d);
    corpo.appendChild(b);
    rolarParaBaixo();
    return b;
  }

  function linkWhatsApp(imovel) {
    if (!config.whatsapp) return null;
    const numero = config.whatsapp.replace(/\D/g, '');
    const msg = imovel
      ? `Olá! Vi o imóvel "${imovel.titulo}" (${reais(imovel.preco)}) no site e quero saber mais.`
      : 'Olá! Vim pelo site e quero ajuda para encontrar um imóvel.';
    return `https://wa.me/${numero}?text=${encodeURIComponent(msg)}`;
  }

  function cartaoImovel(imovel) {
    const c = el('article', 'cartao imovel');
    const foto = el('div', 'imovel-foto');
    if (imovel.foto_url) {
      foto.style.backgroundImage = `url("${encodeURI(imovel.foto_url)}")`;
    } else {
      const [a, b] = GRADIENTES[imovel.id % GRADIENTES.length];
      foto.style.backgroundImage = `linear-gradient(135deg, ${a}, ${b})`;
    }
    foto.append(
      el('span', 'imovel-match', `${imovel.match}% match`),
      el('span', 'imovel-tag', imovel.finalidade === 'aluguel' ? 'Aluguel' : 'Venda'),
    );

    const info = el('div', 'imovel-info');
    const preco = reais(imovel.preco) + (imovel.finalidade === 'aluguel' ? '/mês' : '');
    const dados = [
      imovel.area_m2 ? `${imovel.area_m2} m²` : null,
      imovel.quartos ? `${imovel.quartos} qto${imovel.quartos > 1 ? 's' : ''}` : null,
      imovel.banheiros ? `${imovel.banheiros} banh.` : null,
      imovel.vagas ? `${imovel.vagas} vaga${imovel.vagas > 1 ? 's' : ''}` : null,
    ].filter(Boolean).join(' · ');

    info.append(
      el('div', 'imovel-preco', preco),
      el('div', 'imovel-titulo', imovel.titulo),
      el('div', 'imovel-local', `${imovel.bairro}, ${imovel.cidade}`),
    );
    if (dados) info.appendChild(el('div', 'imovel-dados', dados));

    if (imovel.motivos.length) {
      const motivos = el('div', 'imovel-motivos');
      imovel.motivos.slice(0, 4).forEach((m) => motivos.appendChild(el('span', '', '✓ ' + m)));
      info.appendChild(motivos);
    }

    const acoes = el('div', 'imovel-acoes');
    const interesse = el('button', 'btn btn-solid btn-sm', 'Tenho interesse');
    interesse.type = 'button';
    interesse.addEventListener('click', () => abrirLead(imovel));
    acoes.appendChild(interesse);
    const wa = linkWhatsApp(imovel);
    if (wa) {
      const link = el('a', 'btn btn-sm', 'WhatsApp');
      link.href = wa; link.target = '_blank'; link.rel = 'noopener';
      acoes.appendChild(link);
    }
    info.appendChild(acoes);

    c.append(foto, info);
    return c;
  }

  async function buscar(texto) {
    ultimaBusca = texto;
    balao(texto, 'eu');
    const carregando = digitando();
    botao.disabled = true;

    try {
      const r = await fetch(api('/buscar'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ texto }),
      });
      const dados = await r.json().catch(() => ({}));
      carregando.remove();

      if (!r.ok) {
        balao(typeof dados.detail === 'string' ? dados.detail : 'Não consegui buscar agora. Tente de novo em instantes.', 'ia');
        return;
      }

      const b = balao(dados.mensagem, 'ia');
      if (dados.entendido.length) {
        const entendido = el('div', 'entendido');
        dados.entendido.forEach((t) => entendido.appendChild(el('span', '', t)));
        b.appendChild(el('div', '', '')).style.height = '8px';
        b.appendChild(entendido);
      }

      if (dados.resultados.length) {
        const grade = el('div', 'resultados');
        dados.resultados.forEach((i) => grade.appendChild(cartaoImovel(i)));
        corpo.appendChild(grade);
        // Mostra a resposta e o melhor resultado, não o fim da lista. (scrollIntoView
        // rolaria também a página que contém o iframe.)
        corpo.scrollTo({ top: b.offsetTop - 12, behavior: 'smooth' });
      } else {
        const acoes = el('div', 'exemplos');
        const contato = el('button', '', 'Deixar meu contato');
        contato.type = 'button';
        contato.addEventListener('click', () => abrirLead(null));
        acoes.appendChild(contato);
        corpo.appendChild(acoes);
        rolarParaBaixo();
      }
    } catch {
      carregando.remove();
      balao('Sem conexão no momento. Verifique sua internet e tente de novo.', 'ia');
    } finally {
      botao.disabled = false;
    }
  }

  function abrirLead(imovel) {
    imovelDoLead = imovel;
    $('lead-imovel').textContent = imovel ? `${imovel.titulo} — ${reais(imovel.preco)}` : 'Um corretor vai te ajudar a encontrar o imóvel certo.';
    $('lead-erro').hidden = true;
    $('modal-lead').hidden = false;
    $('form-lead').elements.nome.focus();
  }

  function fecharLead() { $('modal-lead').hidden = true; }

  $('lead-cancelar').addEventListener('click', fecharLead);
  $('modal-lead').addEventListener('click', (e) => { if (e.target.id === 'modal-lead') fecharLead(); });

  $('form-lead').addEventListener('submit', async (e) => {
    e.preventDefault();
    const f = e.target;
    const erro = $('lead-erro');
    const corpoLead = {
      nome: f.elements.nome.value.trim(),
      telefone: f.elements.telefone.value.trim() || null,
      email: f.elements.email.value.trim() || null,
      mensagem: f.elements.mensagem.value.trim(),
      imovel_id: imovelDoLead ? imovelDoLead.id : null,
      busca_texto: ultimaBusca || null,
      aceitou_contato: f.elements.aceitou_contato.checked,
    };
    if (!corpoLead.telefone && !corpoLead.email) {
      erro.textContent = 'Informe um telefone ou e-mail para o corretor falar com você.';
      erro.hidden = false;
      return;
    }

    const enviar = f.querySelector('[type=submit]');
    enviar.disabled = true;
    try {
      const r = await fetch(api('/leads'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(corpoLead),
      });
      const dados = await r.json().catch(() => ({}));
      if (!r.ok) {
        const detalhe = Array.isArray(dados.detail)
          ? 'Confira os dados: ' + dados.detail.map((d) => d.loc.at(-1)).join(', ')
          : dados.detail;
        erro.textContent = detalhe || 'Não foi possível enviar. Tente de novo.';
        erro.hidden = false;
        return;
      }
      fecharLead();
      f.reset();
      balao(dados.mensagem, 'ia');
    } catch {
      erro.textContent = 'Sem conexão. Tente de novo.';
      erro.hidden = false;
    } finally {
      enviar.disabled = false;
    }
  });

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const texto = input.value.trim();
    if (texto.length < 2) return;
    input.value = '';
    buscar(texto);
  });

  if (dentroDeIframe && params.get('modo') === 'widget') {
    $('fechar').hidden = false;
    $('fechar').addEventListener('click', () => window.parent.postMessage({ kazaPro: 'fechar' }, '*'));
  }

  async function iniciar() {
    if (!chave) {
      $('nome-imobiliaria').textContent = 'Widget não configurado';
      form.hidden = true;
      return;
    }
    try {
      const r = await fetch(api('/config'));
      if (!r.ok) throw new Error();
      config = await r.json();
    } catch {
      $('nome-imobiliaria').textContent = 'Busca indisponível';
      balao('Não foi possível carregar a busca desta imobiliária.', 'ia');
      form.hidden = true;
      return;
    }

    document.title = `Busca de imóveis — ${config.nome}`;
    $('nome-imobiliaria').textContent = config.nome;
    document.documentElement.style.setProperty('--cor', config.cor_primaria);
    $('marca').hidden = !config.mostrar_marca;

    const exemplos = $('exemplos');
    config.exemplos.forEach((t) => {
      const b = el('button', '', t);
      b.type = 'button';
      b.addEventListener('click', () => buscar(t));
      exemplos.appendChild(b);
    });
  }

  iniciar();
})();
