// Planta humanizada em 3D, gerada a partir da planta desenhada pela
// imobiliária: cada cômodo ganha o piso do seu tipo (madeira, porcelanato,
// deck, grama), paredes com portas entre cômodos vizinhos e janelas nas
// paredes externas, e móveis típicos daquele cômodo.
//
// Os móveis são ilustrativos, como numa planta humanizada de lançamento:
// mostram escala e uso do espaço, não o que existe no imóvel (a tela diz
// isso). O que vem do anúncio — cômodos, nomes, áreas e as anotações da
// imobiliária (ex.: "lareira") — aparece como foi informado.
import { el } from './util.js';

const VENDOR = '../../vendor/three/';
const ESP = 0.12; // espessura da parede
const ALTURA = 1.5; // paredes em corte, como numa maquete
const PEITORIL = 0.95;
const SEM_PAREDES = new Set(['quintal', 'jardim', 'piscina', 'varanda', 'varanda-gourmet', 'garagem', 'circulacao']);
const CENTRAIS = new Set(['sala', 'circulacao', 'outro']);
const COM_JANELA = new Set(['sala', 'quarto', 'suite', 'escritorio', 'cozinha', 'banheiro', 'lavabo', 'area-de-servico', 'closet']);

function escala(comodos, aspecto, areaTotal) {
  const areaImagem = comodos.reduce((s, c) => s + c.w * aspecto * c.h, 0);
  let k = null;
  if (areaTotal && areaImagem) k = Math.sqrt(areaTotal / areaImagem);
  const comArea = comodos.filter((c) => c.area_m2);
  if (!k && comArea.length) {
    k = Math.sqrt(comArea.reduce((s, c) => s + c.area_m2, 0) / comArea.reduce((s, c) => s + c.w * aspecto * c.h, 0));
  }
  if (!k) k = 14 / aspecto;
  return Math.min(80, Math.max(4, k));
}

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

// ---------- Texturas desenhadas no navegador (nada baixado de fora) ----------
function texturaCanvas(THREE, largura, altura, desenhar, repetir = true) {
  const c = document.createElement('canvas');
  c.width = largura;
  c.height = altura;
  desenhar(c.getContext('2d'), largura, altura);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  if (repetir) {
    t.wrapS = THREE.RepeatWrapping;
    t.wrapT = THREE.RepeatWrapping;
  }
  t.anisotropy = 4;
  return t;
}

function madeira(THREE, base, semente, tabuas = 6) {
  return texturaCanvas(THREE, 512, 512, (g, w, h) => {
    const rnd = aleatorio(semente);
    const larg = w / tabuas;
    for (let i = 0; i < tabuas; i += 1) {
      let y = -rnd() * h;
      while (y < h) {
        const comp = h * (0.35 + rnd() * 0.45);
        const v = (rnd() - 0.5) * 22;
        g.fillStyle = `rgb(${base[0] + v},${base[1] + v * 0.8},${base[2] + v * 0.6})`;
        g.fillRect(i * larg, y, larg, comp);
        for (let k = 0; k < 7; k += 1) {
          g.strokeStyle = `rgba(60,35,15,${0.04 + rnd() * 0.05})`;
          g.lineWidth = 1 + rnd() * 1.5;
          g.beginPath();
          const x = i * larg + rnd() * larg;
          g.moveTo(x, y);
          g.bezierCurveTo(x + (rnd() - 0.5) * 8, y + comp / 3, x + (rnd() - 0.5) * 8, y + (2 * comp) / 3, x, y + comp);
          g.stroke();
        }
        g.fillStyle = 'rgba(40,25,10,0.35)';
        g.fillRect(i * larg, y, larg, 2);
        y += comp;
      }
      g.fillStyle = 'rgba(40,25,10,0.3)';
      g.fillRect(i * larg, 0, 2, h);
    }
  });
}

function porcelanato(THREE, base, rejunte) {
  return texturaCanvas(THREE, 512, 512, (g, w, h) => {
    const rnd = aleatorio(91);
    const n = 2;
    const lado = w / n;
    for (let i = 0; i < n; i += 1) {
      for (let j = 0; j < n; j += 1) {
        const v = (rnd() - 0.5) * 8;
        g.fillStyle = `rgb(${base[0] + v},${base[1] + v},${base[2] + v})`;
        g.fillRect(i * lado, j * lado, lado, lado);
        for (let k = 0; k < 40; k += 1) {
          g.fillStyle = `rgba(255,255,255,${rnd() * 0.06})`;
          g.fillRect(i * lado + rnd() * lado, j * lado + rnd() * lado, 2 + rnd() * 12, 1 + rnd() * 3);
        }
      }
    }
    g.fillStyle = rejunte;
    for (let i = 0; i <= n; i += 1) {
      g.fillRect(i * lado - 2, 0, 4, h);
      g.fillRect(0, i * lado - 2, w, 4);
    }
  });
}

function grama(THREE) {
  return texturaCanvas(THREE, 256, 256, (g, w, h) => {
    const rnd = aleatorio(5);
    g.fillStyle = '#6f9a4f';
    g.fillRect(0, 0, w, h);
    for (let i = 0; i < 2600; i += 1) {
      const v = rnd();
      g.fillStyle = v < 0.5 ? `rgba(70,110,45,${0.25 + rnd() * 0.3})` : `rgba(150,190,100,${0.15 + rnd() * 0.25})`;
      g.fillRect(rnd() * w, rnd() * h, 1 + rnd() * 2, 2 + rnd() * 5);
    }
  });
}

function concreto(THREE) {
  return texturaCanvas(THREE, 256, 256, (g, w, h) => {
    const rnd = aleatorio(17);
    g.fillStyle = '#b9b7b2';
    g.fillRect(0, 0, w, h);
    for (let i = 0; i < 1800; i += 1) {
      g.fillStyle = `rgba(${rnd() < 0.5 ? '90,90,90' : '235,235,230'},${rnd() * 0.12})`;
      g.fillRect(rnd() * w, rnd() * h, 1 + rnd() * 4, 1 + rnd() * 4);
    }
  });
}

function rotulo(THREE, nome, area, destaque) {
  const c = document.createElement('canvas');
  const g = c.getContext('2d');
  const fonteNome = '700 34px Manrope, Inter, system-ui, sans-serif';
  const fonteArea = '600 26px Inter, system-ui, sans-serif';
  g.font = fonteNome;
  const largNome = g.measureText(nome).width;
  g.font = fonteArea;
  const largArea = area ? g.measureText(area).width : 0;
  const largura = Math.ceil(Math.max(largNome, largArea)) + 40;
  const altura = area ? 92 : 60;
  c.width = largura;
  c.height = altura;
  g.fillStyle = destaque ? 'rgba(51,102,255,0.96)' : 'rgba(255,255,255,0.94)';
  g.beginPath();
  g.roundRect(0, 0, largura, altura, 16);
  g.fill();
  g.fillStyle = destaque ? '#ffffff' : '#0E1B3D';
  g.textBaseline = 'middle';
  g.font = fonteNome;
  g.fillText(nome, 20, area ? 32 : 31);
  if (area) {
    g.font = fonteArea;
    g.fillStyle = destaque ? 'rgba(255,255,255,0.85)' : '#5B6680';
    g.fillText(area, 20, 66);
  }
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: t, depthTest: false, transparent: true }));
  sprite.scale.set(largura / 95, altura / 95, 1);
  sprite.renderOrder = 10;
  return sprite;
}

