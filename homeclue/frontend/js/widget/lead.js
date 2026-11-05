// Formulário de contato (para quem prefere não usar o WhatsApp).
import { estado, pedir } from './estado.js';

const $ = (id) => document.getElementById(id);
let contexto = {};
let aoEnviar = null;

export function abrirLead({ imovelId = null, unidadeId = null, sobre = '' } = {}, depois) {
  contexto = { imovelId, unidadeId };
  aoEnviar = depois;
  $('lead-sobre').textContent = sobre || 'Um corretor vai te ajudar a encontrar o imóvel certo.';
  $('lead-erro').hidden = true;
  $('modal-lead').hidden = false;
  $('form-lead').elements.nome.focus();
}

function fechar() { $('modal-lead').hidden = true; }

$('lead-cancelar').addEventListener('click', fechar);
$('modal-lead').addEventListener('click', (e) => { if (e.target.id === 'modal-lead') fechar(); });

$('form-lead').addEventListener('submit', async (e) => {
  e.preventDefault();
  const f = e.target;
  const erro = $('lead-erro');
  const corpo = {
    nome: f.elements.nome.value.trim(),
    telefone: f.elements.telefone.value.trim() || null,
    email: f.elements.email.value.trim() || null,
    mensagem: f.elements.mensagem.value.trim(),
    imovel_id: contexto.imovelId,
    unidade_id: contexto.unidadeId,
    busca_id: estado.buscaId,
    sessao: estado.sessao,
    aceitou_contato: f.elements.aceitou_contato.checked,
  };
  if (!corpo.telefone && !corpo.email) {
    erro.textContent = 'Informe um telefone ou e-mail para o corretor falar com você.';
    erro.hidden = false;
    return;
  }
  const botao = f.querySelector('[type=submit]');
  botao.disabled = true;
  try {
    const r = await pedir('/leads', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(corpo) });
    fechar();
    f.reset();
    if (aoEnviar) aoEnviar(`${r.mensagem} (protocolo ${r.codigo})`);
  } catch (err) {
    const detalhe = err.dados && Array.isArray(err.dados.detail)
      ? 'Confira os dados: ' + err.dados.detail.map((d) => d.loc.at(-1)).join(', ')
      : err.message;
    erro.textContent = detalhe;
    erro.hidden = false;
  } finally {
    botao.disabled = false;
  }
});
