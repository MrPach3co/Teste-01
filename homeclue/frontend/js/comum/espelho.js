// Espelho de vendas de lançamentos: grade 2D (andares × unidades), com as
// unidades coloridas por status. As cores sempre vêm com legenda e rótulo de
// texto — nunca só a cor. O prédio 3D fica em predio3d.js.
import { el, reaisCurto } from './util.js';

export const STATUS = {
  disponivel: { rotulo: 'Disponível', cor: '#1E8E4F' },
  reservada: { rotulo: 'Reservada', cor: '#B26B00' },
  vendida: { rotulo: 'Vendida', cor: '#C2412E' },
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