// ---------- Móveis (cada um olha para +z, centrado na origem, no chão) ----------
function fabricaDeMoveis(THREE, RoundedBoxGeometry) {
  const cache = new Map();
  const geoArredondada = (w, h, d, r) => {
    const raio = Math.min(r, w / 2 - 0.001, h / 2 - 0.001, d / 2 - 0.001);
    const chave = `${w.toFixed(2)}|${h.toFixed(2)}|${d.toFixed(2)}|${raio.toFixed(3)}`;
    if (!cache.has(chave)) cache.set(chave, new RoundedBoxGeometry(w, h, d, 3, Math.max(raio, 0.002)));
    return cache.get(chave);
  };
  const geoCaixa = new THREE.BoxGeometry(1, 1, 1);
  const geoCilindro = new THREE.CylinderGeometry(1, 1, 1, 24);
  const geoEsfera = new THREE.SphereGeometry(1, 20, 14);
  const std = (cor, extra = {}) => new THREE.MeshStandardMaterial({ color: cor, roughness: 0.8, ...extra });
  const M = {
    tecido: std(0x8b919c), tecidoBege: std(0xc9b79c), tecidoAzul: std(0x3e4c66), almofada: std(0xe3d4b8), almofadaAzul: std(0x7f91b3),
    madeira: std(0x9b6b43, { roughness: 0.6 }), madeiraClara: std(0xc8a27a, { roughness: 0.6 }), branco: std(0xf3f2ef, { roughness: 0.45 }),
    preto: std(0x1f2228, { roughness: 0.3, metalness: 0.2 }), tela: std(0x0b0d12, { roughness: 0.15, metalness: 0.4 }),
    metal: std(0xa7adb5, { roughness: 0.3, metalness: 0.8 }), inox: std(0xc9ced4, { roughness: 0.25, metalness: 0.75 }),
    ceramica: std(0xffffff, { roughness: 0.15 }), pedra: std(0x3b3f47, { roughness: 0.35 }), pedraClara: std(0xd7d1c6, { roughness: 0.5 }),
    lencol: std(0xf6f4ef, { roughness: 0.9 }), manta: std(0x6f86a8, { roughness: 0.9 }), mantaTerra: std(0xb98a5e, { roughness: 0.9 }),
    tapete: std(0xd9d2c4, { roughness: 1 }), tapeteAzul: std(0x8ea0c0, { roughness: 1 }), folha: std(0x4c8a55, { roughness: 0.8, flatShading: true }),
    folhaEscura: std(0x2f6a40, { roughness: 0.8, flatShading: true }), vaso: std(0xb36a45, { roughness: 0.7 }), vasoClaro: std(0xe7e1d6, { roughness: 0.6 }),
    tijolo: std(0x9c4f35, { roughness: 0.85 }), vidro: new THREE.MeshStandardMaterial({ color: 0xbfd6ee, roughness: 0.05, metalness: 0.1, transparent: true, opacity: 0.32 }),
    agua: new THREE.MeshStandardMaterial({ color: 0x3fa6db, roughness: 0.05, metalness: 0.1, transparent: true, opacity: 0.82 }),
    fogo: new THREE.MeshBasicMaterial({ color: new THREE.Color(2.2, 1.0, 0.25) }), luz: new THREE.MeshBasicMaterial({ color: new THREE.Color(1.6, 1.45, 1.2) }),
    carro: std(0x2f4f8f, { roughness: 0.25, metalness: 0.55 }), pneu: std(0x16181c, { roughness: 0.9 }),
  };
  const peca = (grupo, geo, mat, [x, y, z], [sx, sy, sz] = [1, 1, 1], rot = null) => {
    const m = new THREE.Mesh(geo, mat);
    m.position.set(x, y, z);
    m.scale.set(sx, sy, sz);
    if (rot) m.rotation.set(...rot);
    m.castShadow = true;
    m.receiveShadow = true;
    grupo.add(m);
    return m;
  };
  const caixa = (g, mat, w, h, d, x, y, z, r = 0.02) => peca(g, geoArredondada(w, h, d, r), mat, [x, y + h / 2, z]);
  const cilindro = (g, mat, raio, h, x, y, z) => peca(g, geoCilindro, mat, [x, y + h / 2, z], [raio, h, raio]);
  const esfera = (g, mat, r, x, y, z, achatada = 1) => peca(g, geoEsfera, mat, [x, y, z], [r, r * achatada, r]);
  const G = () => new THREE.Group();

  const moveis = {
    sofa(L = 2.2, P = 0.92, mat = M.tecido) {
      const g = G();
      caixa(g, mat, L, 0.42, P, 0, 0.04, 0, 0.06);
      caixa(g, mat, L, 0.5, 0.24, 0, 0.36, -P / 2 + 0.12, 0.08);
      caixa(g, mat, 0.2, 0.62, P, -L / 2 + 0.1, 0.04, 0, 0.07);
      caixa(g, mat, 0.2, 0.62, P, L / 2 - 0.1, 0.04, 0, 0.07);
      const n = L > 1.9 ? 3 : 2;
      const lc = (L - 0.4) / n;
      for (let i = 0; i < n; i += 1) {
        caixa(g, mat, lc - 0.03, 0.12, P - 0.3, -L / 2 + 0.2 + lc * (i + 0.5), 0.46, 0.08, 0.05);
        caixa(g, i % 2 ? M.almofadaAzul : M.almofada, lc * 0.62, 0.36, 0.14, -L / 2 + 0.2 + lc * (i + 0.5), 0.5, -P / 2 + 0.3, 0.06);
      }
      for (const x of [-L / 2 + 0.12, L / 2 - 0.12]) cilindro(g, M.preto, 0.025, 0.05, x, 0, P / 2 - 0.12);
      return g;
    },
    poltrona(mat = M.tecidoBege) {
      const g = G();
      caixa(g, mat, 0.8, 0.4, 0.78, 0, 0.06, 0, 0.06);
      caixa(g, mat, 0.8, 0.5, 0.18, 0, 0.34, -0.3, 0.07);
      caixa(g, mat, 0.14, 0.56, 0.78, -0.33, 0.06, 0, 0.06);
      caixa(g, mat, 0.14, 0.56, 0.78, 0.33, 0.06, 0, 0.06);
      caixa(g, M.almofada, 0.5, 0.1, 0.55, 0, 0.46, 0.06, 0.04);
      return g;
    },
    mesaCentro(w = 1.1, d = 0.6) {
      const g = G();
      caixa(g, M.madeiraClara, w, 0.06, d, 0, 0.34, 0, 0.02);
      caixa(g, M.preto, w - 0.2, 0.3, d - 0.2, 0, 0.04, 0, 0.01);
      esfera(g, M.ceramica, 0.08, w * 0.2, 0.47, 0, 0.7);
      caixa(g, M.tapeteAzul, 0.3, 0.04, 0.22, -w * 0.18, 0.4, 0.02, 0.01);
      return g;
    },
    tapete(w, d, mat = M.tapete) {
      const g = G();
      const t = caixa(g, mat, w, 0.012, d, 0, 0, 0, 0.004);
      t.castShadow = false;
      return g;
    },
    rack(w = 1.8) {
      const g = G();
      caixa(g, M.madeira, w, 0.42, 0.42, 0, 0.06, 0, 0.02);
      caixa(g, M.preto, Math.min(1.35, w - 0.3), 0.76, 0.05, 0, 0.56, -0.05, 0.01);
      caixa(g, M.tela, Math.min(1.3, w - 0.35), 0.7, 0.01, 0, 0.59, -0.02, 0.003);
      cilindro(g, M.metal, 0.08, 0.04, 0, 0.48, -0.05);
      return g;
    },
    mesaJantar(w = 1.6, d = 0.9, lugares = 4) {
      const g = G();
      caixa(g, M.madeira, w, 0.05, d, 0, 0.72, 0, 0.02);
      for (const [sx, sz] of [[-1, -1], [1, -1], [-1, 1], [1, 1]]) caixa(g, M.preto, 0.05, 0.72, 0.05, sx * (w / 2 - 0.1), 0, sz * (d / 2 - 0.1), 0.01);
      const porLado = Math.max(1, Math.round((lugares - (lugares > 4 ? 2 : 0)) / 2));
      for (let i = 0; i < porLado; i += 1) {
        const x = -w / 2 + (w / porLado) * (i + 0.5);
        for (const s of [-1, 1]) {
          const c = moveis.cadeira();
          c.position.set(x, 0, s * (d / 2 + 0.22));
          c.rotation.y = s > 0 ? Math.PI : 0;
          g.add(c);
        }
      }
      if (lugares > 4) {
        for (const s of [-1, 1]) {
          const c = moveis.cadeira();
          c.position.set(s * (w / 2 + 0.22), 0, 0);
          c.rotation.y = s > 0 ? -Math.PI / 2 : Math.PI / 2;
          g.add(c);
        }
      }
      esfera(g, M.vasoClaro, 0.09, 0, 0.84, 0, 1.2);
      esfera(g, M.folha, 0.12, 0, 0.98, 0);
      return g;
    },
    cadeira() {
      const g = G();
      caixa(g, M.tecidoBege, 0.44, 0.06, 0.44, 0, 0.44, 0, 0.02);
      caixa(g, M.tecidoBege, 0.44, 0.42, 0.05, 0, 0.5, 0.2, 0.02);
      for (const [sx, sz] of [[-1, -1], [1, -1], [-1, 1], [1, 1]]) caixa(g, M.madeira, 0.035, 0.44, 0.035, sx * 0.18, 0, sz * 0.18, 0.005);
      return g;
    },
    cama(w = 1.6, comp = 2.0) {
      const g = G();
      caixa(g, M.madeira, w + 0.06, 0.3, comp, 0, 0.04, 0, 0.03);
      caixa(g, M.lencol, w, 0.22, comp - 0.06, 0, 0.32, 0.02, 0.07);
      caixa(g, M.tecidoAzul, w + 0.14, 0.95, 0.09, 0, 0.04, -comp / 2 + 0.04, 0.04);
      const travesseiros = w > 1.2 ? 2 : 1;
      for (let i = 0; i < travesseiros; i += 1) {
        const x = travesseiros === 1 ? 0 : (i ? 1 : -1) * w * 0.24;
        caixa(g, M.lencol, Math.min(0.62, w * 0.44), 0.13, 0.36, x, 0.53, -comp / 2 + 0.3, 0.06);
      }
      caixa(g, w > 1.2 ? M.manta : M.mantaTerra, w + 0.04, 0.05, comp * 0.42, 0, 0.53, comp * 0.27, 0.025);
      return g;
    },
    criadoMudo() {
      const g = G();
      caixa(g, M.madeiraClara, 0.46, 0.5, 0.4, 0, 0, 0, 0.02);
      cilindro(g, M.ceramica, 0.06, 0.18, 0, 0.5, 0);
      cilindro(g, M.luz, 0.11, 0.14, 0, 0.68, 0);
      return g;
    },
    guardaRoupa(w = 1.8) {
      const g = G();
      caixa(g, M.branco, w, 1.32, 0.6, 0, 0.02, 0, 0.015);
      const portas = Math.max(2, Math.round(w / 0.6));
      for (let i = 1; i < portas; i += 1) caixa(g, M.preto, 0.012, 1.24, 0.01, -w / 2 + (w / portas) * i, 0.06, 0.301, 0.002);
      for (let i = 0; i < portas; i += 1) caixa(g, M.metal, 0.02, 0.3, 0.02, -w / 2 + (w / portas) * (i + 0.5) + 0.12, 0.6, 0.31, 0.005);
      return g;
    },
    escrivaninha(w = 1.2) {
      const g = G();
      caixa(g, M.madeiraClara, w, 0.04, 0.6, 0, 0.72, 0, 0.01);
      caixa(g, M.branco, 0.42, 0.72, 0.56, -w / 2 + 0.22, 0, 0, 0.01);
      caixa(g, M.preto, 0.04, 0.72, 0.56, w / 2 - 0.04, 0, 0, 0.005);
      caixa(g, M.tela, 0.55, 0.34, 0.03, 0.1, 0.8, -0.18, 0.005);
      const c = moveis.cadeira();
      c.position.set(0.1, 0, 0.5);
      c.rotation.y = Math.PI;
      g.add(c);
      return g;
    },
    bancada(L = 2.4) {
      const g = G();
      caixa(g, M.branco, L, 0.86, 0.6, 0, 0, 0, 0.01);
      caixa(g, M.pedra, L + 0.02, 0.04, 0.63, 0, 0.86, 0.01, 0.01);
      caixa(g, M.inox, 0.62, 0.02, 0.42, -L * 0.18, 0.89, 0.02, 0.01);
      caixa(g, M.tela, 0.58, 0.015, 0.5, L * 0.22, 0.9, 0.02, 0.01);
      cilindro(g, M.metal, 0.018, 0.28, -L * 0.18, 0.9, -0.22);
      for (let i = 0; i < Math.floor(L / 0.6); i += 1) caixa(g, M.preto, 0.01, 0.7, 0.01, -L / 2 + 0.6 * (i + 1), 0.08, 0.301, 0.002);
      return g;
    },
    geladeira() {
      const g = G();
      caixa(g, M.inox, 0.7, 1.75, 0.68, 0, 0, 0, 0.03);
      caixa(g, M.preto, 0.01, 1.6, 0.01, 0.05, 0.08, 0.342, 0.002);
      caixa(g, M.metal, 0.03, 0.4, 0.03, -0.05, 0.9, 0.36, 0.01);
      return g;
    },
    vasoSanitario() {
      const g = G();
      cilindro(g, M.ceramica, 0.19, 0.4, 0, 0, 0.06);
      caixa(g, M.ceramica, 0.38, 0.36, 0.17, 0, 0.36, -0.15, 0.04);
      return g;
    },
    gabinete(w = 0.8) {
      const g = G();
      caixa(g, M.madeiraClara, w, 0.8, 0.46, 0, 0.04, 0, 0.015);
      caixa(g, M.pedraClara, w + 0.02, 0.03, 0.48, 0, 0.84, 0, 0.01);
      esfera(g, M.ceramica, 0.17, 0, 0.9, 0.02, 0.35);
      cilindro(g, M.metal, 0.015, 0.2, 0, 0.87, -0.17);
      caixa(g, M.vidro, w * 0.9, 0.6, 0.02, 0, 1.0, -0.22, 0.005);
      return g;
    },
    box(w = 0.9, d = 0.9) {
      const g = G();
      const piso = caixa(g, M.pedraClara, w, 0.03, d, 0, 0, 0, 0.005);
      piso.castShadow = false;
      caixa(g, M.vidro, 0.012, 1.35, d, w / 2, 0.03, 0, 0.004);
      cilindro(g, M.metal, 0.08, 0.02, 0, 1.35, -d / 2 + 0.15);
      return g;
    },
    maquinaLavar() {
      const g = G();
      caixa(g, M.branco, 0.6, 0.86, 0.6, 0, 0, 0, 0.03);
      peca(g, geoCilindro, M.preto, [0, 0.45, 0.301], [0.2, 0.02, 0.2], [Math.PI / 2, 0, 0]);
      peca(g, geoCilindro, M.vidro, [0, 0.45, 0.31], [0.16, 0.02, 0.16], [Math.PI / 2, 0, 0]);
      return g;
    },
    tanque() {
      const g = G();
      caixa(g, M.ceramica, 0.55, 0.86, 0.5, 0, 0, 0, 0.03);
      caixa(g, M.pedraClara, 0.45, 0.02, 0.38, 0, 0.86, 0.02, 0.01);
      return g;
    },
    churrasqueira() {
      const g = G();
      caixa(g, M.tijolo, 1.1, 0.9, 0.62, 0, 0, 0, 0.01);
      caixa(g, M.pedra, 1.14, 0.05, 0.66, 0, 0.9, 0, 0.01);
      caixa(g, M.preto, 0.7, 0.32, 0.02, 0, 1.0, 0.25, 0.005);
      caixa(g, M.fogo, 0.5, 0.05, 0.3, 0, 0.95, 0.05, 0.005);
      caixa(g, M.tijolo, 1.0, 0.5, 0.55, 0, 1.25, -0.03, 0.01);
      caixa(g, M.tijolo, 0.4, 0.4, 0.4, 0, 1.75, -0.05, 0.01);
      return g;
    },
    lareira() {
      const g = G();
      caixa(g, M.pedraClara, 1.4, 1.15, 0.5, 0, 0, 0, 0.02);
      caixa(g, M.preto, 0.8, 0.55, 0.05, 0, 0.15, 0.23, 0.01);
      caixa(g, M.fogo, 0.5, 0.16, 0.012, 0, 0.2, 0.262, 0.004);
      caixa(g, M.madeira, 1.5, 0.06, 0.56, 0, 1.15, 0, 0.01);
      return g;
    },
    espreguicadeira() {
      const g = G();
      caixa(g, M.branco, 0.65, 0.12, 1.8, 0, 0.18, 0, 0.03);
      peca(g, geoArredondada(0.65, 0.1, 0.7, 0.03), M.branco, [0, 0.42, -0.62], [1, 1, 1], [-0.6, 0, 0]);
      for (const [sx, sz] of [[-1, -1], [1, -1], [-1, 1], [1, 1]]) caixa(g, M.metal, 0.04, 0.18, 0.04, sx * 0.27, 0, sz * 0.8, 0.01);
      return g;
    },
    planta(alta = true) {
      const g = G();
      cilindro(g, alta ? M.vaso : M.vasoClaro, 0.17, 0.36, 0, 0, 0);
      esfera(g, M.folha, alta ? 0.32 : 0.24, 0, alta ? 0.78 : 0.56, 0);
      esfera(g, M.folhaEscura, alta ? 0.24 : 0.18, 0.12, alta ? 1.02 : 0.72, -0.05);
      return g;
    },
    arvore(h = 3.2) {
      const g = G();
      cilindro(g, M.madeira, 0.1, h * 0.55, 0, 0, 0);
      esfera(g, M.folha, h * 0.28, 0, h * 0.68, 0, 0.85);
      esfera(g, M.folhaEscura, h * 0.2, h * 0.14, h * 0.86, 0.05, 0.85);
      esfera(g, M.folha, h * 0.18, -h * 0.13, h * 0.8, -0.08, 0.85);
      return g;
    },
    arbusto(r = 0.45) {
      const g = G();
      esfera(g, M.folhaEscura, r, 0, r * 0.7, 0, 0.75);
      return g;
    },
    banco() {
      const g = G();
      caixa(g, M.madeira, 1.4, 0.06, 0.42, 0, 0.42, 0, 0.01);
      caixa(g, M.pedraClara, 0.12, 0.42, 0.4, -0.55, 0, 0, 0.01);
      caixa(g, M.pedraClara, 0.12, 0.42, 0.4, 0.55, 0, 0, 0.01);
      return g;
    },
    carro() {
      const g = G();
      caixa(g, M.carro, 1.78, 0.62, 4.2, 0, 0.22, 0, 0.2);
      caixa(g, M.vidro, 1.55, 0.5, 2.1, 0, 0.8, -0.15, 0.2);
      caixa(g, M.carro, 1.6, 0.06, 2.0, 0, 1.28, -0.15, 0.04);
      for (const [sx, sz] of [[-1, -1], [1, -1], [-1, 1], [1, 1]]) {
        peca(g, geoCilindro, M.pneu, [sx * 0.82, 0.34, sz * 1.3], [0.34, 0.24, 0.34], [0, 0, Math.PI / 2]);
      }
      return g;
    },
    estante(w = 1.0) {
      const g = G();
      caixa(g, M.madeiraClara, w, 1.3, 0.35, 0, 0, 0, 0.01);
      for (let i = 1; i < 4; i += 1) caixa(g, M.branco, w - 0.06, 0.02, 0.3, 0, i * 0.32, 0.02, 0.003);
      return g;
    },
  };
  return { moveis, M };
}

