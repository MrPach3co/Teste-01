// Maquete 3D gerada a partir da planta: cada cômodo desenhado pela
// imobiliária vira um "cômodo de casa de bonecas" (piso + paredes baixas),
// na escala da área do imóvel. Clicar num cômodo mostra as fotos dele.
// É uma maquete esquemática — não substitui um modelo 3D feito por arquiteto.
import { el } from './util.js';

const CORES = {
  sala: 0xE9DFC9, cozinha: 0xF1D9B5, quarto: 0xD8E2EC, suite: 0xCADBEA, banheiro: 0xD2E9E6, lavabo: 0xD2E9E6,
  varanda: 0xE6E0D2, 'varanda-gourmet': 0xE8D5BC, 'area-de-servico': 0xE2E2DA, escritorio: 0xE0D9EB,
  closet: 0xE6D9E6, garagem: 0xD3D0C8, quintal: 0xB9D6A8, jardim: 0xADD19A, piscina: 0x8BC6E6,
  despensa: 0xE2E2DA, circulacao: 0xEFEBE3, outro: 0xE4E0D7,
};
const SEM_PAREDES = new Set(['quintal', 'jardim', 'piscina', 'varanda', 'varanda-gourmet', 'garagem', 'circulacao']);
const COR_DESTAQUE = 0xC8653A;

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

function rotulo(THREE, texto, destaque) {
  const tela = document.createElement('canvas');
  const ctx = tela.getContext('2d');
  const fonte = '600 40px Inter, system-ui, sans-serif';
  ctx.font = fonte;
  const largura = Math.ceil(ctx.measureText(texto).width) + 36;
  tela.width = largura; tela.height = 64;
  ctx.font = fonte;
  ctx.fillStyle = destaque ? 'rgba(156,74,38,0.95)' : 'rgba(255,253,249,0.92)';
  ctx.beginPath();
  ctx.roundRect(0, 0, largura, 64, 14);
  ctx.fill();
  ctx.fillStyle = destaque ? '#FFFDF9' : '#1B1A17';
  ctx.textBaseline = 'middle';
  ctx.fillText(texto, 18, 34);
  const textura = new THREE.CanvasTexture(tela);
  textura.colorSpace = THREE.SRGBColorSpace;
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: textura, depthTest: false, transparent: true }));
  sprite.scale.set(largura / 75, 64 / 75, 1);
  sprite.renderOrder = 10;
  return sprite;
}

