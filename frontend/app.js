/* ==========================================================================
   Kaza IA — landing page ligada ao backend real
   A landing (nav, hero, seções) é só apresentação. O painel de demo e o
   formulário de lista de espera chamam a API de verdade em /api — não há
   mais dados nem lógica de match aqui no front.
   ========================================================================== */

const nav = document.getElementById('nav');
window.addEventListener('scroll', () => {
  nav.classList.toggle('scrolled', window.scrollY > 8);
});

const reduzMovimento = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const elementosRevelados = document.querySelectorAll('.reveal');
if (reduzMovimento) {
  elementosRevelados.forEach((el) => el.classList.add('in'));
} else {
  const observadorRevelacao = new IntersectionObserver((entradas) => {
    entradas.forEach((entrada) => {
      if (entrada.isIntersecting) entrada.target.classList.add('in');
    });
  }, { threshold: 0.15 });
  elementosRevelados.forEach((el) => observadorRevelacao.observe(el));
}

/* ==========================================================================
   Painel de demo: busca real via POST /api/buscar
   ========================================================================== */
const demo = {
  conversa: document.getElementById("demo-conversa"),
  cards: document.getElementById("demo-cards"),
  chips: document.getElementById("demo-chips"),
  form: document.getElementById("demo-form"),
  input: document.getElementById("demo-input")
};

function fadeIn(el) {
  el.style.transition = "opacity .5s ease, transform .5s ease";
  requestAnimationFrame(() => {
    el.style.opacity = "1";
    el.style.transform = "translateY(0)";
  });
}

function formatarPreco(valor) {
  return valor.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
}

function criarCardImovel(imovel) {
  const card = document.createElement("div");
  card.className = "p-card";
  const gradiente = `linear-gradient(135deg, ${imovel.cor_inicio} 0%, ${imovel.cor_fim} 100%)`;
  card.innerHTML = `
    <div class="photo" style="background:${gradiente}">
      <span class="match">${imovel.match}% match</span>
    </div>
    <div class="info">
      <div class="name">${imovel.nome}</div>
      <div class="meta">${formatarPreco(imovel.preco)} · ${imovel.quartos} quartos · ${imovel.area_m2}m²</div>
      <div class="why">${imovel.motivo}</div>
    </div>
  `;
  return card;
}

async function rodarBusca(texto) {
  demo.conversa.innerHTML = "";
  demo.cards.innerHTML = "";

  const bolhaUsuario = document.createElement("div");
  bolhaUsuario.className = "bubble-user";
  bolhaUsuario.textContent = texto;
  demo.conversa.appendChild(bolhaUsuario);
  fadeIn(bolhaUsuario);

  const bolhaIa = document.createElement("div");
  bolhaIa.className = "bubble-ai";
  bolhaIa.textContent = "Analisando seu pedido...";
  demo.conversa.appendChild(bolhaIa);
  fadeIn(bolhaIa);

  try {
    const resposta = await fetch("/api/buscar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ texto })
    });

    if (!resposta.ok) {
      throw new Error(`A API respondeu com status ${resposta.status}`);
    }

    const dados = await resposta.json();
    bolhaIa.textContent = dados.mensagem;

    dados.resultados.forEach((imovel, indice) => {
      const card = criarCardImovel(imovel);
      demo.cards.appendChild(card);
      setTimeout(() => fadeIn(card), 120 * indice);
    });
  } catch (erro) {
    bolhaIa.textContent = "Não consegui buscar agora — o backend pode estar offline. Tente novamente em instantes.";
    console.error("Erro ao buscar imóveis:", erro);
  }
}

demo.form.addEventListener("submit", (evento) => {
  evento.preventDefault();
  const texto = demo.input.value.trim();
  if (!texto) return;
  rodarBusca(texto);
  demo.input.value = "";
});

demo.chips.querySelectorAll(".demo-chip").forEach((botao) => {
  botao.addEventListener("click", () => rodarBusca(botao.textContent));
});

/* ==========================================================================
   Lista de espera: POST /api/lista-espera (com consentimento LGPD)
   ========================================================================== */
const listaEspera = {
  form: document.getElementById("lista-espera-form"),
  email: document.getElementById("lista-espera-email"),
  consentimento: document.getElementById("lista-espera-consentimento"),
  status: document.getElementById("lista-espera-status")
};

if (listaEspera.form) {
  listaEspera.form.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    listaEspera.status.textContent = "";
    listaEspera.status.classList.remove("erro");

    if (!listaEspera.consentimento.checked) {
      listaEspera.status.textContent = "Marque a caixa de consentimento para continuar.";
      listaEspera.status.classList.add("erro");
      return;
    }

    const botao = listaEspera.form.querySelector("button");
    const textoOriginal = botao.textContent;
    botao.disabled = true;
    botao.textContent = "Enviando...";

    try {
      const resposta = await fetch("/api/lista-espera", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: listaEspera.email.value,
          aceitou_termos: listaEspera.consentimento.checked
        })
      });

      if (!resposta.ok) {
        const erro = await resposta.json().catch(() => ({}));
        throw new Error(erro.detail || `A API respondeu com status ${resposta.status}`);
      }

      botao.textContent = "Você está na lista ✓";
      listaEspera.status.textContent = "Pronto! Avisaremos você por e-mail.";
      listaEspera.form.reset();
    } catch (erro) {
      botao.disabled = false;
      botao.textContent = textoOriginal;
      listaEspera.status.textContent = "Não consegui completar o cadastro. Tente novamente em instantes.";
      listaEspera.status.classList.add("erro");
      console.error("Erro ao entrar na lista de espera:", erro);
    }
  });
}