// ---------- Vizinhança entre cômodos: portas e janelas ----------
const LADOS = ['n', 's', 'o', 'l'];
const OPOSTO = { n: 's', s: 'n', o: 'l', l: 'o' };

function vizinhancas(ret) {
  // Para cada cômodo e cada lado: trechos (a..b, na coordenada local da parede) encostados em outro cômodo.
  const tol = 0.3;
  const viz = ret.map(() => ({ n: [], s: [], o: [], l: [] }));
  for (let i = 0; i < ret.length; i += 1) {
    for (let j = 0; j < ret.length; j += 1) {
      if (i === j) continue;
      const A = ret[i];
      const B = ret[j];
      const sobreX = [Math.max(A.x0, B.x0), Math.min(A.x1, B.x1)];
      const sobreZ = [Math.max(A.z0, B.z0), Math.min(A.z1, B.z1)];
      if (Math.abs(A.z0 - B.z1) < tol && sobreX[1] - sobreX[0] > 0.5) viz[i].n.push({ j, a: sobreX[0] - A.x0, b: sobreX[1] - A.x0 });
      if (Math.abs(A.z1 - B.z0) < tol && sobreX[1] - sobreX[0] > 0.5) viz[i].s.push({ j, a: sobreX[0] - A.x0, b: sobreX[1] - A.x0 });
      if (Math.abs(A.x0 - B.x1) < tol && sobreZ[1] - sobreZ[0] > 0.5) viz[i].o.push({ j, a: sobreZ[0] - A.z0, b: sobreZ[1] - A.z0 });
      if (Math.abs(A.x1 - B.x0) < tol && sobreZ[1] - sobreZ[0] > 0.5) viz[i].l.push({ j, a: sobreZ[0] - A.z0, b: sobreZ[1] - A.z0 });
    }
  }
  return viz;
}

