// Lista de compras gerada a partir do planejador: soma ingredientes
// repetidos, ajusta pelas porções e organiza por seção do mercado.
import { useEffect, useMemo, useState } from "preact/hooks";
import { lerPlano, aoAtualizar, type Plano } from "../lib/plano";
import { formatarMoeda, montarListaDeCompras } from "../lib/comum.mjs";

type Props = { receitas: Record<string, any>; marca: string; referenciaCusto: string };

const CHAVE_MARCADOS = "lista-compras:marcados:v1";

function lerMarcados(): string[] {
  try { return JSON.parse(localStorage.getItem(CHAVE_MARCADOS) ?? "[]"); } catch { return []; }
}

export default function ListaCompras({ receitas, marca, referenciaCusto }: Props) {
  const [plano, setPlano] = useState<Plano | null>(null);
  const [marcados, setMarcados] = useState<string[]>([]);
  const [copiado, setCopiado] = useState(false);

  useEffect(() => {
    setPlano(lerPlano());
    setMarcados(lerMarcados());
    return aoAtualizar(setPlano);
  }, []);

  const entradas = (plano?.entradas ?? []).filter((e) => receitas[e.receita]);
  const lista = useMemo(() => montarListaDeCompras(entradas, receitas), [plano, receitas]);
  const todos = [...lista.secoes.flatMap((s) => s.itens), ...lista.despensa];
  const noCarrinho = todos.filter((i) => marcados.includes(i.chave)).length;

  const receitasDaSemana = useMemo(() => {
    const contagem = new Map<string, number>();
    entradas.forEach((e) => contagem.set(e.receita, (contagem.get(e.receita) ?? 0) + 1));
    return [...contagem].map(([slug, vezes]) => ({ ...receitas[slug], vezes }));
  }, [plano, receitas]);

  function alternar(chave: string) {
    const novo = marcados.includes(chave) ? marcados.filter((c) => c !== chave) : [...marcados, chave];
    setMarcados(novo);
    try { localStorage.setItem(CHAVE_MARCADOS, JSON.stringify(novo)); } catch { /* só nesta visita */ }
  }

  function desmarcarTudo() {
    setMarcados([]);
    try { localStorage.removeItem(CHAVE_MARCADOS); } catch { /* ignora */ }
  }

  function comoTexto() {
    const linhas = [`🛒 Lista de compras · ${marca}`, `${lista.refeicoes} refeições planejadas`, ""];
    for (const s of lista.secoes) {
      linhas.push(`*${s.rotulo}*`);
      s.itens.forEach((i) => linhas.push(`- ${i.nome}: ${i.texto}`));
      linhas.push("");
    }
    if (lista.despensa.length) {
      linhas.push("*Confira na despensa*");
      lista.despensa.forEach((i) => linhas.push(`- ${i.nome}${i.quantidade != null ? `: ${i.texto}` : ""}`));
    }
    return linhas.join("\n").trim();
  }

  async function copiar() {
    try {
      await navigator.clipboard.writeText(comoTexto());
      setCopiado(true);
      setTimeout(() => setCopiado(false), 2200);
    } catch {
      prompt("Copie a lista abaixo:", comoTexto());
    }
  }

  if (!plano) return <p class="lista__carregando">Carregando sua lista…</p>;

  if (!entradas.length) {
    return (
      <div class="lista__vazia">
        <span class="lista__vazia-icone" aria-hidden="true">🛒</span>
        <h2>Sua lista está vazia</h2>
        <p>Adicione receitas ao planejador e a lista de compras aparece aqui, com os ingredientes somados.</p>
        <a href="/planejador" class="btn">Ir para o planejador →</a>
      </div>
    );
  }

  return (
    <div class="lista">
      <div class="lista__resumo">
        <div class="lista__numeros">
          <div><strong>{lista.refeicoes}</strong><span>refeições</span></div>
          <div><strong>{receitasDaSemana.length}</strong><span>receitas</span></div>
          <div><strong>{todos.length}</strong><span>itens</span></div>
          <div><strong>{formatarMoeda(lista.custoTotal)}</strong><span>custo estimado</span></div>
        </div>
        <div class="lista__progresso" aria-label={`${noCarrinho} de ${todos.length} itens marcados`}>
          <span style={{ width: `${todos.length ? (noCarrinho / todos.length) * 100 : 0}%` }}></span>
        </div>
        <p class="lista__progresso-texto">{noCarrinho} de {todos.length} itens no carrinho</p>
        <div class="lista__acoes">
          <button type="button" class="btn btn--pequeno" onClick={copiar}>{copiado ? "✓ Copiada" : "Copiar lista"}</button>
          <a class="btn btn--contorno btn--pequeno" href={`https://wa.me/?text=${encodeURIComponent(comoTexto())}`} target="_blank" rel="noopener">Enviar no WhatsApp</a>
          <button type="button" class="btn btn--contorno btn--pequeno" onClick={() => window.print()}>Imprimir</button>
          {noCarrinho > 0 && <button type="button" class="link-acao" onClick={desmarcarTudo}>Desmarcar tudo</button>}
        </div>
      </div>

      <div class="lista__colunas">
        <div class="lista__secoes">
          {lista.secoes.map((s) => (
            <section class="lista__secao">
              <h2>{s.rotulo} <small>{s.itens.length}</small></h2>
              <ul>{s.itens.map((i) => <Linha item={i} marcado={marcados.includes(i.chave)} aoAlternar={() => alternar(i.chave)} />)}</ul>
            </section>
          ))}
          {lista.despensa.length > 0 && (
            <section class="lista__secao lista__secao--despensa">
              <h2>Confira na despensa <small>{lista.despensa.length}</small></h2>
              <p>Itens que costumam estar em casa. Marque o que já tem.</p>
              <ul>{lista.despensa.map((i) => <Linha item={i} marcado={marcados.includes(i.chave)} aoAlternar={() => alternar(i.chave)} />)}</ul>
            </section>
          )}
        </div>

        <aside class="lista__receitas">
          <h2>Receitas da semana</h2>
          <ul>
            {receitasDaSemana.map((r) => (
              <li><a href={`/receitas/${r.slug}`}>{r.titulo}</a>{r.vezes > 1 && <span>{r.vezes}×</span>}</li>
            ))}
          </ul>
          <a href="/planejador" class="btn btn--contorno btn--pequeno">Editar planejamento</a>
          <p class="lista__nota">Quantidades somadas das receitas, ajustadas às porções escolhidas e arredondadas para cima quando necessário. {referenciaCusto}</p>
        </aside>
      </div>
    </div>
  );
}

function Linha({ item, marcado, aoAlternar }: { item: any; marcado: boolean; aoAlternar: () => void }) {
  return (
    <li class={marcado ? "marcado" : ""}>
      <label>
        <input type="checkbox" checked={marcado} onChange={aoAlternar} />
        <span class="lista__nome">
          {item.nome}
          <small title={item.receitas.join(" · ")}>
            {item.receitas.length > 2 ? `em ${item.receitas.length} receitas` : item.receitas.join(" · ")}
          </small>
        </span>
        <span class="lista__qtd">{item.texto}</span>
      </label>
    </li>
  );
}
