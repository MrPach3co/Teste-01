// Espelho de vendas de lançamentos: grade 2D (andares × unidades) e prédio 3D
// clicável, com as unidades coloridas por status. As cores sempre vêm com
// legenda e rótulo de texto — nunca só a cor.
import { el, reaisCurto } from './util.js';

export const STATUS = {
  disponivel: { rotulo: 'Disponível', cor: '#2F8253', cor3d: 0x2F8253 },
  reservada: { rotulo: 'Reservada', cor: '#C08A1E', cor3d: 0xD49A25 },
  vendida: { rotulo: 'Vendida', cor: '#9E978A', cor3d: 0xB4AEA2 },
};

export function legenda() {
  const caixa = el('div', 'espelho-legenda');
  for (const [chave, s] of Object.entries(STATUS)) {
    const item = el('span', `legenda-${chave}`);
    const cor = el('i');
    cor.style.background = s.cor;
    item.append(cor, document.createTextNode(s.rotulo));
    caixa.appendChild(item);
  }
  return caixa;
}

export function espelho2D(container, emp, { aoClicar, filtro = () => true, marcada = () => false } = {}) {
  container.replaceChildren();
  for (const torre of emp.torres) {
    const bloco = el('div', 'espelho-torre');
    if (emp.torres.length > 1) bloco.appendChild(el('h4', '', torre.nome));
    const grade = el('div', 'espelho-grade');
    grade.style.gridTemplateColumns = `auto repeat(${torre.unidades_por_andar}, minmax(64px, 1fr))`;
    for (let andar = torre.andares; andar >= 1; andar -= 1) {
      grade.appendChild(el('span', 'espelho-andar', `${andar}º`));
      for (let pos = 1; pos <= torre.unidades_por_andar; pos += 1) {
        const u = emp.unidades.find((x) => x.torre === torre.nome && x.andar === andar && x.posicao === pos);
        if (!u) { grade.appendChild(el('span')); continue; }
        const botao = el('button', `espelho-unidade status-${u.status}${filtro(u) ? '' : ' apagada'}${marcada(u) ? ' selecionada' : ''}`);
        if (marcada(u)) botao.setAttribute('aria-pressed', 'true');
        botao.type = 'button';
        botao.append(el('strong', '', u.codigo), el('small', '', STATUS[u.status].rotulo));
        if (u.preco && u.status !== 'vendida') botao.appendChild(el('small', '', reaisCurto(u.preco)));
        botao.setAttribute('aria-label', `Unidade ${u.codigo}, ${STATUS[u.status].rotulo}${u.tipologia ? `, ${u.tipologia}` : ''}`);
        botao.addEventListener('click', () => aoClicar && aoClicar(u));
        grade.appendChild(botao);
      }
    }
    bloco.appendChild(grade);
    container.appendChild(bloco);
  }
}

export async function espelho3D(container, emp, { aoClicar, filtro = () => true } = {}) {
  let THREE;
  let OrbitControls;
  try {
    THREE = await import('../../vendor/three/three.module.min.js');
    ({ OrbitControls } = await import('../../vendor/three/OrbitControls.js'));
  } catch {
    container.replaceChildren(el('p', 'aviso-3d', 'Seu navegador não conseguiu abrir a vista 3D.'));
    return null;
  }
  const L = 3.2;
  const A = 2.9;
  const P = 7;
  const folga = 0.18;
  const cena = new THREE.Scene();
  cena.background = new THREE.Color(0xF1EEE7);
  cena.add(new THREE.HemisphereLight(0xffffff, 0xb0a99a, 1.3));
  const sol = new THREE.DirectionalLight(0xffffff, 1.3);
  sol.position.set(30, 60, 40);
  cena.add(sol);

  const unidades = [];
  let deslocamento = 0;
  let alturaMax = 0;
  let larguraTotal = 0;
  for (const torre of emp.torres) {
    const largura = torre.unidades_por_andar * L;
    const base = new THREE.Mesh(new THREE.BoxGeometry(largura + 1, 1.2, P + 1),
      new THREE.MeshStandardMaterial({ color: 0xCFC8B8 }));
    base.position.set(deslocamento + largura / 2, 0.6, 0);
    cena.add(base);
    for (const u of emp.unidades.filter((x) => x.torre === torre.nome)) {
      const visivel = filtro(u);
      const material = new THREE.MeshStandardMaterial({
        color: STATUS[u.status].cor3d, roughness: 0.6, transparent: !visivel, opacity: visivel ? 1 : 0.18,
      });
      const caixa = new THREE.Mesh(new THREE.BoxGeometry(L - folga, A - folga, P), material);
      caixa.position.set(deslocamento + (u.posicao - 0.5) * L, 1.2 + (u.andar - 0.5) * A, 0);
      caixa.userData.unidade = u;
      cena.add(caixa);
      unidades.push(caixa);
    }
    alturaMax = Math.max(alturaMax, 1.2 + torre.andares * A);
    larguraTotal = deslocamento + largura;
    deslocamento += largura + 8;
  }
  const chao = new THREE.Mesh(new THREE.PlaneGeometry(larguraTotal + 60, 80), new THREE.MeshStandardMaterial({ color: 0xE3DED2 }));
  chao.rotation.x = -Math.PI / 2;
  chao.position.set(larguraTotal / 2, 0, 0);
  cena.add(chao);

  const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 1000);
  const centro = new THREE.Vector3(larguraTotal / 2, alturaMax / 2, 0);
  const distancia = Math.max(alturaMax, larguraTotal) * 1.6;
  camera.position.set(centro.x + distancia * 0.45, alturaMax * 0.75, distancia);
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  const dica = el('div', 'espelho-dica');
  dica.hidden = true;
  container.replaceChildren(renderer.domElement, dica);
  renderer.domElement.setAttribute('aria-label', 'Prédio em 3D com as unidades coloridas por status. Toque numa unidade.');
  renderer.domElement.setAttribute('role', 'img');

  const controles = new OrbitControls(camera, renderer.domElement);
  controles.target.copy(centro);
  controles.enableDamping = true;
  controles.maxPolarAngle = Math.PI * 0.49;
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
  const alvo = (e) => {
    const r = renderer.domElement.getBoundingClientRect();
    ponteiro.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    raio.setFromCamera(ponteiro, camera);
    const achado = raio.intersectObjects(unidades)[0];
    return achado ? achado.object.userData.unidade : null;
  };
  renderer.domElement.addEventListener('pointermove', (e) => {
    const u = alvo(e);
    renderer.domElement.style.cursor = u ? 'pointer' : 'grab';
    if (!u) { dica.hidden = true; return; }
    const r = container.getBoundingClientRect();
    dica.textContent = `Unidade ${u.codigo} · ${STATUS[u.status].rotulo}`;
    dica.style.left = `${e.clientX - r.left + 12}px`;
    dica.style.top = `${e.clientY - r.top - 30}px`;
    dica.hidden = false;
  });
  let inicio = null;
  renderer.domElement.addEventListener('pointerdown', (e) => { inicio = [e.clientX, e.clientY]; });
  renderer.domElement.addEventListener('pointerup', (e) => {
    if (!inicio || Math.hypot(e.clientX - inicio[0], e.clientY - inicio[1]) > 6) return;
    const u = alvo(e);
    if (u && aoClicar) aoClicar(u);
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
      cena.traverse((o) => { if (o.geometry) o.geometry.dispose(); if (o.material) o.material.dispose(); });
      renderer.dispose();
    },
  };
}
