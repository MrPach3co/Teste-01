// Detalhe do imóvel: fotos, dados, o porquê do match, planta interativa,
// maquete 3D, vídeo/drone, contexto do bairro e contato.
import { montarMaquete } from '../comum/maquete3d.js';
import { cartaoComodo, comodosDestacados, desenharPlanta } from '../comum/planta.js';
import { ROTULO_FONTE, distancia, el, gradiente, precoDoImovel, reais, urlDeEmbed } from '../comum/util.js';
import { listaDePontos, resumoDosPontos } from './cartoes.js';
import { abrirCamada, estado, fecharCamada, linkWhatsApp, pedir, registrarEvento } from './estado.js';

const camada = document.getElementById('camada-detalhe');
let maquete = null;

function secao(titulo) {
  const s = el('section', 'camada-secao');
  if (titulo) s.appendChild(el('h3', '', titulo));
  return s;
}

function galeria(d) {
  const g = el('div', 'galeria');
  if (!d.fotos.length) {
    const vazio = el('div', 'sem-foto', 'Sem fotos neste anúncio');
    vazio.style.backgroundImage = gradiente(d.id);
    g.appendChild(vazio);
    return [g];
  }
  d.fotos.forEach((f, i) => {
    const img = el('img');
    img.src = f.url;
    img.alt = f.legenda || `Foto ${i + 1} de ${d.titulo}`;
    img.loading = i === 0 ? 'eager' : 'lazy';
    g.appendChild(img);
  });
  return [g, el('p', 'galeria-conta', `${d.fotos.length} foto${d.fotos.length > 1 ? 's' : ''} — deslize para o lado`)];
}

function fatos(d) {
  const lista = el('dl', 'fatos');
  const itens = [
    ['Quartos', d.quartos], ['Suítes', d.suites], ['Banheiros', d.banheiros], ['Vagas', d.vagas],
    ['Área', d.area_m2 ? `${d.area_m2} m²` : null], ['Terreno', d.area_terreno ? `${d.area_terreno.toLocaleString('pt-BR')} m²` : null],
    ['Condomínio', d.condominio ? reais(d.condominio) : null], ['IPTU/ano', d.iptu ? reais(d.iptu) : null],
    ['Código', d.codigo_referencia],
  ];
  for (const [rotulo, valor] of itens) {
    if (valor === null || valor === undefined || valor === '') continue;
    const item = el('div');
    item.append(el('dt', '', rotulo), el('dd', '', String(valor)));
    lista.appendChild(item);
  }
  return lista;
}

function blocoPlanta(d, s) {
  const tipos = d.planta.tipos || {};
  const destaques = comodosDestacados(d.planta.comodos, estado.criterios);
  const alternador = el('div', 'alternador');
  const b2d = el('button', '', 'Planta');
  const b3d = el('button', '', 'Maquete 3D');
  b2d.type = b3d.type = 'button';
  b2d.setAttribute('aria-pressed', 'true');
  b3d.setAttribute('aria-pressed', 'false');
  const palco = el('div');
  const info = el('div');
  const legenda = el('p', 'legenda-3d');
  const mostrarComodo = (c) => info.replaceChildren(cartaoComodo(c, tipos, destaques.get(c.id)));

  const desenhar2D = () => {
    if (maquete) { maquete.destruir(); maquete = null; }
    palco.className = '';
    desenharPlanta(palco, d.planta, { destaques, tipos, aoClicar: mostrarComodo });
    legenda.textContent = destaques.size
      ? 'Em destaque: os cômodos que combinam com o que você pediu. Toque num cômodo para ver detalhes e fotos.'
      : 'Toque num cômodo para ver detalhes e fotos.';
  };
  const desenhar3D = async () => {
    palco.className = 'palco-3d';
    palco.replaceChildren(el('p', 'aviso-3d', 'Montando a maquete…'));
    const img = new Image();
    img.src = d.planta.imagem;
    await img.decode().catch(() => {});
    const aspecto = img.naturalWidth && img.naturalHeight ? img.naturalWidth / img.naturalHeight : 1.4;
    maquete = await montarMaquete(palco, { comodos: d.planta.comodos, aspecto, area_m2: d.area_para_maquete },
      { destaques, tipos, aoClicar: mostrarComodo });
    legenda.textContent = 'Maquete gerada a partir da planta (esquemática, fora de escala exata). Arraste para girar; toque num cômodo para ver as fotos.';
    registrarEvento('maquete', d.id);
  };
  b2d.addEventListener('click', () => { b2d.setAttribute('aria-pressed', 'true'); b3d.setAttribute('aria-pressed', 'false'); desenhar2D(); });
  b3d.addEventListener('click', () => { b3d.setAttribute('aria-pressed', 'true'); b2d.setAttribute('aria-pressed', 'false'); desenhar3D(); });
  alternador.append(b2d);
  if (d.maquete) alternador.append(b3d);
  s.append(alternador, palco, legenda, info);
  desenhar2D();
  registrarEvento('planta', d.id);
}

