// Planejador semanal (demonstração, salvo no navegador).
// Computador: arraste receitas da lateral para os dias, ou entre os dias.
// Celular: escolha o dia nas abas e toque em "+" na refeição.
import { useEffect, useMemo, useRef, useState } from "preact/hooks";
import type { JSX } from "preact";
import { lerPlano, salvarPlano, aoAtualizar, novoId, type Plano, type Entrada } from "../lib/plano";
import { DIAS, DIAS_CURTOS, REFEICOES, formatarMoeda, formatarTempo, montarListaDeCompras } from "../lib/comum.mjs";

type ReceitaResumo = {
  slug: string; titulo: string; exemplo: boolean; refeicoes: string[]; objetivos: string[];
  tempo: number; porcoes: number; custo_total_estimado: number; ingredientes: any[];
};
type Props = { receitas: Record<string, ReceitaResumo> };

const ORDEM_REFEICOES = Object.keys(REFEICOES) as (keyof typeof REFEICOES)[];
const SUGERIR_EM = ["cafe-da-manha", "almoco", "jantar"];
const TIPO_RECEITA = "application/x-receita";
const TIPO_ENTRADA = "application/x-entrada";

export default function Planejador({ receitas }: Props) {
  const lista = useMemo(() => Object.values(receitas), [receitas]);
  const [plano, setPlano] = useState<Plano>({ versao: 1, entradas: [], porcoesPadrao: 2 });
  const [carregado, setCarregado] = useState(false);
  const [diaAtivo, setDiaAtivo] = useState(() => (new Date().getDay() + 6) % 7);
  const [alvo, setAlvo] = useState<{ dia: number; refeicao: string } | null>(null);
  const [busca, setBusca] = useState("");
  const [filtroLateral, setFiltroLateral] = useState("");
  const [sobre, setSobre] = useState("");
  const [aviso, setAviso] = useState("");

  useEffect(() => {
    setPlano(lerPlano());
    setCarregado(true);
    return aoAtualizar(setPlano);
  }, []);

  useEffect(() => {
    if (!aviso) return;
    const t = setTimeout(() => setAviso(""), 2600);
    return () => clearTimeout(t);
  }, [aviso]);

  // Ignora entradas de receitas que deixaram de existir
  const entradas = plano.entradas.filter((e) => receitas[e.receita]);
  const resumo = useMemo(() => montarListaDeCompras(entradas, receitas), [plano, receitas]);

  function atualizar(mudar: (p: Plano) => void) {
    const copia: Plano = { ...plano, entradas: plano.entradas.map((e) => ({ ...e })) };
    mudar(copia);
    setPlano(copia);
    salvarPlano(copia);
  }

  const adicionar = (receita: string, dia: number, refeicao: string) =>
    atualizar((p) => { p.entradas.push({ id: novoId(), receita, dia, refeicao, porcoes: p.porcoesPadrao }); });

  const mover = (id: string, dia: number, refeicao: string) =>
    atualizar((p) => { const e = p.entradas.find((x) => x.id === id); if (e) { e.dia = dia; e.refeicao = refeicao; } });

  const remover = (id: string) => atualizar((p) => { p.entradas = p.entradas.filter((x) => x.id !== id); });

  const mudarPorcoes = (id: string, delta: number) =>
    atualizar((p) => { const e = p.entradas.find((x) => x.id === id); if (e) e.porcoes = Math.min(20, Math.max(1, e.porcoes + delta)); });

  function sugerirSemana() {
    let adicionadas = 0;
    atualizar((p) => {
      SUGERIR_EM.forEach((refeicao, r) => {
        const candidatas = lista.filter((x) => x.refeicoes.includes(refeicao));
        if (!candidatas.length) return;
        let k = r; // começa em pontos diferentes para variar entre refeições
        for (let dia = 0; dia < 7; dia++) {
          if (p.entradas.some((e) => e.dia === dia && e.refeicao === refeicao)) continue;
          let escolhida = candidatas[k % candidatas.length];
          for (let t = 0; t < candidatas.length; t++) {
            const c = candidatas[(k + t) % candidatas.length];
            if (!p.entradas.some((e) => e.dia === dia && e.receita === c.slug)) { escolhida = c; k += t; break; }
          }
          k++;
          p.entradas.push({ id: novoId(), receita: escolhida.slug, dia, refeicao, porcoes: p.porcoesPadrao });
          adicionadas++;
        }
      });
    });
    setAviso(adicionadas ? `${adicionadas} refeições sugeridas. Ajuste como quiser.` : "Sua semana já está completa.");
  }

  function limpar() {
    if (!entradas.length || confirm("Remover todas as receitas da semana?")) {
      atualizar((p) => { p.entradas = []; });
    }
  }

  // ── Arrastar e soltar ─────────────────────────────────────────
  const aoArrastarReceita = (slug: string) => (e: DragEvent) => {
    e.dataTransfer!.setData(TIPO_RECEITA, slug);
    e.dataTransfer!.effectAllowed = "copy";
  };
  const aoArrastarEntrada = (id: string) => (e: DragEvent) => {
    e.dataTransfer!.setData(TIPO_ENTRADA, id);
    e.dataTransfer!.effectAllowed = "move";
  };
  const propsSoltar = (dia: number, refeicao: string) => {
    const chave = `${dia}-${refeicao}`;
    return {
      onDragOver: (e: DragEvent) => { e.preventDefault(); if (sobre !== chave) setSobre(chave); },
      onDragLeave: (e: DragEvent) => {
        if (!(e.currentTarget as HTMLElement).contains(e.relatedTarget as Node)) setSobre("");
      },
      onDrop: (e: DragEvent) => {
        e.preventDefault();
        setSobre("");
        const slug = e.dataTransfer!.getData(TIPO_RECEITA);
        const id = e.dataTransfer!.getData(TIPO_ENTRADA);
        if (slug) adicionar(slug, dia, refeicao);
        else if (id) mover(id, dia, refeicao);
      },
    };
  };

  const lateral = lista.filter((r) =>
    (!filtroLateral || r.refeicoes.includes(filtroLateral)) &&
    semAcento(r.titulo).includes(semAcento(busca)),
  );

  return (
    <div class={`planejador ${carregado ? "" : "carregando"}`}>
      {/* Barra de ferramentas */}
      <div class="planejador__barra">
        <div class="planejador__resumo">
          <strong>{resumo.refeicoes}</strong> {resumo.refeicoes === 1 ? "refeição planejada" : "refeições planejadas"}
          {resumo.refeicoes > 0 && <> · custo estimado <strong>{formatarMoeda(resumo.custoTotal)}</strong></>}
        </div>
        <div class="planejador__acoes">
          <div class="contador" aria-label="Porções por refeição">
            <span>Porções</span>
            <button type="button" aria-label="Menos porções" onClick={() => atualizar((p) => { p.porcoesPadrao = Math.max(1, p.porcoesPadrao - 1); })}>−</button>
            <output>{plano.porcoesPadrao}</output>
            <button type="button" aria-label="Mais porções" onClick={() => atualizar((p) => { p.porcoesPadrao = Math.min(20, p.porcoesPadrao + 1); })}>+</button>
          </div>
          <button type="button" class="btn btn--contorno btn--pequeno" onClick={sugerirSemana}>✦ Sugerir semana</button>
          <button type="button" class="btn btn--contorno btn--pequeno" onClick={limpar} disabled={!entradas.length}>Limpar</button>
          <a href="/lista-de-compras" class="btn btn--acento btn--pequeno" aria-disabled={!entradas.length}>Lista de compras →</a>
        </div>
      </div>

      <div class="planejador__corpo">
        {/* Lateral com receitas arrastáveis (computador) */}
        <aside class="planejador__lateral" aria-label="Receitas para arrastar">
          <h2>Receitas</h2>
          <p class="dica">Arraste para um dia da semana.</p>
          <input class="campo" type="search" placeholder="Buscar…" value={busca} onInput={(e) => setBusca(e.currentTarget.value)} aria-label="Buscar receita" />
          <div class="mini-chips">
            <button type="button" class={!filtroLateral ? "ativo" : ""} onClick={() => setFiltroLateral("")}>Todas</button>
            {ORDEM_REFEICOES.map((r) => (
              <button type="button" class={filtroLateral === r ? "ativo" : ""} onClick={() => setFiltroLateral(r)}>{REFEICOES[r]}</button>
            ))}
          </div>
          <ul>
            {lateral.map((r) => (
              <li draggable onDragStart={aoArrastarReceita(r.slug)} class="arrastavel" title="Arraste para um dia">
                <span class="alca" aria-hidden="true">⋮⋮</span>
                <span>
                  <strong>{r.titulo}</strong>
                  <small>{formatarTempo(r.tempo)} · {formatarMoeda(r.custo_total_estimado / r.porcoes)}/porção{r.exemplo ? " · exemplo" : ""}</small>
                </span>
              </li>
            ))}
            {!lateral.length && <li class="vazio">Nenhuma receita encontrada.</li>}
          </ul>
        </aside>

        <div class="semana">
          {/* Abas de dias (celular) */}
          <div class="semana__abas" role="tablist" aria-label="Dias da semana">
            {DIAS_CURTOS.map((d, i) => {
              const n = entradas.filter((e) => e.dia === i).length;
              return (
                <button type="button" role="tab" aria-selected={diaAtivo === i} class={diaAtivo === i ? "ativo" : ""} onClick={() => setDiaAtivo(i)}>
                  {d}{n > 0 && <span class="bolinha">{n}</span>}
                </button>
              );
            })}
          </div>

          {/* Cabeçalho das refeições (computador) */}
          <div class="semana__cabecalho" aria-hidden="true">
            <span></span>
            {ORDEM_REFEICOES.map((r) => <span>{REFEICOES[r]}</span>)}
          </div>

          {DIAS.map((nomeDia, dia) => (
            <section class={`dia ${diaAtivo === dia ? "dia--ativo" : ""}`} aria-label={nomeDia}>
              <h3 class="dia__nome"><span class="longo">{nomeDia}</span><span class="curto">{DIAS_CURTOS[dia]}</span></h3>
              {ORDEM_REFEICOES.map((refeicao) => {
                const itens = entradas.filter((e) => e.dia === dia && e.refeicao === refeicao);
                return (
                  <div class={`celula ${sobre === `${dia}-${refeicao}` ? "celula--sobre" : ""}`} {...propsSoltar(dia, refeicao)}>
                    <span class="celula__rotulo">{REFEICOES[refeicao]}</span>
                    {itens.map((e) => (
                      <Item entrada={e} receita={receitas[e.receita]} aoArrastar={aoArrastarEntrada(e.id)}
                        aoRemover={() => remover(e.id)} aoMudarPorcoes={(d) => mudarPorcoes(e.id, d)} />
                    ))}
                    <button type="button" class="celula__mais" onClick={() => setAlvo({ dia, refeicao })}
                      aria-label={`Adicionar receita: ${nomeDia}, ${REFEICOES[refeicao]}`}>
                      <span aria-hidden="true">+</span>{!itens.length && <span class="celula__texto">Adicionar</span>}
                    </button>
                  </div>
                );
              })}
            </section>
          ))}
        </div>
      </div>

      {alvo && (
        <Seletor alvo={alvo} receitas={lista} aoFechar={() => setAlvo(null)}
          aoEscolher={(slug) => { adicionar(slug, alvo.dia, alvo.refeicao); setAlvo(null); setAviso(`Adicionada em ${DIAS[alvo.dia]} · ${REFEICOES[alvo.refeicao as keyof typeof REFEICOES]}`); }} />
      )}

      <div class="planejador__aviso" role="status" aria-live="polite">{aviso && <span>{aviso}</span>}</div>

      {/* Barra fixa no celular */}
      <div class="planejador__rodape">
        <span><strong>{resumo.refeicoes}</strong> refeições{resumo.refeicoes > 0 && <> · {formatarMoeda(resumo.custoTotal)}</>}</span>
        <a href="/lista-de-compras" class="btn btn--acento btn--pequeno">Lista de compras →</a>
      </div>
    </div>
  );
}