function larguraDaAbertura(tipoA, tipoB) {
  const par = new Set([tipoA, tipoB]);
  const externo = ['varanda', 'varanda-gourmet', 'quintal', 'jardim', 'piscina'];
  if (par.has('sala') && externo.some((t) => par.has(t))) return 2.2;
  if (par.has('sala') && par.has('cozinha')) return 1.6;
  if (par.has('circulacao') || par.has('sala') || par.has('outro')) return 0.85;
  if (par.has('suite') && (par.has('banheiro') || par.has('closet'))) return 0.8;
  if (par.has('cozinha') && ['area-de-servico', 'despensa', 'varanda-gourmet', 'quintal', 'jardim'].some((t) => par.has(t))) return 0.85;
  if (par.has('quarto') && par.has('banheiro')) return 0.8;
  return 0;
}

function planejarAberturas(ret, viz) {
  // portas[i][lado] = [{a, b}] (trechos sem parede); janelas[i][lado] = [{a, b}]
  const portas = ret.map(() => ({ n: [], s: [], o: [], l: [] }));
  const janelas = ret.map(() => ({ n: [], s: [], o: [], l: [] }));
  const feitas = new Set();
  const abrir = (i, lado, v, largura) => {
    const j = v.j;
    const chave = i < j ? `${i}-${j}` : `${j}-${i}`;
    if (feitas.has(chave)) return;
    feitas.add(chave);
    const meio = (v.a + v.b) / 2;
    const w = Math.min(largura, v.b - v.a - 0.3);
    if (w < 0.6) return;
    portas[i][lado].push({ a: meio - w / 2, b: meio + w / 2 });
    // mesmo vão do outro lado (coordenada local do vizinho)
    const B = ret[j];
    const A = ret[i];
    const desloc = lado === 'n' || lado === 's' ? A.x0 - B.x0 : A.z0 - B.z0;
    portas[j][OPOSTO[lado]].push({ a: meio - w / 2 + desloc, b: meio + w / 2 + desloc });
  };
  for (let i = 0; i < ret.length; i += 1) {
    for (const lado of LADOS) {
      for (const v of viz[i][lado]) {
        const largura = larguraDaAbertura(ret[i].tipo, ret[v.j].tipo);
        if (largura) abrir(i, lado, v, largura);
      }
    }
  }
  // Cômodo fechado sem porta nenhuma ganha uma para o vizinho com que mais encosta.
  for (let i = 0; i < ret.length; i += 1) {
    if (SEM_PAREDES.has(ret[i].tipo)) continue;
    const temPorta = LADOS.some((l) => portas[i][l].length);
    if (temPorta) continue;
    let melhor = null;
    for (const lado of LADOS) for (const v of viz[i][lado]) if (!melhor || v.b - v.a > melhor.v.b - melhor.v.a) melhor = { lado, v };
    if (melhor) abrir(i, melhor.lado, melhor.v, 0.85);
  }
  // Janelas nas paredes externas (trechos sem vizinho).
  for (let i = 0; i < ret.length; i += 1) {
    const r = ret[i];
    if (!COM_JANELA.has(r.tipo)) continue;
    for (const lado of LADOS) {
      const comp = lado === 'n' || lado === 's' ? r.x1 - r.x0 : r.z1 - r.z0;
      const ocupados = [...viz[i][lado]].sort((p, q) => p.a - q.a);
      let cursor = 0;
      let livre = null;
      for (const o of [...ocupados, { a: comp, b: comp }]) {
        if (o.a - cursor > (livre ? livre.b - livre.a : 0)) livre = { a: cursor, b: o.a };
        cursor = Math.max(cursor, o.b);
      }
      if (!livre) continue;
      const pequena = r.tipo === 'banheiro' || r.tipo === 'lavabo' || r.tipo === 'area-de-servico';
      const w = Math.min(pequena ? 0.7 : 2.0, livre.b - livre.a - 0.5);
      if (w >= (pequena ? 0.5 : 1.0)) {
        const meio = (livre.a + livre.b) / 2;
        janelas[i][lado].push({ a: meio - w / 2, b: meio + w / 2 });
      }
    }
  }
  return { portas, janelas };
}

