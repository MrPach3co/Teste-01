import { el } from '../../comum/util.js';
import { api, avisar, botao, cabecalho, campo, ehDono, entrada, enviarArquivo, estado, temRecurso } from '../nucleo.js';
import { recarregarSessao } from '../main.js';

function blocoCodigo(titulo, ajuda, texto, rotuloCopiar = 'Copiar código') {
  const c = el('div', 'cartao bloco');
  const pre = el('pre', 'codigo-bloco', texto);
  const copiar = botao(rotuloCopiar, 'btn-sm', async () => {
    try { await navigator.clipboard.writeText(texto); copiar.textContent = 'Copiado ✓'; setTimeout(() => { copiar.textContent = rotuloCopiar; }, 1600); }
    catch { avisar('Selecione o texto e copie manualmente.', 'info'); }
  });
  c.append(el('h2', '', titulo), el('p', 'ajuda', ajuda), pre, copiar);
  return c;
}

export async function render(pagina) {
  const imob = estado.sessao.imobiliaria;
  const origem = location.origin;
  const link = `${origem}/embed.html?k=${encodeURIComponent(imob.chave_publica)}`;
  pagina.appendChild(cabecalho('Widget no site', 'Uma linha de código no seu site, com o seu logo e as suas cores. A marca continua sendo a sua.'));
  const colunas = el('div', 'duas-colunas');
  const esquerda = el('div', 'pilha');
  esquerda.append(
    blocoCodigo('1. Botão flutuante (recomendado)', 'Cole antes de </body> em todas as páginas. Aparece um botão “Buscar imóvel com IA” no canto da tela.',
      `<script src="${origem}/widget.js" data-chave="${imob.chave_publica}" async></script>`),
    blocoCodigo('2. Embutido numa página', 'Para uma página “Encontre seu imóvel”: a busca aparece dentro do conteúdo.',
      `<div id="busca-imoveis"></div>\n<script src="${origem}/widget.js" data-chave="${imob.chave_publica}" data-modo="inline" data-alvo="#busca-imoveis" async></script>`),
    blocoCodigo('3. Link direto', 'Sem site? Use na bio do Instagram, no Google Meu Negócio ou mande no WhatsApp.', link, 'Copiar link'),
  );

  if (ehDono()) {
    const aparencia = el('form', 'cartao bloco');
    aparencia.appendChild(el('h2', '', 'Aparência e contato'));
    const nome = entrada('nome', { valor: imob.nome, required: '', minlength: 2 });
    const cor = entrada('cor', { type: 'color', valor: imob.cor_primaria });
    const whatsapp = entrada('whatsapp', { type: 'tel', valor: imob.whatsapp, placeholder: '+55 22 99999-0000' });
    const salvar = botao('Salvar', 'btn-solid');
    salvar.type = 'submit';
    aparencia.append(campo('Nome exibido', nome), campo('Cor da marca', cor),
      campo('WhatsApp da imobiliária (recebe os leads quando o imóvel não tem corretor responsável)', whatsapp), salvar);
    aparencia.addEventListener('submit', async (e) => {
      e.preventDefault();
      try {
        await api('/api/imobiliaria', { method: 'PATCH', json: { nome: nome.value.trim(), cor_primaria: cor.value, whatsapp: whatsapp.value.trim() } });
        await recarregarSessao();
        avisar('Aparência salva.');
        window.dispatchEvent(new HashChangeEvent('hashchange'));
      } catch (err) { avisar(err.message, 'erro'); }
    });

    const logo = el('div', 'cartao bloco');
    logo.appendChild(el('h2', '', 'Logo'));
    if (imob.logo_url) { const img = el('img', 'logo-atual'); img.src = imob.logo_url; img.alt = 'Logo atual'; logo.appendChild(img); }
    const arquivo = el('input');
    arquivo.type = 'file'; arquivo.accept = 'image/png,image/jpeg,image/webp'; arquivo.hidden = true;
    arquivo.addEventListener('change', async () => {
      if (!arquivo.files[0]) return;
      try { await enviarArquivo('/api/imobiliaria/logo', arquivo.files[0]); await recarregarSessao(); avisar('Logo atualizado.'); window.dispatchEvent(new HashChangeEvent('hashchange')); }
      catch (err) { avisar(err.message, 'erro'); }
    });
    const linhaLogo = el('div', 'acoes');
    linhaLogo.append(arquivo, botao(imob.logo_url ? 'Trocar logo' : 'Enviar logo', 'btn-sm', () => arquivo.click()));
    if (imob.logo_url) linhaLogo.appendChild(botao('Remover', 'btn-sm btn-ghost btn-perigo', async () => { await api('/api/imobiliaria/logo', { method: 'DELETE' }); await recarregarSessao(); window.dispatchEvent(new HashChangeEvent('hashchange')); }));
    logo.append(el('p', 'ajuda', 'PNG com fundo transparente fica melhor. Ele aparece no topo da busca.'), linhaLogo);

    const fotos = el('div', 'cartao bloco');
    fotos.appendChild(el('h2', '', 'Inteligência das fotos'));
    if (!temRecurso('analise_fotos')) {
      fotos.appendChild(el('p', 'ajuda', 'No Premium, a IA olha as fotos dos anúncios para achar o que o texto não diz (ex.: lareira, piscina). Aparece para o comprador como “parece ter, pela foto”, com a foto ao lado.'));
    } else if (!estado.sessao.ia_ativa) {
      fotos.appendChild(el('p', 'ajuda', 'A IA ainda não foi configurada nesta instalação.'));
    } else {
      const rotulo = el('label', 'check');
      const cx = el('input');
      cx.type = 'checkbox';
      cx.checked = imob.analisar_fotos;
      rotulo.append(cx, el('span', '', 'Analisar as fotos dos anúncios com IA (custo por anúncio analisado; o resultado aparece como indício, nunca como fato)'));
      cx.addEventListener('change', async () => {
        try { await api('/api/imobiliaria', { method: 'PATCH', json: { analisar_fotos: cx.checked } }); await recarregarSessao(); avisar(cx.checked ? 'Análise de fotos ligada.' : 'Análise de fotos desligada.'); }
        catch (err) { avisar(err.message, 'erro'); }
      });
      fotos.appendChild(rotulo);
    }

    const chave = el('div', 'cartao bloco');
    chave.append(el('h2', '', 'Chave do widget'), el('p', 'ajuda', 'Gere uma nova se alguém estiver usando sua chave em outro site. O código antigo para de funcionar.'),
      botao('Gerar nova chave', 'btn-sm btn-perigo', async () => {
        if (!confirm('Gerar uma nova chave? O código instalado no seu site para de funcionar até você trocar pelo novo.')) return;
        await api('/api/imobiliaria/regenerar-chave', { method: 'POST' }); await recarregarSessao(); avisar('Nova chave gerada. Atualize o código no seu site.');
        window.dispatchEvent(new HashChangeEvent('hashchange'));
      }));
    esquerda.append(aparencia, logo, fotos, chave);
  }

  const previa = el('div', 'previa');
  const quadro = el('iframe');
  quadro.src = link;
  quadro.title = 'Pré-visualização do widget';
  quadro.allow = 'microphone';
  previa.append(el('div', 'previa-rotulo', 'Pré-visualização — é exatamente o que o cliente vê'), quadro);
  colunas.append(esquerda, previa);
  pagina.appendChild(colunas);
}