export async function montarMaquete(container, { comodos, aspecto, area_m2: areaTotal }, opcoes = {}) {
  const { destaques = new Map(), tipos = {}, aoClicar } = opcoes;
  let THREE;
  let OrbitControls;
  try {
    THREE = await import('../../vendor/three/three.module.min.js');
    ({ OrbitControls } = await import('../../vendor/three/OrbitControls.js'));
  } catch {
    container.replaceChildren(el('p', 'aviso-3d', 'Seu navegador não conseguiu abrir a maquete 3D.'));
    return null;
  }
  const teste = document.createElement('canvas');
  if (!(teste.getContext('webgl2') || teste.getContext('webgl'))) {
    container.replaceChildren(el('p', 'aviso-3d', 'Este aparelho não tem suporte a 3D (WebGL).'));
    return null;
  }

  const k = escala(comodos, aspecto, areaTotal);
  const largura = aspecto * k;
  const profundidade = k;
  const cena = new THREE.Scene();
  cena.background = new THREE.Color(0xF1EEE7);
  cena.add(new THREE.HemisphereLight(0xffffff, 0xb9b2a3, 1.25));
  const sol = new THREE.DirectionalLight(0xffffff, 1.4);
  sol.position.set(largura * 0.4, 22, profundidade * 0.2);
  cena.add(sol);

  const grupo = new THREE.Group();
  grupo.position.set(-largura / 2, 0, -profundidade / 2);
  cena.add(grupo);

  const chao = new THREE.Mesh(new THREE.PlaneGeometry(largura * 3, profundidade * 3),
    new THREE.MeshStandardMaterial({ color: 0xE3DED2, roughness: 1 }));
  chao.rotation.x = -Math.PI / 2;
  chao.position.set(largura / 2, -0.01, profundidade / 2);
  grupo.add(chao);

  const parede = new THREE.MeshStandardMaterial({ color: 0xFBF8F2, roughness: 0.9 });
  const alturaParede = 1.15;
  const espessura = 0.1;
  const pisos = [];
  for (const c of comodos) {
    const x0 = c.x * aspecto * k;
    const z0 = c.y * k;
    const w = c.w * aspecto * k;
    const d = c.h * k;
    const destaque = destaques.has(c.id);
    const piso = new THREE.Mesh(new THREE.BoxGeometry(Math.max(0.1, w - 0.05), 0.1, Math.max(0.1, d - 0.05)),
      new THREE.MeshStandardMaterial({ color: destaque ? COR_DESTAQUE : (CORES[c.tipo] ?? CORES.outro), roughness: 0.85 }));
    piso.position.set(x0 + w / 2, 0.05, z0 + d / 2);
    piso.userData.comodo = c;
    grupo.add(piso);
    pisos.push(piso);
    if (c.tipo === 'piscina') {
      const agua = new THREE.Mesh(new THREE.BoxGeometry(w * 0.8, 0.06, d * 0.8),
        new THREE.MeshStandardMaterial({ color: 0x4FA8D8, transparent: true, opacity: 0.85 }));
      agua.position.set(x0 + w / 2, 0.13, z0 + d / 2);
      grupo.add(agua);
    }
    if (!SEM_PAREDES.has(c.tipo)) {
      const lados = [
        [w, espessura, x0 + w / 2, z0], [w, espessura, x0 + w / 2, z0 + d],
        [espessura, d, x0, z0 + d / 2], [espessura, d, x0 + w, z0 + d / 2],
      ];
      for (const [lx, lz, px, pz] of lados) {
        const m = new THREE.Mesh(new THREE.BoxGeometry(lx, alturaParede, lz), parede);
        m.position.set(px, alturaParede / 2 + 0.05, pz);
        grupo.add(m);
      }
    }
    const nome = c.nome || tipos[c.tipo] || c.tipo;
    const placa = rotulo(THREE, nome, destaque);
    placa.position.set(x0 + w / 2, alturaParede + 0.9, z0 + d / 2);
    grupo.add(placa);
  }

  const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 500);
  const maior = Math.max(largura, profundidade);
  camera.position.set(maior * 0.2, maior * 0.72, maior * 0.78);
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  container.replaceChildren(renderer.domElement);
  renderer.domElement.setAttribute('aria-label', 'Maquete 3D do imóvel. Arraste para girar, use dois dedos ou a roda do mouse para aproximar.');
  renderer.domElement.setAttribute('role', 'img');

  const controles = new OrbitControls(camera, renderer.domElement);
  controles.target.set(0, 0, 0);
  controles.enableDamping = true;
  controles.maxPolarAngle = Math.PI * 0.46;
  controles.minDistance = maior * 0.35;
  controles.maxDistance = maior * 2.6;
  controles.update();

  const ajustar = () => {
    const { width, height } = container.getBoundingClientRect();
    if (!width || !height) return;
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  };
  const observador = new ResizeObserver(ajustar);
  observador.observe(container);
  ajustar();

  const raio = new THREE.Raycaster();
  const ponteiro = new THREE.Vector2();
  let inicio = null;
  renderer.domElement.addEventListener('pointerdown', (e) => { inicio = [e.clientX, e.clientY]; });
  renderer.domElement.addEventListener('pointerup', (e) => {
    if (!inicio || Math.hypot(e.clientX - inicio[0], e.clientY - inicio[1]) > 6) return;
    const r = renderer.domElement.getBoundingClientRect();
    ponteiro.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    raio.setFromCamera(ponteiro, camera);
    const achado = raio.intersectObjects(pisos)[0];
    if (achado && aoClicar) aoClicar(achado.object.userData.comodo);
  });

  let ativo = true;
  const desenhar = () => {
    if (!ativo) return;
    controles.update();
    renderer.render(cena, camera);
    requestAnimationFrame(desenhar);
  };
  desenhar();

  return {
    destruir() {
      ativo = false;
      observador.disconnect();
      controles.dispose();
      cena.traverse((o) => {
        if (o.geometry) o.geometry.dispose();
        if (o.material) {
          if (o.material.map) o.material.map.dispose();
          o.material.dispose();
        }
      });
      renderer.dispose();
    },
  };
}