/**
 * Monta a planta humanizada em `container`.
 * opcoes: destaques (Map id → motivo), tipos (nomes dos tipos), aoClicar(comodo).
 */
export async function montarMaquete(container, { comodos, aspecto, area_m2: areaTotal }, opcoes = {}) {
  const { destaques = new Map(), tipos = {}, aoClicar } = opcoes;
  let THREE;
  let OrbitControls;
  let RoundedBoxGeometry;
  let RoomEnvironment;
  try {
    THREE = await import(`${VENDOR}three.module.min.js`);
    [{ OrbitControls }, { RoundedBoxGeometry }, { RoomEnvironment }] = await Promise.all([
      import(`${VENDOR}OrbitControls.js`), import(`${VENDOR}RoundedBoxGeometry.js`), import(`${VENDOR}RoomEnvironment.js`),
    ]);
  } catch {
    container.replaceChildren(el('p', 'aviso-3d', 'Seu navegador não conseguiu abrir a maquete 3D.'));
    return null;
  }
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true });
  } catch {
    container.replaceChildren(el('p', 'aviso-3d', 'Este aparelho não tem suporte a 3D (WebGL).'));
    return null;
  }
  const leve = matchMedia('(pointer: coarse)').matches || Math.min(screen.width, screen.height) < 700;
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, leve ? 1.5 : 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;

  const k = escala(comodos, aspecto, areaTotal);
  const larguraTotal = aspecto * k;
  const profTotal = k;
  const cena = new THREE.Scene();
  const fundo = new THREE.Color(0xe7ebf2);
  cena.background = fundo;
  cena.fog = new THREE.Fog(fundo, Math.max(larguraTotal, profTotal) * 2.2, Math.max(larguraTotal, profTotal) * 5);
  const pmrem = new THREE.PMREMGenerator(renderer);
  const ambiente = pmrem.fromScene(new RoomEnvironment(renderer), 0.04).texture;
  cena.environment = ambiente;

  const { moveis, M } = fabricaDeMoveis(THREE, RoundedBoxGeometry);
  const texturas = {
    madeira: madeira(THREE, [176, 132, 92], 3),
    madeiraEscura: madeira(THREE, [128, 88, 58], 8, 5),
    deck: madeira(THREE, [150, 108, 72], 11, 4),
    porcelanato: porcelanato(THREE, [226, 224, 219], 'rgba(160,156,150,0.8)'),
    porcelanatoEscuro: porcelanato(THREE, [176, 176, 172], 'rgba(120,118,115,0.9)'),
    grama: grama(THREE),
    concreto: concreto(THREE),
  };
  const PISO = {
    sala: ['madeira', 2.2], quarto: ['madeira', 2.2], suite: ['madeira', 2.2], escritorio: ['madeira', 2.2], closet: ['madeira', 2.2],
    circulacao: ['madeira', 2.2], outro: ['madeira', 2.2], cozinha: ['porcelanato', 1.2], banheiro: ['porcelanatoEscuro', 1.2],
    lavabo: ['porcelanatoEscuro', 1.2], 'area-de-servico': ['porcelanato', 1.2], despensa: ['porcelanato', 1.2],
    varanda: ['deck', 2.4], 'varanda-gourmet': ['deck', 2.4], quintal: ['grama', 3], jardim: ['grama', 3], garagem: ['concreto', 3], piscina: ['concreto', 3],
  };
  const materialPiso = (tipo, w, d) => {
    const [nome, tile] = PISO[tipo] || PISO.outro;
    const t = texturas[nome].clone();
    t.needsUpdate = true;
    t.repeat.set(w / tile, d / tile);
    return new THREE.MeshStandardMaterial({ map: t, roughness: nome.startsWith('porcelanato') ? 0.35 : 0.75, envMapIntensity: 0.5 });
  };
  const paredeLado = new THREE.MeshStandardMaterial({ color: 0xf8f7f4, roughness: 0.9, envMapIntensity: 0.4 });
  const paredeCorte = new THREE.MeshStandardMaterial({ color: 0x343b4c, roughness: 0.8 });
  const materiaisParede = [paredeLado, paredeLado, paredeCorte, paredeLado, paredeLado, paredeLado];
  const vidroJanela = new THREE.MeshStandardMaterial({ color: 0xa9c8ea, roughness: 0.05, metalness: 0.1, transparent: true, opacity: 0.38 });
  const caixilho = new THREE.MeshStandardMaterial({ color: 0x2b2f36, roughness: 0.4, metalness: 0.5 });
  const geoParede = new THREE.BoxGeometry(1, 1, 1);

  const grupo = new THREE.Group();
  grupo.position.set(-larguraTotal / 2, 0, -profTotal / 2);
  cena.add(grupo);

  // Chão de estúdio que recebe sombra
  const chao = new THREE.Mesh(new THREE.PlaneGeometry(larguraTotal * 8, profTotal * 8), new THREE.MeshStandardMaterial({ color: 0xe1e6ee, roughness: 1 }));
  chao.rotation.x = -Math.PI / 2;
  chao.position.set(larguraTotal / 2, -0.001, profTotal / 2);
  chao.receiveShadow = true;
  grupo.add(chao);
  const base = new THREE.Mesh(new THREE.BoxGeometry(larguraTotal + 0.6, 0.08, profTotal + 0.6), new THREE.MeshStandardMaterial({ color: 0xd2d8e2, roughness: 0.9 }));
  base.position.set(larguraTotal / 2, 0.04, profTotal / 2);
  base.receiveShadow = true;
  grupo.add(base);

  const ret = comodos.map((c) => {
    const x0 = c.x * aspecto * k;
    const z0 = c.y * k;
    return { c, tipo: c.tipo, x0, z0, x1: x0 + c.w * aspecto * k, z1: z0 + c.h * k };
  });
  const viz = vizinhancas(ret);
  const { portas, janelas } = planejarAberturas(ret, viz);

  const pisos = [];
  const contornos = new Map();
  ret.forEach((r, i) => {
    const { c } = r;
    const W = r.x1 - r.x0;
    const D = r.z1 - r.z0;
    const sala = new THREE.Group();
    sala.position.set(r.x0, 0.08, r.z0);
    grupo.add(sala);
    const destaque = destaques.has(c.id);
    const comParedes = !SEM_PAREDES.has(c.tipo);

    // Piso
    const piso = new THREE.Mesh(new THREE.BoxGeometry(Math.max(0.1, W - 0.02), 0.06, Math.max(0.1, D - 0.02)), materialPiso(c.tipo, W, D));
    piso.position.set(W / 2, 0.03, D / 2);
    piso.receiveShadow = true;
    piso.userData.comodo = c;
    sala.add(piso);
    pisos.push(piso);
    if (c.tipo === 'piscina') {
      const agua = new THREE.Mesh(new THREE.BoxGeometry(W * 0.8, 0.04, D * 0.76), M.agua);
      agua.position.set(W / 2, 0.08, D / 2);
      sala.add(agua);
    }
    // Contorno do cômodo (aparece ao passar o mouse e nos cômodos que bateram com o pedido)
    const linha = new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.BoxGeometry(W - 0.06, 0.02, D - 0.06)),
      new THREE.LineBasicMaterial({ color: destaque ? 0x3366ff : 0xffffff, transparent: true, opacity: destaque ? 1 : 0 }));
    linha.position.set(W / 2, 0.08, D / 2);
    sala.add(linha);
    contornos.set(c.id, linha);
    if (destaque) {
      const brilho = new THREE.Mesh(new THREE.PlaneGeometry(W - 0.1, D - 0.1), new THREE.MeshBasicMaterial({ color: 0x3366ff, transparent: true, opacity: 0.14, depthWrite: false }));
      brilho.rotation.x = -Math.PI / 2;
      brilho.position.set(W / 2, 0.065, D / 2);
      sala.add(brilho);
    }

    // Paredes com vãos de porta e janela
    if (comParedes) {
      for (const lado of LADOS) {
        const horizontal = lado === 'n' || lado === 's';
        const comp = horizontal ? W : D - 2 * ESP;
        const offset = horizontal ? 0 : ESP;
        const vaos = [...portas[i][lado].map((p) => ({ ...p, tipo: 'porta' })), ...janelas[i][lado].map((p) => ({ ...p, tipo: 'janela' }))]
          .map((v) => ({ ...v, a: Math.max(0, v.a - offset), b: Math.min(comp, v.b - offset) }))
          .filter((v) => v.b - v.a > 0.2)
          .sort((p, q) => p.a - q.a);
        const trechos = [];
        let cursor = 0;
        for (const v of vaos) {
          if (v.a > cursor) trechos.push({ a: cursor, b: v.a, h: ALTURA });
          if (v.tipo === 'janela') trechos.push({ a: v.a, b: v.b, h: PEITORIL, janela: true });
          cursor = Math.max(cursor, v.b);
        }
        if (cursor < comp) trechos.push({ a: cursor, b: comp, h: ALTURA });
        for (const t of trechos) {
          const len = t.b - t.a;
          if (len < 0.02) continue;
          const m = new THREE.Mesh(geoParede, materiaisParede);
          const meio = offset + (t.a + t.b) / 2;
          if (horizontal) {
            m.scale.set(len, t.h, ESP);
            m.position.set(meio, t.h / 2 + 0.06, lado === 'n' ? ESP / 2 : D - ESP / 2);
          } else {
            m.scale.set(ESP, t.h, len);
            m.position.set(lado === 'o' ? ESP / 2 : W - ESP / 2, t.h / 2 + 0.06, meio);
          }
          m.castShadow = true;
          m.receiveShadow = true;
          sala.add(m);
          if (t.janela) {
            const vidro = new THREE.Mesh(geoParede, vidroJanela);
            const quadro = new THREE.Mesh(geoParede, caixilho);
            const h = ALTURA - PEITORIL;
            if (horizontal) {
              vidro.scale.set(len, h, 0.02);
              vidro.position.set(meio, PEITORIL + h / 2 + 0.06, lado === 'n' ? ESP / 2 : D - ESP / 2);
              quadro.scale.set(len, 0.04, ESP + 0.02);
              quadro.position.set(meio, ALTURA + 0.06, lado === 'n' ? ESP / 2 : D - ESP / 2);
            } else {
              vidro.scale.set(0.02, h, len);
              vidro.position.set(lado === 'o' ? ESP / 2 : W - ESP / 2, PEITORIL + h / 2 + 0.06, meio);
              quadro.scale.set(ESP + 0.02, 0.04, len);
              quadro.position.set(lado === 'o' ? ESP / 2 : W - ESP / 2, ALTURA + 0.06, meio);
            }
            sala.add(vidro, quadro);
          }
        }
      }
    }

    const nenhum = { n: [], s: [], o: [], l: [] };
    mobiliar(THREE, sala, r, W, D, comParedes ? portas[i] : nenhum, comParedes ? janelas[i] : nenhum, moveis, M, i);

    const nome = c.nome || tipos[c.tipo] || c.tipo;
    const placa = rotulo(THREE, nome, c.area_m2 ? `${String(c.area_m2).replace('.', ',')} m²` : null, destaque);
    placa.position.set(W / 2, ALTURA + 0.55, D * 0.74);
    sala.add(placa);
  });

  // Luz de estúdio: céu suave, sol com sombra macia
  cena.add(new THREE.HemisphereLight(0xffffff, 0xdcd6cc, 0.85));
  const sol = new THREE.DirectionalLight(0xfff1df, 2.4);
  const maior = Math.max(larguraTotal, profTotal);
  sol.position.set(-maior * 0.55, maior * 1.4, maior * 0.75);
  sol.castShadow = true;
  sol.shadow.mapSize.set(leve ? 1024 : 2048, leve ? 1024 : 2048);
  Object.assign(sol.shadow.camera, { left: -maior, right: maior, top: maior, bottom: -maior, near: 0.5, far: maior * 4 });
  sol.shadow.bias = -0.0004;
  sol.shadow.normalBias = 0.02;
  cena.add(sol, sol.target);

  const camera = new THREE.PerspectiveCamera(35, 1, 0.1, 800);
  const alvo = new THREE.Vector3(0, 0.4, 0);
  const posicionar = (aspecto2) => {
    // Vista de cima a ~52°: a profundidade aparece encurtada, a largura não.
    const elev = THREE.MathUtils.degToRad(52);
    const giro = 0.2;
    const meiaV = Math.tan(THREE.MathUtils.degToRad(camera.fov / 2));
    const meiaH = meiaV * aspecto2;
    const projV = profTotal * Math.sin(elev) + (ALTURA + 1.3) * Math.cos(elev);
    const projH = larguraTotal * Math.cos(giro) + profTotal * Math.sin(giro);
    const d = Math.max(projV / 0.84 / 2 / meiaV, projH / 0.88 / 2 / meiaH);
    const h = d * Math.cos(elev);
    camera.position.set(alvo.x + h * Math.sin(giro), alvo.y + d * Math.sin(elev), alvo.z + h * Math.cos(giro));
  };
  posicionar(1.6);
  container.replaceChildren(renderer.domElement);
  renderer.domElement.setAttribute('role', 'img');
  renderer.domElement.setAttribute('aria-label', 'Planta humanizada em 3D. Arraste para girar, use dois dedos ou a roda do mouse para aproximar. Toque num cômodo para ver as fotos dele.');

  const controles = new OrbitControls(camera, renderer.domElement);
  controles.target.copy(alvo);
  controles.enableDamping = true;
  controles.dampingFactor = 0.08;
  controles.maxPolarAngle = Math.PI * 0.42;
  controles.minPolarAngle = Math.PI * 0.05;
  controles.minDistance = maior * 0.3;
  controles.maxDistance = maior * 3;
  controles.enablePan = false;
  controles.update();
  let mexeu = false;
  controles.addEventListener('start', () => { mexeu = true; });

  const ajustar = () => {
    const { width, height } = container.getBoundingClientRect();
    if (!width || !height) return;
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    if (!mexeu) {
      posicionar(camera.aspect);
      controles.update();
    }
  };
  const observador = new ResizeObserver(ajustar);
  observador.observe(container);
  ajustar();

  // Passar o mouse destaca o cômodo; tocar abre as fotos dele
  const raio = new THREE.Raycaster();
  const ponteiro = new THREE.Vector2();
  const sob = (e) => {
    const r = renderer.domElement.getBoundingClientRect();
    ponteiro.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    raio.setFromCamera(ponteiro, camera);
    const achado = raio.intersectObjects(pisos)[0];
    return achado ? achado.object.userData.comodo : null;
  };
  let sobId = null;
  renderer.domElement.addEventListener('pointermove', (e) => {
    if (e.pointerType === 'touch') return;
    const c = sob(e);
    renderer.domElement.style.cursor = c ? 'pointer' : 'grab';
    const id = c ? c.id : null;
    if (id === sobId) return;
    if (sobId !== null && !destaques.has(sobId)) contornos.get(sobId).material.opacity = 0;
    if (id !== null && !destaques.has(id)) contornos.get(id).material.opacity = 0.95;
    sobId = id;
  });
  let inicio = null;
  renderer.domElement.addEventListener('pointerdown', (e) => { inicio = [e.clientX, e.clientY]; });
  renderer.domElement.addEventListener('pointerup', (e) => {
    if (!inicio || Math.hypot(e.clientX - inicio[0], e.clientY - inicio[1]) > 6) return;
    const c = sob(e);
    if (c && aoClicar) aoClicar(c);
  });

  let ativo = true;
  const desenhar = () => {
    if (!ativo) return;
    requestAnimationFrame(desenhar);
    if (document.hidden) return;
    controles.update();
    renderer.render(cena, camera);
  };
  desenhar();

  return {
    destruir() {
      ativo = false;
      observador.disconnect();
      controles.dispose();
      cena.traverse((o) => {
        if (o.geometry) o.geometry.dispose();
        const mats = Array.isArray(o.material) ? o.material : o.material ? [o.material] : [];
        for (const m of mats) {
          if (m.map) m.map.dispose();
          m.dispose();
        }
      });
      Object.values(texturas).forEach((t) => t.dispose());
      ambiente.dispose();
      pmrem.dispose();
      renderer.dispose();
    },
  };
}

