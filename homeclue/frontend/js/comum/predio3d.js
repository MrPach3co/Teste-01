// Prédio 3D noturno do lançamento: fachada com sacadas e vidro, cada unidade
// acesa na cor do seu status, térreo iluminado, cidade ao fundo e brilho nas
// janelas. A cor nunca anda sozinha: a etiqueta e o painel dizem o status por
// escrito.
import { el, reaisCurto } from './util.js';

const VENDOR = '../../vendor/three/';

export const STATUS_3D = {
  disponivel: { rotulo: 'Disponível', brilho: [0.02, 1.2, 0.12] },
  reservada: { rotulo: 'Reservada', brilho: [1.5, 0.62, 0.04] },
  vendida: { rotulo: 'Vendida', brilho: [1.4, 0.07, 0.05] },
};
const APAGADA = [0.035, 0.04, 0.055];

// Medidas em metros.
const BAIA = 7.2;
const PE_DIREITO = 3.1;
const TERREO = 4.6;
const PROFUNDIDADE = 15;
const RECUO = 0.35;
const MARGEM = 0.7;
const SACADA = 1.55;

function aleatorio(semente) {
  let a = semente >>> 0;
  return () => {
    a = (a + 0x6D2B79F5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function canvas(largura, altura) {
  const c = document.createElement('canvas');
  c.width = largura;
  c.height = altura;
  return [c, c.getContext('2d')];
}

// Um cômodo aceso visto pelo vidro: luz no teto, parede e uma cortina de lado.
function texturaInterior(THREE) {
  const [c, g] = canvas(64, 128);
  const grad = g.createLinearGradient(0, 0, 0, 128);
  grad.addColorStop(0, '#ffffff');
  grad.addColorStop(0.16, '#f2f2f2');
  grad.addColorStop(0.5, '#b4b4b4');
  grad.addColorStop(1, '#707070');
  g.fillStyle = grad;
  g.fillRect(0, 0, 64, 128);
  for (let x = 0; x < 16; x += 2) {
    g.fillStyle = x % 4 ? 'rgba(255,255,255,.16)' : 'rgba(0,0,0,.14)';
    g.fillRect(x, 4, 2, 124);
  }
  g.fillStyle = 'rgba(255,255,255,.10)';
  g.beginPath();
  g.moveTo(34, 0); g.lineTo(46, 0); g.lineTo(22, 128); g.lineTo(10, 128);
  g.fill();
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

// Janelas de prédio da cidade ao fundo: algumas acesas (quente ou fria), outras não.
function texturaCidade(THREE, semente) {
  const [c, g] = canvas(128, 256);
  const rnd = aleatorio(semente);
  g.fillStyle = '#04060b';
  g.fillRect(0, 0, 128, 256);
  const colunas = 8;
  const linhas = 16;
  const w = 128 / colunas;
  const h = 256 / linhas;
  for (let r = 0; r < linhas; r += 1) {
    for (let k = 0; k < colunas; k += 1) {
      const p = rnd();
      if (p < 0.42) {
        const quente = rnd() < 0.72;
        const a = 0.55 + rnd() * 0.45;
        g.fillStyle = quente
          ? `rgba(255,${(185 + rnd() * 45) | 0},${(110 + rnd() * 50) | 0},${a})`
          : `rgba(${(165 + rnd() * 40) | 0},${(195 + rnd() * 35) | 0},255,${a})`;
      } else {
        g.fillStyle = 'rgba(38,48,68,.45)';
      }
      g.fillRect(k * w + 3, r * h + 4, w - 6, h - 7);
    }
  }
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.wrapS = THREE.RepeatWrapping;
  t.wrapT = THREE.RepeatWrapping;
  return t;
}

function texturaClarao(THREE, cor) {
  const [c, g] = canvas(128, 128);
  const grad = g.createRadialGradient(64, 64, 0, 64, 64, 64);
  grad.addColorStop(0, cor);
  grad.addColorStop(1, 'rgba(0,0,0,0)');
  g.fillStyle = grad;
  g.fillRect(0, 0, 128, 128);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

function texturaPlaca(THREE, nome) {
  const [c, g] = canvas(1024, 160);
  g.fillStyle = '#0b0f17';
  g.fillRect(0, 0, 1024, 160);
  g.fillStyle = '#f4ead8';
  g.textAlign = 'center';
  g.textBaseline = 'middle';
  let tamanho = 64;
  const texto = nome.toUpperCase();
  const espaco = 'letterSpacing' in g ? 4 : 0;
  if (espaco) g.letterSpacing = `${espaco}px`;
  do {
    g.font = `700 ${tamanho}px Manrope, "Helvetica Neue", Arial, sans-serif`;
    tamanho -= 2;
  } while (g.measureText(texto).width + espaco * texto.length > 960 && tamanho > 18);
  g.fillText(texto, 512, 84);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

// Junta caixas e planos repetidos num InstancedMesh: uma chamada de desenho para todos.
class Lote {
  constructor(THREE) {
    this.THREE = THREE;
    this.itens = [];
  }

  add(pos, escala, rotY = 0, extra = null) {
    this.itens.push({ pos, escala, rotY, extra });
    return this.itens.length - 1;
  }

  malha(geometria, material, { sombra = false, cores = null } = {}) {
    const { THREE } = this;
    const m = new THREE.InstancedMesh(geometria, material, Math.max(this.itens.length, 1));
    m.count = this.itens.length;
    const mat = new THREE.Matrix4();
    const q = new THREE.Quaternion();
    const eixo = new THREE.Vector3(0, 1, 0);
    this.itens.forEach((it, i) => {
      q.setFromAxisAngle(eixo, it.rotY);
      mat.compose(new THREE.Vector3(...it.pos), q, new THREE.Vector3(...it.escala));
      m.setMatrixAt(i, mat);
      if (cores) m.setColorAt(i, new THREE.Color(...cores(it, i)));
    });
    m.instanceMatrix.needsUpdate = true;
    if (m.instanceColor) m.instanceColor.needsUpdate = true;
    m.castShadow = sombra;
    m.receiveShadow = sombra;
    return m;
  }
}

function construirTorre(THREE, torre, unidades, origemX, materiais, texturas) {
  const grupo = new THREE.Group();
  const n = Math.max(torre.unidades_por_andar, 1);
  const frente = Math.ceil(n / 2);
  const fundos = Math.floor(n / 2);
  const colunas = Math.max(frente, fundos, 1);
  const W = colunas * BAIA + 2 * MARGEM;
  const H = TERREO + torre.andares * PE_DIREITO;
  const D = PROFUNDIDADE;
  const faceZ = D / 2 - RECUO;
  grupo.position.x = origemX + W / 2;

  // Corpo e base de pedra
  const corpo = new THREE.Mesh(new THREE.BoxGeometry(W - 0.2, H - TERREO, D - 2 * RECUO), materiais.fachada);
  corpo.position.y = TERREO + (H - TERREO) / 2;
  corpo.castShadow = true;
  corpo.receiveShadow = true;
  grupo.add(corpo);
  const base = new THREE.Mesh(new THREE.BoxGeometry(W + 0.3, TERREO, D - 2 * RECUO + 0.3), materiais.pedra);
  base.position.y = TERREO / 2;
  base.castShadow = true;
  base.receiveShadow = true;
  grupo.add(base);

  const vidros = new Lote(THREE);
  const sacadas = new Lote(THREE);
  const guardaCorpos = new Lote(THREE);
  const corrimaos = new Lote(THREE);
  const caixilhos = new Lote(THREE);
  const pilares = new Lote(THREE);
  const faixas = new Lote(THREE);
  const lateral = new Lote(THREE);
  const registros = [];

  const lado = (frenteDoPredio) => (frenteDoPredio ? 1 : -1);
  const quadro = (cx, cy, z, w, h, rotY, mullion) => {
    const sz = 0.09;
    caixilhos.add([cx, cy + h / 2, z], [w + 0.12, 0.08, sz], rotY);
    caixilhos.add([cx, cy - h / 2, z], [w + 0.12, 0.08, sz], rotY);
    caixilhos.add([cx - w / 2, cy, z], [0.08, h, sz], rotY);
    caixilhos.add([cx + w / 2, cy, z], [0.08, h, sz], rotY);
    if (mullion === 'v') caixilhos.add([cx, cy, z], [0.05, h, 0.07], rotY);
    if (mullion === 'h') caixilhos.add([cx, cy + h * 0.18, z], [w, 0.05, 0.07], rotY);
  };

  for (const u of unidades) {
    const pos = Math.min(Math.max(u.posicao, 1), n);
    const naFrente = pos <= frente;
    const indice = naFrente ? pos - 1 : pos - frente - 1;
    const s = lado(naFrente);
    const cx = naFrente ? -W / 2 + MARGEM + (indice + 0.5) * BAIA : W / 2 - MARGEM - (indice + 0.5) * BAIA;
    const y0 = TERREO + (u.andar - 1) * PE_DIREITO;
    const rotY = naFrente ? 0 : Math.PI;
    const zVidro = s * (faceZ + 0.012);
    const portaX = cx - s * BAIA * 0.13;
    const janelaX = cx + s * BAIA * 0.29;
    const registro = { u, centro: [origemX + W / 2 + cx, y0 + PE_DIREITO / 2, s * (faceZ + SACADA / 2)], normal: s, vidros: [] };
    // Porta de correr da sacada e janela
    registro.vidros.push(vidros.add([portaX, y0 + 0.12 + 1.25, zVidro], [BAIA * 0.52, 2.5, 1], rotY, registro));
    registro.vidros.push(vidros.add([janelaX, y0 + 1.05 + 0.725, zVidro], [1.5, 1.45, 1], rotY, registro));
    quadro(portaX, y0 + 0.12 + 1.25, s * (faceZ + 0.04), BAIA * 0.52, 2.5, rotY, 'v');
    quadro(janelaX, y0 + 1.05 + 0.725, s * (faceZ + 0.04), 1.5, 1.45, rotY, 'h');
    // Sacada com guarda-corpo de vidro
    const sx = cx - s * BAIA * 0.05;
    const largSacada = BAIA * 0.74;
    sacadas.add([sx, y0 + 0.08, s * (faceZ + SACADA / 2)], [largSacada, 0.16, SACADA], 0, registro);
    guardaCorpos.add([sx, y0 + 0.66, s * (faceZ + SACADA - 0.02)], [largSacada, 1.0, 0.03], 0, registro);
    guardaCorpos.add([sx - largSacada / 2, y0 + 0.66, s * (faceZ + SACADA / 2)], [0.03, 1.0, SACADA], 0, registro);
    guardaCorpos.add([sx + largSacada / 2, y0 + 0.66, s * (faceZ + SACADA / 2)], [0.03, 1.0, SACADA], 0, registro);
    corrimaos.add([sx, y0 + 1.18, s * (faceZ + SACADA - 0.02)], [largSacada + 0.04, 0.05, 0.06]);
    registros.push(registro);
  }

  // Pilares entre as baias e faixas de laje em cada andar (frente e fundos)
  for (const s of [1, -1]) {
    for (let k = 0; k <= colunas; k += 1) {
      const x = -W / 2 + MARGEM + k * BAIA;
      pilares.add([x, TERREO + (H - TERREO) / 2 + 0.3, s * (faceZ + 0.27)], [0.44, H - TERREO + 0.6, 0.54]);
    }
    for (let f = 0; f <= torre.andares; f += 1) {
      faixas.add([0, TERREO + f * PE_DIREITO, s * (faceZ + 0.3)], [W + 0.1, f === torre.andares ? 0.5 : 0.3, 0.6]);
    }
  }
  // Janelas das laterais (decorativas, acesas ao acaso)
  const rnd = aleatorio(torre.andares * 97 + n * 13 + Math.round(origemX));
  for (const sx of [1, -1]) {
    for (let a = 0; a < torre.andares; a += 1) {
      for (const dz of [-D / 5, D / 5]) {
        lateral.add([sx * ((W - 0.2) / 2 + 0.012), TERREO + a * PE_DIREITO + 1.75, dz], [1.3, 1.4, 1], sx * Math.PI / 2,
          rnd() < 0.55 ? [1.2, 0.84, 0.44] : [0.05, 0.06, 0.08]);
      }
    }
  }

  const geoCaixa = new THREE.BoxGeometry(1, 1, 1);
  const geoPlano = new THREE.PlaneGeometry(1, 1);
  const malhaVidros = vidros.malha(geoPlano, materiais.vidroUnidade, { cores: () => [1, 1, 1] });
  const malhaSacadas = sacadas.malha(geoCaixa, materiais.concretoClaro, { sombra: true });
  const malhaGuarda = guardaCorpos.malha(geoCaixa, materiais.vidroGuarda);
  const malhaCorrimao = corrimaos.malha(geoCaixa, materiais.metal);
  const malhaCaixilho = caixilhos.malha(geoCaixa, materiais.caixilho);
  const malhaPilares = pilares.malha(geoCaixa, materiais.fachadaPilar, { sombra: true });
  const malhaFaixas = faixas.malha(geoCaixa, materiais.concretoClaro, { sombra: true });
  const malhaLateral = lateral.malha(geoPlano, materiais.vidroDecorativo, { cores: (it) => it.extra });
  malhaVidros.userData.registros = vidros.itens.map((it) => it.extra);
  malhaSacadas.userData.registros = sacadas.itens.map((it) => it.extra);
  malhaGuarda.userData.registros = guardaCorpos.itens.map((it) => it.extra);
  grupo.add(malhaVidros, malhaSacadas, malhaGuarda, malhaCorrimao, malhaCaixilho, malhaPilares, malhaFaixas, malhaLateral);

  // Térreo: portaria envidraçada e acesa, marquise com placa e portão da garagem
  const zBase = (D - 2 * RECUO + 0.3) / 2 + 0.012;
  const lobbyW = W * 0.5;
  const lobby = new THREE.Mesh(new THREE.PlaneGeometry(lobbyW, TERREO - 1.3), materiais.lobby);
  lobby.position.set(-W * 0.12, (TERREO - 1.3) / 2 + 0.2, zBase);
  grupo.add(lobby);
  const mullions = new Lote(THREE);
  for (let k = 0; k <= 6; k += 1) mullions.add([-W * 0.12 - lobbyW / 2 + (k * lobbyW) / 6, (TERREO - 1.3) / 2 + 0.2, zBase + 0.03], [0.07, TERREO - 1.3, 0.07]);
  grupo.add(mullions.malha(new THREE.BoxGeometry(1, 1, 1), materiais.caixilho));
  const marquise = new THREE.Mesh(new THREE.BoxGeometry(W * 0.62, 0.24, 3.2), materiais.concretoClaro);
  marquise.position.set(-W * 0.12, TERREO - 0.45, zBase + 1.6);
  marquise.castShadow = true;
  grupo.add(marquise);
  const placa = new THREE.Mesh(new THREE.PlaneGeometry(W * 0.56, (W * 0.56) * (160 / 1024)), new THREE.MeshBasicMaterial({ map: texturas.placa }));
  placa.position.set(-W * 0.12, TERREO - 0.45, zBase + 3.21);
  grupo.add(placa);
  const spots = new Lote(THREE);
  for (let k = 0; k < 5; k += 1) spots.add([-W * 0.12 - W * 0.24 + k * W * 0.12, TERREO - 0.58, zBase + 1.6], [0.35, 0.02, 0.35]);
  grupo.add(spots.malha(new THREE.BoxGeometry(1, 1, 1), materiais.luzQuente));
  const garagem = new THREE.Mesh(new THREE.PlaneGeometry(3.4, 2.7), materiais.garagem);
  garagem.position.set(W / 2 - 3.2, 1.35, zBase);
  grupo.add(garagem);

  // Cobertura: platibanda, casa de máquinas e luz de sinalização
  const plat = new Lote(THREE);
  plat.add([0, H + 0.5, D / 2 - RECUO], [W, 1.0, 0.3]);
  plat.add([0, H + 0.5, -(D / 2 - RECUO)], [W, 1.0, 0.3]);
  plat.add([W / 2 - 0.15, H + 0.5, 0], [0.3, 1.0, D - 2 * RECUO]);
  plat.add([-(W / 2 - 0.15), H + 0.5, 0], [0.3, 1.0, D - 2 * RECUO]);
  grupo.add(plat.malha(new THREE.BoxGeometry(1, 1, 1), materiais.fachada, { sombra: true }));
  const casaMaquinas = new THREE.Mesh(new THREE.BoxGeometry(W * 0.32, 2.6, D * 0.35), materiais.fachadaPilar);
  casaMaquinas.position.set(0, H + 1.3, -D * 0.1);
  casaMaquinas.castShadow = true;
  grupo.add(casaMaquinas);
  const sinal = new THREE.Mesh(new THREE.SphereGeometry(0.22, 12, 8), materiais.sinalizacao);
  sinal.position.set(0, H + 2.8, -D * 0.1);
  grupo.add(sinal);

  return { grupo, W, H, D, registros, malhaVidros, pickaveis: [malhaVidros, malhaSacadas, malhaGuarda], sinal, nome: torre.nome };
}

function construirCidade(THREE, cena, raioMin, semente, centroX, alturaRef) {
  const rnd = aleatorio(semente);
  const texturas = [1, 2, 3, 4].map((k) => texturaCidade(THREE, semente * 7 + k));
  const geo = new THREE.BoxGeometry(1, 1, 1);
  const luzesTopo = new Lote(THREE);
  for (let i = 0; i < 78; i += 1) {
    const ang = (i / 78) * Math.PI * 2 + rnd() * 0.05;
    const raio = raioMin + rnd() * 150;
    // Deixa um respiro na frente do prédio (a câmera começa por ali).
    const w = 10 + rnd() * 16;
    const d = 10 + rnd() * 16;
    const h = Math.min(10 + rnd() * rnd() * 90, alturaRef * (1.1 + (raio - raioMin) / 160));
    const tex = texturas[i % texturas.length].clone();
    tex.needsUpdate = true;
    tex.repeat.set(Math.max(1, Math.round(w / 24 * 2) / 2), Math.max(1, Math.round(h / 48 * 2) / 2));
    tex.offset.set(rnd(), rnd());
    const material = new THREE.MeshStandardMaterial({ color: 0x0b0f1a, roughness: 0.9, emissive: 0xffffff, emissiveMap: tex, emissiveIntensity: 0.8 });
    const predio = new THREE.Mesh(geo, material);
    predio.scale.set(w, h, d);
    predio.position.set(centroX + Math.cos(ang) * raio, h / 2, Math.sin(ang) * raio);
    predio.rotation.y = rnd() * Math.PI;
    cena.add(predio);
    if (h > alturaRef * 1.25) luzesTopo.add([predio.position.x, h + 0.6, predio.position.z], [0.5, 0.5, 0.5]);
  }
  const vermelhas = luzesTopo.malha(new THREE.SphereGeometry(1, 8, 6), new THREE.MeshBasicMaterial({ color: new THREE.Color(3, 0.25, 0.2) }));
  cena.add(vermelhas);
  return vermelhas;
}

function construirEntorno(THREE, cena, largura, materiais, texturas) {
  const chao = new THREE.Mesh(new THREE.PlaneGeometry(1400, 1400), materiais.asfalto);
  chao.rotation.x = -Math.PI / 2;
  chao.receiveShadow = true;
  cena.add(chao);
  const calcada = new THREE.Mesh(new THREE.PlaneGeometry(largura + 34, PROFUNDIDADE + 34), materiais.calcada);
  calcada.rotation.x = -Math.PI / 2;
  calcada.position.set(largura / 2, 0.02, 0);
  calcada.receiveShadow = true;
  cena.add(calcada);
  const faixas = new Lote(THREE);
  for (let x = -120; x <= largura + 120; x += 7) faixas.add([x, 0.03, PROFUNDIDADE / 2 + 24], [3.2, 1, 0.16]);
  const geoFaixa = new THREE.PlaneGeometry(1, 1).rotateX(-Math.PI / 2);
  cena.add(faixas.malha(geoFaixa, new THREE.MeshBasicMaterial({ color: new THREE.Color(0.2, 0.19, 0.15) })));

  const troncos = new Lote(THREE);
  const copas = new Lote(THREE);
  const postes = new Lote(THREE);
  const lampadas = new Lote(THREE);
  const claroes = new Lote(THREE);
  const rnd = aleatorio(4242);
  const xs = [];
  for (let x = -14; x <= largura + 14; x += 9) xs.push(x);
  for (const x of xs) {
    for (const z of [PROFUNDIDADE / 2 + 15.5, -(PROFUNDIDADE / 2 + 13)]) {
      if (z > 0 && x > -10 && x < largura + 10) continue;
      const h = 3.2 + rnd() * 1.8;
      troncos.add([x, h / 2, z], [0.22, h, 0.22]);
      copas.add([x, h + 1.2, z], [1.7 + rnd() * 0.7, 2.0 + rnd() * 0.7, 1.7 + rnd() * 0.7], rnd() * 3);
    }
  }
  for (const x of [-10, largura / 2, largura + 10]) {
    for (const z of [PROFUNDIDADE / 2 + 17, -(PROFUNDIDADE / 2 + 17)]) {
      postes.add([x, 3.6, z], [0.14, 7.2, 0.14]);
      lampadas.add([x, 7.25, z], [0.7, 0.18, 0.7]);
      claroes.add([x, 0.05, z], [12, 1, 12]);
    }
  }
  cena.add(troncos.malha(new THREE.CylinderGeometry(0.5, 0.6, 1, 6), materiais.tronco));
  const copasMalha = copas.malha(new THREE.IcosahedronGeometry(1, 1), materiais.folhagem);
  copasMalha.castShadow = true;
  cena.add(copasMalha);
  cena.add(postes.malha(new THREE.CylinderGeometry(0.5, 0.5, 1, 6), materiais.metal));
  cena.add(lampadas.malha(new THREE.BoxGeometry(1, 1, 1), materiais.luzQuente));
  const geoClarao = new THREE.PlaneGeometry(1, 1).rotateX(-Math.PI / 2);
  cena.add(claroes.malha(geoClarao, new THREE.MeshBasicMaterial({
    map: texturas.clarao, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, opacity: 0.32,
  })));
  // Clarão quente no chão em volta do prédio (a luz da fachada batendo na calçada)
  const halo = new THREE.Mesh(geoClarao.clone(), new THREE.MeshBasicMaterial({
    map: texturas.clarao, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, opacity: 0.22,
  }));
  halo.scale.set(largura + 46, 1, PROFUNDIDADE + 46);
  halo.position.set(largura / 2, 0.04, 0);
  cena.add(halo);
}

function construirCeu(THREE, cena) {
  const ceu = new THREE.Mesh(new THREE.SphereGeometry(700, 32, 16), new THREE.ShaderMaterial({
    side: THREE.BackSide,
    depthWrite: false,
    fog: false,
    uniforms: {
      topo: { value: new THREE.Color(0x02040c) },
      meio: { value: new THREE.Color(0x0a1638) },
      horizonte: { value: new THREE.Color(0x24407e) },
    },
    vertexShader: 'varying vec3 vPos; void main(){ vPos = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
    fragmentShader: `uniform vec3 topo; uniform vec3 meio; uniform vec3 horizonte; varying vec3 vPos;
      void main(){ float h = clamp(vPos.y, -0.1, 1.0);
        vec3 c = mix(horizonte, meio, smoothstep(0.0, 0.18, h));
        c = mix(c, topo, smoothstep(0.18, 0.75, h));
        gl_FragColor = vec4(c, 1.0); }`,
  }));
  cena.add(ceu);
  const rnd = aleatorio(77);
  const pontos = [];
  for (let i = 0; i < 900; i += 1) {
    const teta = rnd() * Math.PI * 2;
    const fi = Math.acos(0.15 + rnd() * 0.85);
    pontos.push(Math.sin(fi) * Math.cos(teta) * 650, Math.cos(fi) * 650, Math.sin(fi) * Math.sin(teta) * 650);
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(pontos, 3));
  cena.add(new THREE.Points(geo, new THREE.PointsMaterial({ color: 0xcfd8ff, size: 1.3, sizeAttenuation: false, transparent: true, opacity: 0.75, fog: false })));
  const lua = new THREE.Mesh(new THREE.SphereGeometry(9, 24, 16), new THREE.MeshBasicMaterial({ color: new THREE.Color(1.6, 1.65, 1.8), fog: false }));
  lua.position.set(-260, 300, -420);
  cena.add(lua);
}

function materiaisDaCena(THREE, texturas) {
  return {
    fachada: new THREE.MeshStandardMaterial({ color: 0xe9e1d3, roughness: 0.86 }),
    fachadaPilar: new THREE.MeshStandardMaterial({ color: 0xd5c9b6, roughness: 0.8 }),
    concretoClaro: new THREE.MeshStandardMaterial({ color: 0xf1ece3, roughness: 0.75 }),
    pedra: new THREE.MeshStandardMaterial({ color: 0x3a3430, roughness: 0.65 }),
    caixilho: new THREE.MeshStandardMaterial({ color: 0x24272d, roughness: 0.45, metalness: 0.4 }),
    metal: new THREE.MeshStandardMaterial({ color: 0x3a3f48, roughness: 0.35, metalness: 0.7 }),
    vidroUnidade: new THREE.MeshBasicMaterial({ map: texturas.interior }),
    vidroDecorativo: new THREE.MeshBasicMaterial({ map: texturas.interior }),
    vidroGuarda: new THREE.MeshStandardMaterial({ color: 0x9fc0e8, roughness: 0.08, metalness: 0.1, transparent: true, opacity: 0.22, depthWrite: false }),
    lobby: new THREE.MeshBasicMaterial({ color: new THREE.Color(1.45, 0.98, 0.55), map: texturas.interior }),
    luzQuente: new THREE.MeshBasicMaterial({ color: new THREE.Color(1.7, 1.2, 0.72) }),
    garagem: new THREE.MeshStandardMaterial({ color: 0x1f2229, roughness: 0.6, metalness: 0.5 }),
    sinalizacao: new THREE.MeshBasicMaterial({ color: new THREE.Color(3, 0.2, 0.15) }),
    asfalto: new THREE.MeshStandardMaterial({ color: 0x0a0d15, roughness: 0.95 }),
    calcada: new THREE.MeshStandardMaterial({ color: 0x2c303a, roughness: 0.8 }),
    tronco: new THREE.MeshStandardMaterial({ color: 0x2b2118, roughness: 0.9 }),
    folhagem: new THREE.MeshStandardMaterial({ color: 0x1e3a2b, roughness: 0.85, flatShading: true }),
  };
}

const facil = (t) => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2);

/**
 * Monta o prédio 3D dentro de `container`.
 * opcoes: aoClicar(unidade), filtro(unidade) → bool.
 * Retorna { selecionar(u), focarAndar(andar|null), repintar(), visaoGeral(), destruir() } ou null sem WebGL.
 */
export async function predio3D(container, emp, { aoClicar, filtro = () => true } = {}) {
  let THREE;
  let OrbitControls;
  let EffectComposer;
  let RenderPass;
  let UnrealBloomPass;
  let OutputPass;
  try {
    THREE = await import(`${VENDOR}three.module.min.js`);
    [{ OrbitControls }, { EffectComposer }, { RenderPass }, { UnrealBloomPass }, { OutputPass }] = await Promise.all([
      import(`${VENDOR}OrbitControls.js`), import(`${VENDOR}EffectComposer.js`), import(`${VENDOR}RenderPass.js`),
      import(`${VENDOR}UnrealBloomPass.js`), import(`${VENDOR}OutputPass.js`),
    ]);
  } catch {
    container.replaceChildren(el('p', 'aviso-3d', 'Não foi possível abrir a vista 3D neste navegador. Use a grade de unidades ao lado.'));
    return null;
  }

  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
  } catch {
    container.replaceChildren(el('p', 'aviso-3d', 'Seu aparelho não abriu a vista 3D. Use a grade de unidades ao lado.'));
    return null;
  }
  const leve = matchMedia('(pointer: coarse)').matches || Math.min(screen.width, screen.height) < 700;
  const semMovimento = matchMedia('(prefers-reduced-motion: reduce)').matches;
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, leve ? 1.5 : 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.0;
  renderer.shadowMap.enabled = !leve;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;

  const texturas = {
    interior: texturaInterior(THREE),
    clarao: texturaClarao(THREE, 'rgba(255,190,120,0.9)'),
    placa: texturaPlaca(THREE, emp.nome || 'Residencial'),
  };
  const materiais = materiaisDaCena(THREE, texturas);
  const cena = new THREE.Scene();
  cena.fog = new THREE.Fog(0x0b1534, 140, 520);
  construirCeu(THREE, cena);

  // Torres lado a lado
  const torres = [];
  let x = 0;
  for (const torre of emp.torres) {
    const t = construirTorre(THREE, torre, emp.unidades.filter((u) => u.torre === torre.nome), x, materiais, texturas);
    cena.add(t.grupo);
    torres.push(t);
    x += t.W + 10;
  }
  const larguraTotal = Math.max(x - 10, 1);
  const alturaMax = Math.max(...torres.map((t) => t.H), 10);
  const centroX = larguraTotal / 2;
  construirEntorno(THREE, cena, larguraTotal, materiais, texturas);
  const luzesCidade = construirCidade(THREE, cena, Math.max(150, larguraTotal + 120), 1337, centroX, alturaMax);

  // Luz: lua fria, céu, luz quente de baixo na fachada e portaria
  cena.add(new THREE.HemisphereLight(0x2a3d78, 0x07080d, 0.7));
  const lua = new THREE.DirectionalLight(0xa8c0ff, 0.65);
  lua.position.set(centroX - 70, 140, 90);
  lua.target.position.set(centroX, 0, 0);
  lua.castShadow = !leve;
  lua.shadow.mapSize.set(2048, 2048);
  Object.assign(lua.shadow.camera, { left: -70, right: 70, top: 70, bottom: -70, near: 10, far: 400 });
  lua.shadow.bias = -0.0005;
  cena.add(lua, lua.target);
  for (const t of torres) {
    const baseX = t.grupo.position.x;
    for (const dx of [-t.W / 2 + 1.2, 0, t.W / 2 - 1.2]) {
      for (const s of leve ? [1] : [1, -1]) {
        const spot = new THREE.SpotLight(0xffb36b, s > 0 ? 34 : 18, 0, 0.5, 0.95, 1);
        spot.position.set(baseX + dx, 0.6, s * (t.D / 2 + 11));
        spot.target.position.set(baseX + dx, t.H * 0.62, s * (t.D / 2 - 1));
        cena.add(spot, spot.target);
      }
    }
    const portaria = new THREE.PointLight(0xffc98a, 18, 22, 1.5);
    portaria.position.set(baseX - t.W * 0.12, 3.2, t.D / 2 + 3);
    cena.add(portaria);
  }

  // Câmera e controles
  const camera = new THREE.PerspectiveCamera(32, 1, 0.5, 2000);
  const alvoInicial = new THREE.Vector3(centroX, alturaMax * 0.5, 0);
  const posInicial = new THREE.Vector3();
  const direcaoInicial = new THREE.Vector3(0.55, 0, 0.84).normalize();
  let distInicial = 100;
  const enquadrar = (aspecto) => {
    const meiaV = Math.tan(THREE.MathUtils.degToRad(camera.fov / 2));
    const meiaH = meiaV * aspecto;
    const largura = Math.hypot(larguraTotal, PROFUNDIDADE + 2 * SACADA);
    distInicial = Math.max((alturaMax + 3) / 0.62 / 2 / meiaV, largura / 0.7 / 2 / meiaH);
    posInicial.copy(alvoInicial).addScaledVector(direcaoInicial, distInicial);
    posInicial.y = alturaMax * 0.34;
  };
  enquadrar(1.6);
  camera.position.copy(posInicial);

  const composer = new EffectComposer(renderer);
  composer.addPass(new RenderPass(cena, camera));
  const bloom = new UnrealBloomPass(new THREE.Vector2(256, 256), 0.62, 0.5, 0.82);
  composer.addPass(bloom);
  composer.addPass(new OutputPass());

  const vinheta = el('div', 'predio-vinheta');
  const dica = el('div', 'predio-dica');
  dica.hidden = true;
  container.replaceChildren(renderer.domElement, vinheta, dica);
  renderer.domElement.setAttribute('role', 'img');
  renderer.domElement.setAttribute('aria-label', `${emp.nome}: prédio em 3D com cada unidade acesa na cor do status. Toque numa unidade para ver os detalhes.`);

  const controles = new OrbitControls(camera, renderer.domElement);
  controles.target.copy(alvoInicial);
  controles.enableDamping = true;
  controles.dampingFactor = 0.07;
  controles.enablePan = false;
  controles.minDistance = 16;
  controles.maxDistance = distInicial * 2.4;
  controles.maxPolarAngle = Math.PI * 0.485;
  controles.minPolarAngle = Math.PI * 0.12;
  controles.autoRotate = !semMovimento;
  controles.autoRotateSpeed = 0.35;
  controles.update();

  let parado = null;
  const pausarGiro = () => {
    controles.autoRotate = false;
    clearTimeout(parado);
    if (!semMovimento) parado = setTimeout(() => { if (!selecionada) controles.autoRotate = true; }, 9000);
  };
  controles.addEventListener('start', pausarGiro);

  // Contornos de destaque (passar o mouse e unidade escolhida)
  const geoContorno = new THREE.EdgesGeometry(new THREE.BoxGeometry(BAIA - 0.3, PE_DIREITO - 0.12, SACADA + 0.3));
  const contornoHover = new THREE.LineSegments(geoContorno, new THREE.LineBasicMaterial({ color: new THREE.Color(2.4, 2.4, 2.4), transparent: true, opacity: 0.9 }));
  const contornoSel = new THREE.LineSegments(geoContorno, new THREE.LineBasicMaterial({ color: new THREE.Color(1.1, 1.5, 3.2) }));
  const caixaSel = new THREE.Mesh(new THREE.BoxGeometry(BAIA - 0.3, PE_DIREITO - 0.12, SACADA + 0.3),
    new THREE.MeshBasicMaterial({ color: new THREE.Color(0.35, 0.5, 1.4), transparent: true, opacity: 0.16, depthWrite: false }));
  contornoHover.visible = false;
  contornoSel.visible = false;
  caixaSel.visible = false;
  cena.add(contornoHover, contornoSel, caixaSel);
  const faixaAndar = new THREE.Mesh(new THREE.BoxGeometry(1, 0.18, 1), new THREE.MeshBasicMaterial({ color: new THREE.Color(0.9, 1.2, 3), transparent: true, opacity: 0.5, depthWrite: false }));
  faixaAndar.visible = false;
  cena.add(faixaAndar);

  const registros = torres.flatMap((t) => t.registros.map((r) => ({ ...r, torre: t })));
  const porId = new Map(registros.map((r) => [r.u.id, r]));
  let selecionada = null;
  let andarFocado = null;
  const cor = new THREE.Color();

  const corDa = (r, fator = 1) => {
    if (!filtro(r.u)) return APAGADA;
    const b = STATUS_3D[r.u.status]?.brilho || STATUS_3D.vendida.brilho;
    let f = fator;
    if (andarFocado !== null && r.u.andar !== andarFocado) f *= 0.07;
    return [b[0] * f, b[1] * f, b[2] * f];
  };
  const repintar = () => {
    for (const t of torres) {
      t.registros.forEach((r) => {
        const c = corDa(r);
        for (const i of r.vidros) t.malhaVidros.setColorAt(i, cor.setRGB(c[0], c[1], c[2]));
      });
      t.malhaVidros.instanceColor.needsUpdate = true;
    }
  };
  repintar();

  const posicionarContorno = (obj, r) => {
    obj.position.set(r.centro[0], r.centro[1], r.centro[2]);
    obj.visible = true;
  };

  // Voo da câmera
  let voo = null;
  const voar = (destPos, destAlvo, ms = 1100) => {
    if (semMovimento) {
      camera.position.copy(destPos);
      controles.target.copy(destAlvo);
      return;
    }
    voo = { t0: performance.now(), ms, dePos: camera.position.clone(), deAlvo: controles.target.clone(), paraPos: destPos, paraAlvo: destAlvo };
  };
  const focarUnidade = (r) => {
    const alvo = new THREE.Vector3(...r.centro);
    const lateral = (r.centro[0] - centroX) >= 0 ? 1 : -1;
    const pos = new THREE.Vector3(alvo.x + lateral * 9, alvo.y + 2.5, alvo.z + r.normal * 30);
    voar(pos, alvo);
  };

  const selecionar = (u, { voarAte = true } = {}) => {
    const r = u ? porId.get(u.id) : null;
    selecionada = r;
    if (!r) {
      contornoSel.visible = false;
      caixaSel.visible = false;
      return;
    }
    posicionarContorno(contornoSel, r);
    posicionarContorno(caixaSel, r);
    controles.autoRotate = false;
    if (voarAte) focarUnidade(r);
  };

  const focarAndar = (andar) => {
    andarFocado = andar;
    repintar();
    if (andar === null) {
      faixaAndar.visible = false;
      return;
    }
    const t = torres[0];
    const y = TERREO + (andar - 1) * PE_DIREITO;
    faixaAndar.scale.set(larguraTotal + 1.4, 1, t.D + 3.6);
    faixaAndar.position.set(centroX, y + 0.02, 0);
    faixaAndar.visible = true;
    controles.autoRotate = false;
    const alvo = new THREE.Vector3(centroX, y + PE_DIREITO / 2, 0);
    const dir = camera.position.clone().sub(controles.target).setY(0).normalize();
    const dist = Math.max(36, larguraTotal * 1.6);
    voar(alvo.clone().add(dir.multiplyScalar(dist)).setY(y + 5), alvo);
  };

  const visaoGeral = () => {
    andarFocado = null;
    faixaAndar.visible = false;
    repintar();
    voar(posInicial.clone(), alvoInicial.clone());
    if (!semMovimento) setTimeout(() => { if (!selecionada) controles.autoRotate = true; }, 1300);
  };

  // Ponteiro: etiqueta ao passar e clique para escolher
  const raio = new THREE.Raycaster();
  const ponteiro = new THREE.Vector2();
  const pickaveis = torres.flatMap((t) => t.pickaveis);
  const sob = (e) => {
    const rect = renderer.domElement.getBoundingClientRect();
    ponteiro.set(((e.clientX - rect.left) / rect.width) * 2 - 1, -((e.clientY - rect.top) / rect.height) * 2 + 1);
    raio.setFromCamera(ponteiro, camera);
    const achado = raio.intersectObjects(pickaveis, false)[0];
    if (!achado || achado.instanceId === undefined) return null;
    const r = achado.object.userData.registros?.[achado.instanceId];
    return r ? porId.get(r.u.id) : null;
  };
  const textoDica = (u) => {
    const partes = [u.tipologia || (u.quartos ? `${u.quartos} quartos` : null), u.area_m2 ? `${u.area_m2} m²` : null].filter(Boolean).join(' · ');
    dica.replaceChildren(
      el('strong', '', `Apto ${u.codigo}`),
      el('span', 'predio-dica-andar', `${u.andar}º andar`),
      el('span', `predio-dica-status st-${u.status}`, STATUS_3D[u.status]?.rotulo || u.status),
    );
    if (partes) dica.appendChild(el('span', 'predio-dica-dados', partes));
    if (u.preco && u.status !== 'vendida') dica.appendChild(el('span', 'predio-dica-preco', reaisCurto(u.preco)));
  };
  let hoverId = null;
  renderer.domElement.addEventListener('pointermove', (e) => {
    if (e.pointerType === 'touch') return;
    const r = sob(e);
    renderer.domElement.style.cursor = r ? 'pointer' : 'grab';
    if (!r) {
      contornoHover.visible = false;
      dica.hidden = true;
      hoverId = null;
      return;
    }
    if (hoverId !== r.u.id) {
      hoverId = r.u.id;
      textoDica(r.u);
      posicionarContorno(contornoHover, r);
    }
    const caixa = container.getBoundingClientRect();
    const px = e.clientX - caixa.left;
    dica.style.left = `${Math.min(px + 16, caixa.width - 220)}px`;
    dica.style.top = `${Math.max(e.clientY - caixa.top - 70, 8)}px`;
    dica.hidden = false;
  });
  renderer.domElement.addEventListener('pointerleave', () => {
    contornoHover.visible = false;
    dica.hidden = true;
    hoverId = null;
  });
  let inicio = null;
  renderer.domElement.addEventListener('pointerdown', (e) => { inicio = [e.clientX, e.clientY]; });
  renderer.domElement.addEventListener('pointerup', (e) => {
    if (!inicio || Math.hypot(e.clientX - inicio[0], e.clientY - inicio[1]) > 6) return;
    const r = sob(e);
    if (!r) return;
    selecionar(r.u);
    if (aoClicar) aoClicar(r.u);
  });

  let mexeu = false;
  controles.addEventListener('start', () => { mexeu = true; });
  const ajustar = () => {
    const { width, height } = container.getBoundingClientRect();
    if (!width || !height) return;
    renderer.setSize(width, height, false);
    composer.setSize(width, height);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    if (!mexeu && !selecionada && !voo) {
      enquadrar(camera.aspect);
      camera.position.copy(posInicial);
      controles.maxDistance = distInicial * 2.4;
    }
  };
  const observador = new ResizeObserver(ajustar);
  observador.observe(container);
  ajustar();

  let ativo = true;
  const relogio = new THREE.Clock();
  const sinais = torres.map((t) => t.sinal);
  const desenhar = () => {
    if (!ativo) return;
    requestAnimationFrame(desenhar);
    if (document.hidden) return;
    const tempo = relogio.getElapsedTime();
    if (voo) {
      const p = Math.min((performance.now() - voo.t0) / voo.ms, 1);
      const k = facil(p);
      camera.position.lerpVectors(voo.dePos, voo.paraPos, k);
      controles.target.lerpVectors(voo.deAlvo, voo.paraAlvo, k);
      if (p >= 1) voo = null;
    }
    // Luz de sinalização piscando e unidade escolhida "respirando"
    const pisca = Math.sin(tempo * 3) > 0.2 ? 1 : 0.15;
    for (const s of sinais) s.material.color.setRGB(3 * pisca, 0.2 * pisca, 0.15 * pisca);
    luzesCidade.material.color.setRGB(3 * pisca, 0.25 * pisca, 0.2 * pisca);
    if (selecionada) {
      const f = 1.25 + 0.35 * Math.sin(tempo * 3.2);
      const c = corDa(selecionada, f);
      for (const i of selecionada.vidros) selecionada.torre.malhaVidros.setColorAt(i, cor.setRGB(c[0], c[1], c[2]));
      selecionada.torre.malhaVidros.instanceColor.needsUpdate = true;
      caixaSel.material.opacity = 0.04 + 0.035 * (Math.sin(tempo * 3.2) + 1);
    }
    controles.update();
    composer.render();
  };
  desenhar();

  return {
    selecionar(u) { repintar(); selecionar(u); },
    focarAndar,
    visaoGeral,
    repintar,
    destruir() {
      ativo = false;
      clearTimeout(parado);
      observador.disconnect();
      controles.dispose();
      cena.traverse((o) => {
        if (o.geometry) o.geometry.dispose();
        const mats = Array.isArray(o.material) ? o.material : o.material ? [o.material] : [];
        for (const m of mats) {
          for (const v of Object.values(m)) if (v && v.isTexture) v.dispose();
          m.dispose();
        }
      });
      Object.values(texturas).forEach((t) => t.dispose());
      bloom.dispose?.();
      composer.dispose?.();
      renderer.dispose();
    },
  };
}