function blocoContexto(contexto) {
  const s = secao('O que tem por perto');
  const grade = el('div', 'contexto');
  for (const cat of Object.values(contexto.categorias)) {
    const caixa = el('div', 'contexto-cat');
    caixa.appendChild(el('strong', '', cat.rotulo));
    if (!cat.mais_proximos.length) {
      caixa.appendChild(el('span', 'fonte', `Nada mapeado em até ${distancia(cat.raio_m)}`));
    } else {
      const lista = el('ul');
      for (const p of cat.mais_proximos) lista.appendChild(el('li', '', `${p.nome} — ${distancia(p.distancia_m)}`));
      caixa.appendChild(lista);
    }
    grade.appendChild(caixa);
  }
  s.append(grade, el('p', 'fonte', `${contexto.aproximado ? 'Distâncias aproximadas (a partir do bairro). ' : ''}Dados ${contexto.fonte}. O mapa pode estar incompleto.`));
  return s;
}

export async function abrirDetalhe(id, { aoContato }) {
  const resultado = estado.resultados.get(id);
  camada.replaceChildren();
  const topo = el('div', 'camada-topo');
  const voltar = el('button', 'btn btn-ghost btn-sm', '← Voltar');
  voltar.type = 'button';
  voltar.addEventListener('click', fecharCamada);
  topo.append(voltar, el('h2', '', resultado ? resultado.titulo : 'Imóvel'));
  const corpo = el('div', 'camada-corpo');
  corpo.appendChild(el('p', 'camada-secao', 'Carregando…'));
  camada.append(topo, corpo);
  abrirCamada(camada, () => { if (maquete) { maquete.destruir(); maquete = null; } });

  let d;
  try {
    d = await pedir(`/imoveis/${id}?sessao=${encodeURIComponent(estado.sessao)}`);
  } catch (erro) {
    corpo.replaceChildren(el('p', 'camada-secao', erro.message));
    return;
  }
  corpo.replaceChildren(...galeria(d));

  const principal = secao();
  const preco = precoDoImovel(d, estado.criterios && estado.criterios.finalidade);
  principal.append(
    el('div', 'detalhe-preco', reais(preco.valor) + (preco.aluguel ? '/mês' : '')),
    el('h3', '', d.titulo),
    el('p', 'imovel-local', [d.endereco, d.bairro, d.cidade].filter(Boolean).join(', ')),
    fatos(d),
  );
  if (d.finalidade === 'venda_aluguel' && d.preco_aluguel) principal.appendChild(el('p', 'imovel-dados', `Também para alugar: ${reais(d.preco_aluguel)}/mês`));
  corpo.appendChild(principal);

  if (resultado && resultado.pontos.length) {
    const s = secao(`Por que combina com você — ${resultado.match}%`);
    s.classList.add('pontos-detalhe');
    s.append(el('p', 'fonte', resumoDosPontos(resultado.pontos)), listaDePontos(resultado.pontos, { comFonte: true }));
    const fontes = [...new Set(resultado.pontos.map((p) => ROTULO_FONTE[p.fonte]).filter(Boolean))];
    s.appendChild(el('p', 'fonte', `Tudo acima vem de: ${fontes.join(', ')}. O que o anúncio não diz aparece como “não informado” — pergunte ao corretor.`));
    corpo.appendChild(s);
  }

  if (d.planta) {
    const s = secao(d.maquete ? 'Planta e maquete 3D' : 'Planta interativa');
    blocoPlanta(d, s);
    corpo.appendChild(s);
  }

  for (const [url, titulo] of [[d.video_url, 'Vídeo'], [d.video_drone_url, 'Vista aérea (drone)']]) {
    const embed = urlDeEmbed(url);
    if (!url) continue;
    const s = secao(titulo);
    if (embed) {
      const caixa = el('div', 'video');
      const quadro = el('iframe');
      quadro.src = embed;
      quadro.title = `${titulo} — ${d.titulo}`;
      quadro.loading = 'lazy';
      quadro.allow = 'accelerometer; encrypted-media; gyroscope; picture-in-picture; fullscreen';
      caixa.appendChild(quadro);
      s.appendChild(caixa);
    } else {
      const link = el('a', 'btn btn-sm', `Abrir ${titulo.toLowerCase()}`);
      link.href = url; link.target = '_blank'; link.rel = 'noopener';
      s.appendChild(link);
    }
    corpo.appendChild(s);
  }

  if (d.descricao) {
    const s = secao('Descrição do anúncio');
    s.appendChild(el('p', 'descricao', d.descricao));
    corpo.appendChild(s);
  }
  const itens = [...d.caracteristicas, ...d.comodidades];
  if (itens.length) {
    const s = secao('Itens do imóvel');
    const caixa = el('div', 'itens');
    for (const item of itens) caixa.appendChild(el('span', '', item));
    s.appendChild(caixa);
    corpo.appendChild(s);
  }
  if (d.contexto) corpo.appendChild(blocoContexto(d.contexto));
  if (d.bairro_info && (d.bairro_info.descricao || d.bairro_info.valorizacao)) {
    const s = secao(`Sobre ${d.bairro}`);
    if (d.bairro_info.descricao) s.appendChild(el('p', '', d.bairro_info.descricao));
    if (d.bairro_info.valorizacao) {
      const nivel = { alta: 'alto', media: 'médio', baixa: 'baixo' }[d.bairro_info.valorizacao];
      s.appendChild(el('p', 'imovel-motivo', `Segundo a imobiliária, potencial de valorização ${nivel}${d.bairro_info.valorizacao_justificativa ? `: ${d.bairro_info.valorizacao_justificativa}` : '.'}`));
    }
    corpo.appendChild(s);
  }
  if (d.url_anuncio) {
    const s = secao();
    const link = el('a', 'btn btn-sm', 'Ver o anúncio no site da imobiliária');
    link.href = d.url_anuncio; link.target = '_blank'; link.rel = 'noopener';
    s.appendChild(link);
    corpo.appendChild(s);
  }

  const rodape = el('div', 'camada-rodape');
  if (d.whatsapp) {
    const wa = el('a', 'btn btn-whatsapp', 'Falar no WhatsApp');
    wa.href = linkWhatsApp({ imovelId: d.id }); wa.target = '_blank'; wa.rel = 'noopener';
    rodape.appendChild(wa);
  }
  const contato = el('button', 'btn btn-solid', 'Quero saber mais');
  contato.type = 'button';
  contato.addEventListener('click', () => aoContato(d));
  rodape.appendChild(contato);
  camada.appendChild(rodape);
}
