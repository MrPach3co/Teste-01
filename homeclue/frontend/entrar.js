// Entrar, criar conta, "esqueci minha senha" e criar nova senha pelo link do e-mail.
(function () {
  const lerToken = () => (location.hash.startsWith('#redefinir=') ? decodeURIComponent(location.hash.slice('#redefinir='.length)) : null);
  let tokenRedefinicao = lerToken();
  if (!tokenRedefinicao && localStorage.getItem('hc_token')) { location.replace('app.html'); return; }

  const telas = {
    login: [document.getElementById('form-login'), document.getElementById('trocar-login')],
    cadastro: [document.getElementById('form-cadastro'), document.getElementById('trocar-cadastro')],
    esqueci: [document.getElementById('form-esqueci'), document.getElementById('trocar-esqueci')],
    redefinir: [document.getElementById('form-redefinir'), document.getElementById('trocar-esqueci')],
  };

  function mostrar(qual) {
    for (const [nome, els] of Object.entries(telas)) {
      if (nome !== qual) els.forEach((e) => { e.hidden = true; });
    }
    telas[qual].forEach((e) => { e.hidden = false; });
    if (qual !== 'redefinir') {
      // O link do e-mail sai da barra de endereço assim que é lido.
      history.replaceState(null, '', qual === 'login' ? location.pathname : `#${qual}`);
    }
    telas[qual][0].querySelector('input').focus();
  }

  document.querySelectorAll('[data-ir]').forEach((b) => b.addEventListener('click', () => mostrar(b.dataset.ir)));

  // Também quando só o "#" muda (link do e-mail colado na aba que já estava no login).
  function aplicarEndereco() {
    const token = lerToken();
    if (token) {
      tokenRedefinicao = token;
      history.replaceState(null, '', location.pathname);
      mostrar('redefinir');
    } else if (['#cadastro', '#esqueci'].includes(location.hash)) {
      mostrar(location.hash.slice(1));
    } else {
      mostrar('login');
    }
  }
  window.addEventListener('hashchange', aplicarEndereco);
  aplicarEndereco();

  function mensagemDeErro(dados) {
    if (typeof dados.detail === 'string') return dados.detail;
    if (Array.isArray(dados.detail)) {
      const campo = dados.detail[0].loc.at(-1);
      const nomes = { email: 'E-mail inválido.', senha: 'A senha precisa ter de 8 a 72 caracteres.',
        nova_senha: 'A senha precisa ter de 8 a 72 caracteres.' };
      return nomes[campo] || 'Confira os campos preenchidos.';
    }
    return 'Algo deu errado. Tente de novo.';
  }

  async function postar(form, url, corpo) {
    const erro = form.querySelector('.aviso-erro');
    const botao = form.querySelector('[type=submit]');
    erro.hidden = true;
    botao.disabled = true;
    try {
      const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(corpo) });
      const dados = await r.json().catch(() => ({}));
      if (!r.ok) {
        erro.textContent = r.status === 429 ? 'Muitas tentativas. Espere um minuto e tente de novo.' : mensagemDeErro(dados);
        erro.hidden = false;
        return null;
      }
      return dados;
    } catch {
      erro.textContent = 'Sem conexão com o servidor.';
      erro.hidden = false;
      return null;
    } finally {
      botao.disabled = false;
    }
  }

  function entrar(dados, destino) {
    localStorage.setItem('hc_token', dados.access_token);
    location.replace(destino);
  }

  telas.login[0].addEventListener('submit', async (e) => {
    e.preventDefault();
    const f = e.target.elements;
    const dados = await postar(e.target, '/api/auth/login', { email: f.email.value.trim(), senha: f.senha.value });
    if (dados) entrar(dados, 'app.html');
  });

  telas.cadastro[0].addEventListener('submit', async (e) => {
    e.preventDefault();
    const f = e.target.elements;
    const dados = await postar(e.target, '/api/auth/cadastro', {
      nome_imobiliaria: f.nome_imobiliaria.value.trim(),
      nome: f.nome.value.trim(),
      email: f.email.value.trim(),
      senha: f.senha.value,
      aceitou_termos: f.aceitou_termos.checked,
    });
    if (dados) entrar(dados, 'app.html#widget');
  });

  telas.esqueci[0].addEventListener('submit', async (e) => {
    e.preventDefault();
    const ok = e.target.querySelector('.aviso-ok');
    ok.hidden = true;
    const dados = await postar(e.target, '/api/auth/esqueci-senha', { email: e.target.elements.email.value.trim() });
    if (dados) { ok.textContent = dados.mensagem; ok.hidden = false; }
  });

  telas.redefinir[0].addEventListener('submit', async (e) => {
    e.preventDefault();
    const f = e.target.elements;
    const erro = e.target.querySelector('.aviso-erro');
    if (f.nova_senha.value !== f.confirmacao.value) {
      erro.textContent = 'As duas senhas não são iguais.';
      erro.hidden = false;
      return;
    }
    const dados = await postar(e.target, '/api/auth/redefinir-senha', { token: tokenRedefinicao, nova_senha: f.nova_senha.value });
    if (dados) entrar(dados, 'app.html');
  });
})();
