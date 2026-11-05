import { el } from '../../comum/util.js';
import { api, avisar, botao, cabecalho, campo, ehDono, entrada, enviarArquivo } from '../nucleo.js';

const data = (iso) => (iso ? new Date(iso + (iso.endsWith('Z') ? '' : 'Z')).toLocaleString('pt-BR') : '—');

export async function render(pagina) {
  const feed = await api('/api/feed');
  pagina.appendChild(cabecalho('Integração por feed XML',
    'A Homeclue lê o mesmo feed XML que o seu sistema já envia para ZAP, VivaReal e OLX. Sem cadastro duplicado: imóvel novo entra, imóvel vendido sai, e tudo se atualiza sozinho a cada 6 horas.'));

  const status = el('div', 'cartao bloco');
  status.appendChild(el('h2', '', 'Situação'));
  if (!feed.url && !feed.status) {
    status.appendChild(el('p', 'ajuda', 'Nenhum feed conectado ainda.'));
  } else {
    const classe = feed.status === 'ok' ? 'aviso-ok' : feed.status === 'erro' ? 'aviso-erro' : 'aviso-info';
    status.appendChild(el('p', `aviso ${classe}`, feed.mensagem || 'Aguardando a primeira sincronização.'));
    const lista = el('ul', 'lista-simples');
    for (const [r, v] of [['Endereço', feed.url || 'arquivo enviado manualmente'], ['Formato reconhecido', feed.formato || '—'],
      ['Imóveis no ar pelo feed', feed.total ?? '—'], ['Última sincronização', data(feed.ultima_sincronizacao)],
      ['Próxima sincronização', feed.url ? data(feed.proxima_sincronizacao) : '—']]) {
      const li = el('li');
      li.append(el('span', '', r), el('small', '', String(v)));
      lista.appendChild(li);
    }
    status.appendChild(lista);
  }
  pagina.appendChild(status);

  if (!ehDono()) {
    pagina.appendChild(el('p', 'ajuda', 'Só o dono da conta pode configurar a integração.'));
    return;
  }

  const recarregar = () => window.dispatchEvent(new HashChangeEvent('hashchange'));
  const form = el('form', 'cartao bloco');
  form.appendChild(el('h2', '', 'Conectar pelo endereço do feed'));
  const url = entrada('url', { type: 'url', valor: feed.url, required: '', placeholder: 'https://seusistema.com.br/xml/sua-imobiliaria.xml' });
  form.append(campo('Endereço (URL) do feed XML', url),
    el('p', 'ajuda', 'Onde achar: no seu sistema imobiliário, procure por “Integração com portais”, “Exportação XML” ou “Feed ZAP/VivaReal”. Se não encontrar, peça ao suporte do sistema “o link do XML que vocês enviam para o ZAP/VivaReal”.'));
  const acoes = el('div', 'acoes');
  const salvar = botao('Salvar e sincronizar', 'btn-solid');
  salvar.type = 'submit';
  acoes.appendChild(salvar);
  if (feed.url) {
    acoes.append(botao('Sincronizar agora', '', async (e) => {
      e.currentTarget.disabled = true;
      try { await api('/api/feed/sincronizar', { method: 'POST' }); avisar('Sincronizado.'); recarregar(); }
      catch (err) { avisar(err.message, 'erro'); recarregar(); }
    }), botao('Desconectar', 'btn-ghost btn-perigo', async () => {
      if (!confirm('Parar de sincronizar? Os imóveis que vieram do feed continuam no ar até você desativá-los.')) return;
      await api('/api/feed', { method: 'DELETE' });
      recarregar();
    }));
  }
  form.appendChild(acoes);
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    salvar.disabled = true;
    salvar.textContent = 'Baixando e lendo o feed…';
    try {
      await api('/api/feed', { method: 'PUT', json: { url: url.value.trim() } });
      avisar('Feed conectado e sincronizado.');
    } catch (err) { avisar(err.message, 'erro'); }
    recarregar();
  });
  pagina.appendChild(form);

  const arquivo = el('div', 'cartao bloco');
  arquivo.appendChild(el('h2', '', 'Ou envie o arquivo XML'));
  arquivo.appendChild(el('p', 'ajuda', 'Para sistemas que só exportam o arquivo, ou para testar antes de conectar o endereço. Aceita .xml e .xml.gz.'));
  const entradaArquivo = entrada('arquivo', { type: 'file', accept: '.xml,.gz,text/xml,application/xml' });
  arquivo.append(entradaArquivo, botao('Enviar e sincronizar', '', async () => {
    if (!entradaArquivo.files[0]) return;
    try { await enviarArquivo('/api/feed/arquivo', entradaArquivo.files[0]); avisar('Arquivo lido e estoque atualizado.'); }
    catch (err) { avisar(err.message, 'erro'); }
    recarregar();
  }));
  pagina.appendChild(arquivo);

  const formatos = el('div', 'cartao bloco');
  formatos.append(el('h2', '', 'Formatos aceitos'), el('p', 'ajuda',
    'VRSync (padrão do Grupo OLX: ZAP, VivaReal e OLX) e o formato “Carga/Imóvel” (padrão ZAP antigo), além de variações com nomes de campos parecidos, que a maioria dos sistemas brasileiros gera. Se o seu feed não for reconhecido, a mensagem acima diz o porquê — mande um exemplo para o suporte que a gente adiciona.'),
    el('p', 'ajuda', 'Segurança: um feed vazio ou ilegível nunca apaga o seu estoque; a sincronização é cancelada e você vê o erro aqui.'));
  pagina.appendChild(formatos);
}