function Item({ entrada, receita, aoArrastar, aoRemover, aoMudarPorcoes }: {
  entrada: Entrada; receita: ReceitaResumo; aoArrastar: (e: DragEvent) => void;
  aoRemover: () => void; aoMudarPorcoes: (delta: number) => void;
}) {
  return (
    <div class="item arrastavel" draggable onDragStart={aoArrastar}>
      <div class="item__topo">
        <a href={`/receitas/${receita.slug}`} class="item__titulo">{receita.titulo}</a>
        <button type="button" class="item__remover" aria-label={`Remover ${receita.titulo}`} onClick={aoRemover}>×</button>
      </div>
      <span class="item__porcoes">
        <button type="button" aria-label="Menos porções" onClick={() => aoMudarPorcoes(-1)}>−</button>
        <span>{entrada.porcoes} {entrada.porcoes > 1 ? "porções" : "porção"}</span>
        <button type="button" aria-label="Mais porções" onClick={() => aoMudarPorcoes(1)}>+</button>
      </span>
    </div>
  );
}

function Seletor({ alvo, receitas, aoFechar, aoEscolher }: {
  alvo: { dia: number; refeicao: string }; receitas: ReceitaResumo[];
  aoFechar: () => void; aoEscolher: (slug: string) => void;
}) {
  const dialogo = useRef<HTMLDialogElement>(null);
  const [busca, setBusca] = useState("");

  useEffect(() => {
    const d = dialogo.current!;
    d.showModal();
    const fechar = () => aoFechar();
    d.addEventListener("close", fechar);
    return () => d.removeEventListener("close", fechar);
  }, []);

  const filtradas = receitas.filter((r) => semAcento(r.titulo).includes(semAcento(busca)));
  const indicadas = filtradas.filter((r) => r.refeicoes.includes(alvo.refeicao));
  const outras = filtradas.filter((r) => !r.refeicoes.includes(alvo.refeicao));
  const nomeRefeicao = REFEICOES[alvo.refeicao as keyof typeof REFEICOES];

  const opcao = (r: ReceitaResumo) => (
    <li>
      <button type="button" onClick={() => aoEscolher(r.slug)}>
        <strong>{r.titulo}</strong>
        <small>{formatarTempo(r.tempo)} · {formatarMoeda(r.custo_total_estimado / r.porcoes)}/porção{r.exemplo ? " · exemplo" : ""}</small>
      </button>
    </li>
  );

  const fecharFora = (e: JSX.TargetedMouseEvent<HTMLDialogElement>) => { if (e.target === dialogo.current) dialogo.current.close(); };

  return (
    <dialog ref={dialogo} class="seletor" onClick={fecharFora} aria-labelledby="seletor-titulo">
      <div class="seletor__conteudo">
        <header>
          <div>
            <p class="seletor__onde">{DIAS[alvo.dia]} · {nomeRefeicao}</p>
            <h2 id="seletor-titulo">Escolha uma receita</h2>
          </div>
          <button type="button" class="seletor__fechar" aria-label="Fechar" onClick={() => dialogo.current!.close()}>×</button>
        </header>
        <input class="campo" type="search" placeholder="Buscar receita…" value={busca} onInput={(e) => setBusca(e.currentTarget.value)} aria-label="Buscar receita" />
        <div class="seletor__lista">
          {indicadas.length > 0 && <><h3>Indicadas para {nomeRefeicao.toLowerCase()}</h3><ul>{indicadas.map(opcao)}</ul></>}
          {outras.length > 0 && <><h3>Outras receitas</h3><ul>{outras.map(opcao)}</ul></>}
          {!filtradas.length && <p class="vazio">Nenhuma receita encontrada.</p>}
        </div>
      </div>
    </dialog>
  );
}

function semAcento(s: string) {
  return s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
}
