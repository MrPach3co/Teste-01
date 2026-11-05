/*!
 * Kaza Pro — widget de busca com IA para sites de imobiliária.
 *
 * Uso (botão flutuante):
 *   <script src="https://SEU-DOMINIO/widget.js" data-chave="pk_..." async></script>
 *
 * Uso (embutido numa seção da página):
 *   <div id="busca-imoveis"></div>
 *   <script src="https://SEU-DOMINIO/widget.js" data-chave="pk_..." data-modo="inline"
 *           data-alvo="#busca-imoveis" async></script>
 *
 * A busca roda num iframe servido pelo Kaza Pro, então o CSS do site do
 * cliente não interfere nela (e vice-versa).
 */
(function () {
  var script = document.currentScript;
  if (!script || window.__kazaProCarregado) return;
  window.__kazaProCarregado = true;

  var chave = script.getAttribute('data-chave');
  if (!chave) { console.warn('[Kaza Pro] data-chave ausente no script do widget.'); return; }

  var origem = new URL(script.src).origin;
  var modo = script.getAttribute('data-modo') || 'flutuante';
  var texto = script.getAttribute('data-texto') || 'Buscar imóvel com IA';
  var urlBusca = origem + '/embed.html?k=' + encodeURIComponent(chave);

  function criarIframe(modoIframe) {
    var iframe = document.createElement('iframe');
    iframe.src = urlBusca + '&modo=' + modoIframe;
    iframe.title = 'Busca de imóveis';
    iframe.loading = 'lazy';
    iframe.allow = 'clipboard-write';
    iframe.style.cssText = 'border:0;width:100%;height:100%;display:block;background:#FFFDF9;';
    return iframe;
  }

  if (modo === 'inline') {
    var alvo = document.querySelector(script.getAttribute('data-alvo') || '');
    if (!alvo) { console.warn('[Kaza Pro] data-alvo não encontrado na página.'); return; }
    var caixa = document.createElement('div');
    caixa.style.cssText = 'height:' + (script.getAttribute('data-altura') || '620px') +
      ';border:1px solid #D9D2C2;border-radius:16px;overflow:hidden;';
    caixa.appendChild(criarIframe('inline'));
    alvo.appendChild(caixa);
    return;
  }

  // Modo flutuante: botão no canto + painel. Shadow DOM isola o estilo.
  var host = document.createElement('div');
  host.style.cssText = 'position:fixed;z-index:2147483000;bottom:0;right:0;';
  document.body.appendChild(host);
  var raiz = host.attachShadow ? host.attachShadow({ mode: 'open' }) : host;

  var estilo = document.createElement('style');
  estilo.textContent =
    '.kp-botao{position:fixed;right:20px;bottom:20px;display:flex;align-items:center;gap:8px;' +
    'font:600 15px/1 system-ui,-apple-system,sans-serif;color:#fff;background:var(--kp-cor,#1F3B2C);' +
    'border:0;border-radius:999px;padding:14px 20px;cursor:pointer;box-shadow:0 8px 28px rgba(0,0,0,.22);}' +
    '.kp-botao:hover{filter:brightness(1.08);}' +
    '.kp-painel{position:fixed;right:20px;bottom:84px;width:420px;height:min(680px,calc(100vh - 110px));' +
    'border-radius:18px;overflow:hidden;background:#FFFDF9;box-shadow:0 18px 60px rgba(0,0,0,.28);display:none;}' +
    '.kp-painel.aberto{display:block;}' +
    '@media (max-width:520px){.kp-painel{right:0;bottom:0;width:100vw;height:100dvh;border-radius:0;}' +
    '.kp-painel.aberto + .kp-botao{display:none;}}';
  raiz.appendChild(estilo);

  var painel = document.createElement('div');
  painel.className = 'kp-painel';
  painel.setAttribute('role', 'dialog');
  painel.setAttribute('aria-label', 'Busca de imóveis');

  var botao = document.createElement('button');
  botao.className = 'kp-botao';
  botao.type = 'button';
  botao.setAttribute('aria-expanded', 'false');
  botao.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>';
  botao.appendChild(document.createTextNode(texto));

  raiz.appendChild(painel);
  raiz.appendChild(botao);

  var carregado = false;
  function alternar(abrir) {
    if (abrir && !carregado) { painel.appendChild(criarIframe('widget')); carregado = true; }
    painel.classList.toggle('aberto', abrir);
    botao.setAttribute('aria-expanded', String(abrir));
  }
  botao.addEventListener('click', function () { alternar(!painel.classList.contains('aberto')); });

  window.addEventListener('message', function (e) {
    if (e.origin === origem && e.data && e.data.kazaPro === 'fechar') alternar(false);
  });

  // Puxa a cor da marca da imobiliária para o botão.
  fetch(origem + '/api/publico/' + encodeURIComponent(chave) + '/config')
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (c) { if (c && /^#[0-9a-f]{6}$/i.test(c.cor_primaria)) host.style.setProperty('--kp-cor', c.cor_primaria); })
    .catch(function () {});
})();
