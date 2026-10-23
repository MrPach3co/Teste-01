// Planejamento semanal salvo no navegador (localStorage).
// Versão de demonstração: sem login, cada pessoa vê só o próprio plano.
// Componentes diferentes (planejador, lista, botão "adicionar") ficam
// sincronizados pelo evento "plano:atualizado".

export type Entrada = {
  id: string;
  receita: string;   // slug
  dia: number;       // 0 = segunda … 6 = domingo
  refeicao: string;  // cafe-da-manha | almoco | lanche | jantar
  porcoes: number;
};

export type Plano = { versao: 1; entradas: Entrada[]; porcoesPadrao: number };

const CHAVE = "plano-semanal:v1";
const EVENTO = "plano:atualizado";
const vazio = (): Plano => ({ versao: 1, entradas: [], porcoesPadrao: 2 });

export function lerPlano(): Plano {
  try {
    const bruto = localStorage.getItem(CHAVE);
    if (!bruto) return vazio();
    const plano = JSON.parse(bruto);
    if (plano?.versao !== 1 || !Array.isArray(plano.entradas)) return vazio();
    return plano;
  } catch {
    return vazio();
  }
}

export function salvarPlano(plano: Plano) {
  try {
    localStorage.setItem(CHAVE, JSON.stringify(plano));
  } catch {
    // navegação privada ou armazenamento cheio: o plano vale só nesta visita
  }
  window.dispatchEvent(new CustomEvent(EVENTO, { detail: plano }));
}

export function aoAtualizar(callback: (plano: Plano) => void) {
  const local = (e: Event) => callback((e as CustomEvent<Plano>).detail);
  const outraAba = (e: StorageEvent) => e.key === CHAVE && callback(lerPlano());
  window.addEventListener(EVENTO, local);
  window.addEventListener("storage", outraAba);
  return () => {
    window.removeEventListener(EVENTO, local);
    window.removeEventListener("storage", outraAba);
  };
}

export const novoId = () => Math.random().toString(36).slice(2, 10);

export function adicionarAoPlano(dados: Omit<Entrada, "id">) {
  const plano = lerPlano();
  plano.entradas.push({ ...dados, id: novoId() });
  salvarPlano(plano);
}
