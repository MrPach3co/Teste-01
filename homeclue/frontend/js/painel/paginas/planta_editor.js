// Editor de planta: a imobiliária envia a imagem da planta e desenha os
// cômodos por cima (arrastar para criar, mover e redimensionar). Cada cômodo
// recebe tipo, nome, área, observações e fotos — é daí que saem a planta
// interativa e a maquete 3D do widget.
import { montarMaquete } from '../../comum/maquete3d.js';
import { el } from '../../comum/util.js';
import { abrirModal, api, avisar, botao, campo, entrada, enviarArquivo, garantirVocabulario, selecao } from '../nucleo.js';

const MINIMO = 0.02;

export async function abrirEditorPlanta(imovel, aoSalvar) {
  const v = await garantirVocabulario();
  const tipos = v.tipos_comodo;
  const planta = {
    imagem: (imovel.planta && imovel.planta.imagem) || null,
    comodos: JSON.parse(JSON.stringify((imovel.planta && imovel.planta.comodos) || [])),
  };
  let selecionado = null;
  let maquete = null;
  const { dialogo, conteudo, rodape, fechar } = abrirModal(`Planta — ${imovel.titulo}`, { largo: true });
  dialogo.addEventListener('close', () => { if (maquete) { maquete.destruir(); maquete = null; } }, { once: true });

  const ajudaTopo = el('p', 'ajuda', 'Arraste sobre a planta para criar um cômodo. Clique num cômodo para editar; arraste para mover e use o canto laranja para redimensionar.');
  const enviar = el('input');
  enviar.type = 'file'; enviar.accept = 'image/*'; enviar.hidden = true;
  const linhaImagem = el('div', 'acoes');
  linhaImagem.append(botao(planta.imagem ? 'Trocar imagem da planta' : 'Enviar imagem da planta', 'btn-sm', () => enviar.click()), enviar);

  const palco = el('div', 'palco-planta');
  const img = el('img');
  img.alt = 'Planta do imóvel';
  palco.appendChild(img);
  const lado = el('div', 'pilha');
  const lista = el('ul', 'lista-comodos');
  const formulario = el('div', 'pilha');
  const editor = el('div', 'editor-planta');
  editor.append(palco, lado);
  lado.append(el('strong', '', 'Cômodos'), lista, formulario);
  const vista3d = el('div', 'palco-3d');
  vista3d.hidden = true;
  conteudo.append(ajudaTopo, linhaImagem, editor, vista3d);

  enviar.addEventListener('change', async () => {
    const arquivo = enviar.files[0];
    enviar.value = '';
    if (!arquivo) return;
    try {
      const r = await enviarArquivo(`/api/imoveis/${imovel.id}/planta/imagem`, arquivo);
      planta.imagem = r.url;
      img.src = r.url;
      avisar('Planta enviada. Agora desenhe os cômodos.');
    } catch (e) { avisar(e.message, 'erro'); }
  });

  const fotosDoImovel = (imovel.fotos || []).map((f) => f.url);

  function desenhar() {
    palco.querySelectorAll('.ret').forEach((r) => r.remove());
    for (const c of planta.comodos) {
      const r = el('div', `ret${c === selecionado ? ' selecionado' : ''}`);
      Object.assign(r.style, { left: `${c.x * 100}%`, top: `${c.y * 100}%`, width: `${c.w * 100}%`, height: `${c.h * 100}%` });
      r.appendChild(el('span', '', c.nome || tipos[c.tipo]));
      if (c === selecionado) r.appendChild(el('i', 'alca'));
      r.addEventListener('pointerdown', (e) => iniciarArraste(e, c, e.target.classList.contains('alca') ? 'redimensionar' : 'mover'));
      palco.appendChild(r);
    }
    lista.replaceChildren();
    planta.comodos.forEach((c) => {
      const li = el('li');
      const b = botao(`${c.nome || tipos[c.tipo]}${c.area_m2 ? ` · ${c.area_m2} m²` : ''}`, c === selecionado ? 'ativo' : '', () => { selecionado = c; desenhar(); });
      li.appendChild(b);
      lista.appendChild(li);
    });
    if (!planta.comodos.length) lista.appendChild(el('li', 'ajuda', 'Nenhum cômodo ainda.'));
    desenharFormulario();
  }

  function desenharFormulario() {
    formulario.replaceChildren();
    if (!selecionado) return;
    const c = selecionado;
    const tipo = selecao('tipo', Object.entries(tipos), c.tipo);
    tipo.addEventListener('change', () => { c.tipo = tipo.value; desenhar(); });
    const nome = entrada('nome', { valor: c.nome, maxlength: 60, placeholder: tipos[c.tipo] });
    nome.addEventListener('input', () => { c.nome = nome.value; palco.querySelector('.ret.selecionado span').textContent = c.nome || tipos[c.tipo]; });
    const area = entrada('area', { type: 'number', min: 0.5, step: 0.5, valor: c.area_m2 });
    area.addEventListener('input', () => { c.area_m2 = area.value ? Number(area.value) : null; });
    const notas = entrada('notas', { tag: 'textarea', rows: 2, maxlength: 300, valor: c.notas, placeholder: 'Ex.: sol da manhã, lareira, vista para a serra' });
    notas.addEventListener('input', () => { c.notas = notas.value; });
    formulario.append(campo('Tipo', tipo), campo('Nome', nome), campo('Área (m²)', area),
      campo('Observações (o comprador vê; a busca usa como prova)', notas));
    if (fotosDoImovel.length) {
      const escolha = el('div', 'escolher-fotos');
      for (const url of fotosDoImovel) {
        const l = el('label');
        l.style.backgroundImage = `url("${encodeURI(url)}")`;
        const cx = el('input');
        cx.type = 'checkbox';
        cx.checked = (c.fotos || []).includes(url);
        cx.setAttribute('aria-label', 'Usar esta foto neste cômodo');
        cx.addEventListener('change', () => {
          c.fotos = c.fotos || [];
          if (cx.checked) c.fotos.push(url); else c.fotos = c.fotos.filter((u) => u !== url);
        });
        l.appendChild(cx);
        escolha.appendChild(l);
      }
      formulario.append(el('span', 'ajuda', 'Fotos deste cômodo:'), escolha);
    }
    const nova = el('input');
    nova.type = 'file'; nova.accept = 'image/*'; nova.hidden = true;
    nova.addEventListener('change', async () => {
      const arquivo = nova.files[0];
      nova.value = '';
      if (!arquivo) return;
      try {
        const r = await enviarArquivo(`/api/imoveis/${imovel.id}/fotos`, arquivo);
        c.fotos = [...(c.fotos || []), r.url];
        fotosDoImovel.push(r.url);
        desenharFormulario();
      } catch (e) { avisar(e.message, 'erro'); }
    });
    formulario.append(nova, botao('Enviar foto deste cômodo', 'btn-sm', () => nova.click()),
      botao('Excluir cômodo', 'btn-sm btn-perigo', () => {
        planta.comodos = planta.comodos.filter((x) => x !== c);
        selecionado = null;
        desenhar();
      }));
  }

  function posicao(e) {
    const r = palco.getBoundingClientRect();
    return [Math.min(1, Math.max(0, (e.clientX - r.left) / r.width)), Math.min(1, Math.max(0, (e.clientY - r.top) / r.height))];
  }

  function iniciarArraste(e, comodo, modo) {
    e.stopPropagation();
    e.preventDefault();
    selecionado = comodo;
    const [x0, y0] = posicao(e);
    const original = { ...comodo };
    const mover = (ev) => {
      const [x, y] = posicao(ev);
      if (modo === 'mover') {
        comodo.x = Math.min(1 - comodo.w, Math.max(0, original.x + x - x0));
        comodo.y = Math.min(1 - comodo.h, Math.max(0, original.y + y - y0));
      } else {
        comodo.w = Math.min(1 - comodo.x, Math.max(MINIMO, original.w + x - x0));
        comodo.h = Math.min(1 - comodo.y, Math.max(MINIMO, original.h + y - y0));
      }
      desenhar();
    };
    const soltar = () => { window.removeEventListener('pointermove', mover); window.removeEventListener('pointerup', soltar); desenhar(); };
    window.addEventListener('pointermove', mover);
    window.addEventListener('pointerup', soltar);
    desenhar();
  }

  palco.addEventListener('pointerdown', (e) => {
    if (!planta.imagem || e.target !== palco) return;
    const [x0, y0] = posicao(e);
    const novo = { id: `c${Date.now().toString(36)}`, tipo: 'sala', nome: '', x: x0, y: y0, w: MINIMO, h: MINIMO, area_m2: null, notas: '', fotos: [] };
    planta.comodos.push(novo);
    selecionado = novo;
    const mover = (ev) => {
      const [x, y] = posicao(ev);
      novo.x = Math.min(x0, x); novo.y = Math.min(y0, y);
      novo.w = Math.max(MINIMO, Math.abs(x - x0)); novo.h = Math.max(MINIMO, Math.abs(y - y0));
      desenhar();
    };
    const soltar = () => {
      window.removeEventListener('pointermove', mover);
      window.removeEventListener('pointerup', soltar);
      if (novo.w <= MINIMO && novo.h <= MINIMO) { novo.w = 0.12; novo.h = 0.12; novo.x = Math.min(novo.x, 0.88); novo.y = Math.min(novo.y, 0.88); }
      desenhar();
    };
    window.addEventListener('pointermove', mover);
    window.addEventListener('pointerup', soltar);
  });

  if (planta.imagem) img.src = planta.imagem;
  desenhar();

  const arredondar = (c) => ({ ...c, x: +c.x.toFixed(4), y: +c.y.toFixed(4), w: +Math.min(c.w, 1 - c.x).toFixed(4), h: +Math.min(c.h, 1 - c.y).toFixed(4) });

  rodape.append(
    botao('Ver maquete 3D', '', async () => {
      if (planta.comodos.length < 2) { avisar('Desenhe pelo menos 2 cômodos para gerar a maquete.', 'info'); return; }
      vista3d.hidden = false;
      if (maquete) maquete.destruir();
      const aspecto = img.naturalWidth && img.naturalHeight ? img.naturalWidth / img.naturalHeight : 1.4;
      maquete = await montarMaquete(vista3d, { comodos: planta.comodos, aspecto, area_m2: imovel.area_m2 }, { tipos });
      vista3d.scrollIntoView({ behavior: 'smooth' });
    }),
    botao('Cancelar', 'btn-ghost', fechar),
    botao('Salvar planta', 'btn-solid', async () => {
      try {
        await api(`/api/imoveis/${imovel.id}/planta`, { method: 'PUT', json: { imagem: planta.imagem, comodos: planta.comodos.map(arredondar) } });
        avisar('Planta salva. Ela já aparece no widget, com os cômodos destacados conforme a busca.');
        fechar();
        if (aoSalvar) aoSalvar();
      } catch (e) { avisar(e.message, 'erro'); }
    }),
  );

}