// ---------- Móveis por tipo de cômodo ----------
function livreNoTrecho(obstaculos, inicio, fim, largura) {
  // Meio do maior trecho livre entre `inicio` e `fim` em que o móvel cabe; null se não couber.
  const ocupados = obstaculos.filter((o) => o.b > inicio && o.a < fim).sort((p, q) => p.a - q.a);
  let cursor = inicio + 0.15;
  let melhor = null;
  for (const o of [...ocupados, { a: fim - 0.15, b: fim }]) {
    const espaco = o.a - cursor;
    if (espaco >= largura + 0.1 && (!melhor || espaco > melhor.b - melhor.a)) melhor = { a: cursor, b: o.a };
    cursor = Math.max(cursor, o.b + 0.1);
  }
  return melhor ? (melhor.a + melhor.b) / 2 : null;
}

function encostar(item, lado, ao, W, D, prof, recuo = ESP + 0.02) {
  if (lado === 'n') { item.position.set(ao, 0, recuo + prof / 2); item.rotation.y = 0; }
  if (lado === 's') { item.position.set(ao, 0, D - recuo - prof / 2); item.rotation.y = Math.PI; }
  if (lado === 'o') { item.position.set(recuo + prof / 2, 0, ao); item.rotation.y = Math.PI / 2; }
  if (lado === 'l') { item.position.set(W - recuo - prof / 2, 0, ao); item.rotation.y = -Math.PI / 2; }
}

