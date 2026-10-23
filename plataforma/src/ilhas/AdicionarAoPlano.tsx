// Botão "Adicionar ao planejador" da página da receita.
import { useEffect, useRef, useState } from "preact/hooks";
import { adicionarAoPlano, lerPlano } from "../lib/plano";
import { DIAS, REFEICOES } from "../lib/comum.mjs";

type Props = { receita: string; titulo: string; refeicoes: string[] };

export default function AdicionarAoPlano({ receita, titulo, refeicoes }: Props) {
  const [aberto, setAberto] = useState(false);
  const [dia, setDia] = useState(() => (new Date().getDay() + 6) % 7);
  const [refeicao, setRefeicao] = useState(refeicoes[0]);
  const [porcoes, setPorcoes] = useState(2);
  const [confirmacao, setConfirmacao] = useState("");
  const painel = useRef<HTMLDivElement>(null);

  useEffect(() => setPorcoes(lerPlano().porcoesPadrao), []);

  useEffect(() => {
    if (!aberto) return;
    const fora = (e: MouseEvent) => painel.current && !painel.current.contains(e.target as Node) && setAberto(false);
    const esc = (e: KeyboardEvent) => e.key === "Escape" && setAberto(false);
    document.addEventListener("mousedown", fora);
    document.addEventListener("keydown", esc);
    return () => { document.removeEventListener("mousedown", fora); document.removeEventListener("keydown", esc); };
  }, [aberto]);

  function adicionar() {
    adicionarAoPlano({ receita, dia, refeicao, porcoes });
    setAberto(false);
    setConfirmacao(`${DIAS[dia]} · ${REFEICOES[refeicao as keyof typeof REFEICOES]}`);
  }

  return (
    <div class="adicionar" ref={painel}>
      <button type="button" class="btn" aria-expanded={aberto} onClick={() => setAberto(!aberto)}>
        <span aria-hidden="true">＋</span> Adicionar ao planejador
      </button>

      {aberto && (
        <div class="adicionar__painel" role="dialog" aria-label={`Adicionar ${titulo} ao planejador`}>
          <label>
            <span>Dia</span>
            <select value={dia} onChange={(e) => setDia(Number(e.currentTarget.value))}>
              {DIAS.map((d, i) => <option value={i}>{d}</option>)}
            </select>
          </label>
          <label>
            <span>Refeição</span>
            <select value={refeicao} onChange={(e) => setRefeicao(e.currentTarget.value)}>
              {Object.entries(REFEICOES).map(([v, r]) => <option value={v}>{r}</option>)}
            </select>
          </label>
          <label>
            <span>Porções</span>
            <input type="number" min={1} max={20} value={porcoes}
              onInput={(e) => setPorcoes(Math.max(1, Math.min(20, Number(e.currentTarget.value) || 1)))} />
          </label>
          <button type="button" class="btn btn--acento" onClick={adicionar}>Adicionar</button>
        </div>
      )}

      {confirmacao && (
        <p class="adicionar__ok" role="status">
          ✓ Adicionada em {confirmacao}. <a href="/planejador">Ver planejador</a>
        </p>
      )}
    </div>
  );
}
