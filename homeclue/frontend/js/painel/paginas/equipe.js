import { el } from '../../comum/util.js';
import { api, avisar, botao, cabecalho, campo, ehDono, entrada } from '../nucleo.js';

export async function render(pagina) {
  const recarregar = () => window.dispatchEvent(new HashChangeEvent('hashchange'));
  pagina.appendChild(cabecalho('Equipe', 'Corretores com acesso ao painel. Quando um corretor é o responsável por um imóvel, os leads do WhatsApp daquele imóvel vão direto para o número dele.'));
  const pessoas = await api('/api/equipe');
  const colunas = el('div', 'duas-colunas');
  const lista = el('div', 'cartao bloco');
  lista.appendChild(el('h2', '', 'Pessoas'));
  for (const p of pessoas) {
    const linha = el('form', 'pilha');
    linha.style.borderBottom = '1px solid var(--concreto-alt)';
    linha.style.paddingBottom = '12px';
    linha.appendChild(el('strong', '', `${p.nome} · ${p.papel === 'dono' ? 'Dono da conta' : 'Corretor'}`));
    linha.appendChild(el('span', 'ajuda', p.email));
    const whatsapp = entrada('whatsapp', { type: 'tel', valor: p.whatsapp, placeholder: 'WhatsApp com DDD' });
    const acoes = el('div', 'acoes');
    if (ehDono()) {
      const salvar = botao('Salvar WhatsApp', 'btn-sm');
      salvar.type = 'submit';
      acoes.appendChild(salvar);
      if (p.papel !== 'dono') {
        acoes.appendChild(botao('Remover', 'btn-sm btn-ghost btn-perigo', async () => {
          if (!confirm(`Remover ${p.nome} da equipe?`)) return;
          try { await api(`/api/equipe/${p.id}`, { method: 'DELETE' }); recarregar(); } catch (e) { avisar(e.message, 'erro'); }
        }));
      }
      linha.append(whatsapp, acoes);
      linha.addEventListener('submit', async (e) => {
        e.preventDefault();
        try { await api(`/api/equipe/${p.id}`, { method: 'PATCH', json: { whatsapp: whatsapp.value.trim() } }); avisar('WhatsApp salvo.'); }
        catch (err) { avisar(err.message, 'erro'); }
      });
    } else if (p.whatsapp) {
      linha.appendChild(el('span', 'ajuda', `WhatsApp: ${p.whatsapp}`));
    }
    lista.appendChild(linha);
  }
  colunas.appendChild(lista);
  if (ehDono()) {
    const form = el('form', 'cartao bloco');
    form.appendChild(el('h2', '', 'Adicionar corretor'));
    const nome = entrada('nome', { required: '', minlength: 2 });
    const email = entrada('email', { type: 'email', required: '' });
    const whatsapp = entrada('whatsapp', { type: 'tel', placeholder: 'Opcional' });
    const resultado = el('div', 'aviso');
    resultado.hidden = true;
    const enviar = botao('Adicionar', 'btn-solid');
    enviar.type = 'submit';
    form.append(campo('Nome', nome), campo('E-mail', email), campo('WhatsApp', whatsapp), resultado, enviar);
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      try {
        const r = await api('/api/equipe', { method: 'POST', json: { nome: nome.value.trim(), email: email.value.trim(), whatsapp: whatsapp.value.trim() || null } });
        resultado.className = 'aviso aviso-ok';
        resultado.replaceChildren(document.createTextNode(`${r.usuario.nome} foi adicionado. Envie a senha temporária para ele: `),
          el('strong', '', r.senha_temporaria), document.createTextNode(' — ela não aparece de novo. Peça para trocar em “Minha conta”.'));
        form.reset();
      } catch (err) { resultado.className = 'aviso aviso-erro'; resultado.textContent = err.message; }
      resultado.hidden = false;
    });
    colunas.appendChild(form);
  }
  pagina.appendChild(colunas);
}