function mobiliar(THREE, sala, r, W, D, portas, janelas, moveis, M, indice) {
  const tipo = r.tipo;
  const notas = `${r.c.nome || ''} ${r.c.notas || ''}`.toLowerCase();
  const comp = (lado) => (lado === 'n' || lado === 's' ? W : D);
  // Móvel alto (armário, TV, lareira, geladeira) não fica na frente de janela.
  const obstaculos = (lado, alto) => [...portas[lado], ...(alto ? janelas[lado] : [])];
  const paredes = (larg, ordem = ['n', 'o', 'l', 's'], alto = false) => {
    for (const lado of ordem) {
      const ao = livreNoTrecho(obstaculos(lado, alto), 0, comp(lado), larg);
      if (ao !== null) return { lado, ao };
    }
    return null;
  };
  const por = (item, larg, prof, ordem, alto = false) => {
    const p = paredes(larg, ordem, alto);
    if (!p) return null;
    encostar(item, p.lado, p.ao, W, D, prof);
    sala.add(item);
    return p;
  };
  const centro = (item, x, z, rot = 0) => { item.position.set(x, 0, z); item.rotation.y = rot; sala.add(item); };
  const lado = Math.min(W, D);
  const area = W * D;

  if (tipo === 'sala') {
    const largo = W >= D;
    const temJantar = area > 20;
    const zona = temJantar ? 0.58 : 1;
    const Wl = largo ? W * zona : W;
    const Dl = largo ? D : D * zona;
    const L = Math.min(2.4, Math.max(1.6, Wl * 0.55));
    const comLareira = notas.includes('lareira');
    const larg = comLareira ? 1.5 : Math.min(2, L);
    const prof = comLareira ? 0.5 : 0.42;
    const ao = livreNoTrecho(obstaculos('n', true), 0, Wl, larg);
    if (ao !== null) {
      // TV ou lareira na parede do fundo; o sofá de frente para ela (de costas para quem olha)
      const destaque = comLareira ? moveis.lareira() : moveis.rack(larg);
      encostar(destaque, 'n', ao, W, D, prof);
      sala.add(destaque);
      const zSofa = Math.max(ESP + prof + 1.6, Math.min(Dl - 0.62, ESP + prof + 3.1));
      const sofa = moveis.sofa(L);
      centro(sofa, ao, zSofa, Math.PI);
      const zMesa = (ESP + prof + zSofa - 0.46) / 2 + 0.15;
      centro(moveis.tapete(L + 0.5, Math.max(1.4, zSofa - ESP - prof - 0.2), M.tapete), ao, (ESP + prof + zSofa) / 2 + 0.1);
      centro(moveis.mesaCentro(Math.min(1.1, L * 0.5), 0.55), ao, zMesa);
      const xPoltrona = ao + L / 2 + 0.55;
      if (xPoltrona + 0.45 < Wl) centro(moveis.poltrona(), xPoltrona, zMesa, -Math.PI / 2);
      centro(moveis.planta(true), Math.max(0.45, ao - L / 2 - 0.5), ESP + 0.45);
    } else {
      const sofa = moveis.sofa(L);
      por(sofa, L, 0.92, ['o', 'l', 's']);
      centro(moveis.planta(true), 0.45, D - 0.45);
    }
    if (temJantar) {
      const mesa = moveis.mesaJantar(1.6, 0.9, area > 30 ? 6 : 4);
      if (largo) centro(mesa, Wl + (W - Wl) / 2, D / 2, Math.PI / 2);
      else centro(mesa, W / 2, Dl + (D - Dl) / 2);
    }
  } else if (tipo === 'quarto' || tipo === 'suite') {
    const casal = tipo === 'suite' || lado >= 3.0;
    const wCama = casal ? (tipo === 'suite' ? 1.6 : 1.4) : 0.9;
    const cama = moveis.cama(wCama, 2.0);
    const p = por(cama, wCama + (casal ? 1.0 : 0.5), 2.0, ['n', 'o', 'l', 's']);
    if (p) {
      const dx = wCama / 2 + 0.3;
      for (const s of casal ? [-1, 1] : [1]) {
        const cm = moveis.criadoMudo();
        encostar(cm, p.lado, p.ao + s * dx, W, D, 0.4);
        sala.add(cm);
      }
    }
    const roupa = moveis.guardaRoupa(Math.min(2.2, Math.max(1.2, (p && (p.lado === 'n' || p.lado === 's') ? W : D) * 0.45)));
    por(roupa, 1.6, 0.6, p ? [OPOSTO[p.lado], 'o', 'l', 'n', 's'] : ['s', 'o', 'l'], true);
    if (area > 14) centro(moveis.poltrona(M.tecidoAzul), W * 0.82, D * 0.78, -Math.PI * 0.75);
    else centro(moveis.planta(false), W - 0.4, D - 0.4);
  } else if (tipo === 'escritorio') {
    por(moveis.escrivaninha(Math.min(1.4, lado - 0.6)), Math.min(1.4, lado - 0.6), 0.6, ['n', 'o', 'l']);
    por(moveis.estante(1.0), 1.0, 0.35, ['l', 's', 'o'], true);
  } else if (tipo === 'cozinha') {
    const longo = W >= D ? 'n' : 'o';
    const L = Math.min((longo === 'n' ? W : D) - 1.2, 3.4);
    if (L > 1.2) {
      const banc = moveis.bancada(L);
      const p = por(banc, L, 0.6, [longo, longo === 'n' ? 'o' : 'n', 'l', 's']);
      const gel = moveis.geladeira();
      if (p) {
        encostar(gel, p.lado, Math.min(comp(p.lado) - 0.5, p.ao + L / 2 + 0.42), W, D, 0.68);
        sala.add(gel);
      }
    }
    if (area > 10 && lado > 2.6) centro(moveis.mesaJantar(1.1, 0.7, 4), W * 0.55, D * 0.62);
  } else if (tipo === 'banheiro' || tipo === 'lavabo') {
    por(moveis.gabinete(Math.min(0.9, lado * 0.45)), Math.min(0.9, lado * 0.45), 0.46, ['n', 'o', 'l', 's']);
    const vaso = moveis.vasoSanitario();
    por(vaso, 0.45, 0.6, ['o', 'l', 's', 'n']);
    if (tipo === 'banheiro' && area >= 3) {
      const box = moveis.box(Math.min(1.0, W - 0.3), Math.min(1.0, D - 0.3));
      centro(box, W - Math.min(1.0, W - 0.3) / 2 - ESP, D - Math.min(1.0, D - 0.3) / 2 - ESP);
    }
  } else if (tipo === 'area-de-servico') {
    const maq = moveis.maquinaLavar();
    const p = por(maq, 0.62, 0.6, ['n', 'o', 'l', 's']);
    if (p) {
      const tq = moveis.tanque();
      encostar(tq, p.lado, Math.min(comp(p.lado) - 0.4, p.ao + 0.65), W, D, 0.5);
      sala.add(tq);
    }
  } else if (tipo === 'closet') {
    por(moveis.guardaRoupa(Math.min(2, W - 0.4)), Math.min(2, W - 0.4), 0.6, ['n', 'o']);
    por(moveis.estante(Math.min(1.2, D - 0.6)), Math.min(1.2, D - 0.6), 0.35, ['l', 's']);
  } else if (tipo === 'varanda-gourmet') {
    por(moveis.churrasqueira(), 1.15, 0.62, ['n', 'l', 'o', 's']);
    if (area > 7) centro(moveis.mesaJantar(1.3, 0.8, 4), W / 2, D * 0.62);
  } else if (tipo === 'varanda') {
    centro(moveis.poltrona(M.tecidoBege), W * 0.3, D * 0.45, 0.3);
    if (W > 2.5) centro(moveis.poltrona(M.tecidoBege), W * 0.7, D * 0.45, -0.3);
    centro(moveis.planta(true), W - 0.4, 0.4);
  } else if (tipo === 'quintal' || tipo === 'jardim') {
    const rnd = aleatorio(indice * 31 + 7);
    const arvores = Math.max(1, Math.min(4, Math.round(area / 14)));
    for (let a = 0; a < arvores; a += 1) {
      centro(moveis.arvore(2.6 + rnd() * 1.4), 0.9 + rnd() * Math.max(0.1, W - 1.8), 0.9 + rnd() * Math.max(0.1, D - 1.8));
    }
    for (let a = 0; a < Math.round((W + D) / 2.5); a += 1) {
      const borda = rnd() < 0.5;
      centro(moveis.arbusto(0.3 + rnd() * 0.25), borda ? 0.35 : 0.35 + rnd() * (W - 0.7), borda ? 0.35 + rnd() * (D - 0.7) : D - 0.35);
    }
    if (W > 2.2 && D > 2.2) centro(moveis.banco(), W / 2, D / 2, rnd() * 0.4 - 0.2);
  } else if (tipo === 'piscina') {
    if (W > 3) centro(moveis.espreguicadeira(), 0.5, D / 2, 0);
  } else if (tipo === 'garagem') {
    if (lado >= 2.3) centro(moveis.carro(), W / 2, D / 2, W > D ? Math.PI / 2 : 0);
  }
}
