import { el } from '../../comum/util.js';
import { api, avisar, baixar, botao, cabecalho, campo, ehDono, entrada, estado, sair } from '../nucleo.js';
import { recarregarSessao } from '../main.js';

export async function render(pagina) {
  const u = estado.sessao.usuario;
  pagina.appendChild(cabecalho('Minha conta'));
  const colunas = el('div', 'duas-colunas');

  const perfil = el('form', 'cartao bloco');
  const nome = entrada('nome', { valor: u.nome, required: '', minlength: 2 });
  const whatsapp = entrada('whatsapp', { type: 'tel', valor: u.whatsapp, placeholder: 'Para receber os leads dos seus imóveis' });
  const salvar = botao('Salvar', 'btn-solid');
  salvar.type = 'submit';
  perfil.append(el('h2', '', 'Perfil'), campo('Nome', nome), campo('Seu WhatsApp', whatsapp), salvar);
  perfil.addEventListener('submit', async (e) => {
    e.preventDefault();
    try { await api('/api/auth/perfil', { method: 'PATCH', json: { nome: nome.value.trim(), whatsapp: whatsapp.value.trim() } }); await recarregarSessao(); avisar('Perfil salvo.'); }
    catch (err) { avisar(err.message, 'erro'); }
  });

  const senha = el('form', 'cartao bloco');
  const atual = entrada('senha_atual', { type: 'password', required: '', autocomplete: 'current-password' });
  const nova = entrada('nova_senha', { type: 'password', required: '', minlength: 8, maxlength: 72, autocomplete: 'new-password' });
  const trocar = botao('Salvar nova senha', 'btn-solid');
  trocar.type = 'submit';
  senha.append(el('h2', '', 'Trocar senha'), campo('Senha atual', atual), campo('Nova senha (mínimo 8)', nova), trocar);
  senha.addEventListener('submit', async (e) => {
    e.preventDefault();
    try { await api('/api/auth/trocar-senha', { method: 'POST', json: { senha_atual: atual.value, nova_senha: nova.value } }); senha.reset(); avisar('Senha alterada.'); }
    catch (err) { avisar(err.message, 'erro'); }
  });

  const lgpd = el('div', 'cartao bloco');
  lgpd.append(el('h2', '', 'Seus dados (LGPD)'), el('p', 'ajuda', ehDono()
    ? 'Como dono, excluir a conta apaga a imobiliária inteira: imóveis, leads, equipe e arquivos.' : 'Baixe uma cópia dos seus dados ou exclua seu acesso.'),
  botao('Baixar meus dados', '', async () => {
    const dados = await api('/api/auth/meus-dados');
    baixar(new Blob([JSON.stringify(dados, null, 2)], { type: 'application/json' }), 'meus-dados-homeclue.json');
  }),
  botao('Excluir minha conta', 'btn-perigo', async () => {
    if (prompt('Digite EXCLUIR para confirmar.') !== 'EXCLUIR') return;
    try { await api('/api/auth/minha-conta', { method: 'DELETE' }); sair(); } catch (e) { avisar(e.message, 'erro'); }
  }));
  colunas.append(perfil, senha, lgpd);
  pagina.appendChild(colunas);
}
