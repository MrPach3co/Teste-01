/* ==========================================================================
   Kaza IA — landing page + demo funcional (sem back-end)
   A landing (nav, hero, seções) é só apresentação. O painel de demo dentro
   do hero, porém, é real: o texto que você digita roda contra os imóveis
   fictícios abaixo e o mesmo cálculo de match do protótipo.
   ========================================================================== */

/* ---- Barra de navegação: ganha uma linha de baixo ao rolar a página ---- */
const nav = document.getElementById('nav');
window.addEventListener('scroll', () => {
  nav.classList.toggle('scrolled', window.scrollY > 8);
});

/* ---- Seções aparecem suavemente conforme entram na tela ---- */
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
   Demo real: banco de imóveis fictícios (Rio de Janeiro) e o motor de match
   ========================================================================== */
const IMOVEIS = [
  {
    nome: "Casa em condomínio na Barra",
    bairro: "Barra da Tijuca, Rio de Janeiro",
    preco: 1850000,
    quartos: 4,
    area: 320,
    gradiente: "linear-gradient(135deg, #1F3B2C 0%, #2E5741 100%)",
    tags: ["moderna", "perto-do-mar", "escritorio", "piscina", "condominio-fechado", "pet-friendly"],
    motivo: "Melhor custo-benefício por m² entre as casas da Barra"
  },
  {
    nome: "Casa nova frente ao mar",
    bairro: "Recreio dos Bandeirantes, Rio de Janeiro",
    preco: 2450000,
    quartos: 4,
    area: 380,
    gradiente: "linear-gradient(135deg, #9C4A26 0%, #C06A3F 100%)",
    tags: ["perto-do-mar", "vista-mar", "escritorio", "moderna", "investimento"],
    motivo: "Maior valorização histórica da região nos últimos 5 anos"
  },
  {
    nome: "Apartamento reformado com vista mar",
    bairro: "Ipanema, Rio de Janeiro",
    preco: 3200000,
    quartos: 3,
    area: 140,
    gradiente: "linear-gradient(135deg, #1B1A17 0%, #4A473F 100%)",
    tags: ["vista-mar", "reformado", "perto-do-mar", "investimento"],
    motivo: "Localização mais valorizada do Rio de Janeiro"
  },
  {
    nome: "Apartamento compacto reformado",
    bairro: "Botafogo, Rio de Janeiro",
    preco: 890000,
    quartos: 2,
    area: 78,
    gradiente: "linear-gradient(135deg, #2E5741 0%, #4C7C63 100%)",
    tags: ["reformado", "escritorio", "investimento"],
    motivo: "Melhor custo-benefício para quem busca praticidade"
  },
  {
    nome: "Cobertura duplex com piscina",
    bairro: "Leblon, Rio de Janeiro",
    preco: 5800000,
    quartos: 4,
    area: 310,
    gradiente: "linear-gradient(135deg, #1F3B2C 0%, #9C4A26 100%)",
    tags: ["cobertura", "piscina", "vista-mar", "escritorio", "perto-do-mar"],
    motivo: "Padrão de acabamento mais alto entre as opções"
  }
];

const DICIONARIO_TAGS = {
  "moderna": "moderna",
  "moderno": "moderna",
  "perto do mar": "perto-do-mar",
  "beira mar": "perto-do-mar",
  "beira-mar": "perto-do-mar",
  "frente ao mar": "perto-do-mar",
  "praia": "perto-do-mar",
  "vista mar": "vista-mar",
  "vista para o mar": "vista-mar",
  "vista": "vista-mar",
  "escritório": "escritorio",
  "escritorio": "escritorio",
  "home office": "escritorio",
  "cobertura": "cobertura",
  "piscina": "piscina",
  "reformado": "reformado",
  "reformada": "reformado",
  "condomínio": "condominio-fechado",
  "condominio": "condominio-fechado",
  "segurança": "condominio-fechado",
  "seguranca": "condominio-fechado",
  "pet": "pet-friendly",
  "animais": "pet-friendly",
  "investimento": "investimento",
  "valorização": "investimento",
  "valorizacao": "investimento"
};

function extrairOrcamento(texto) {
  const milhoes = texto.match(/(\d+(?:[.,]\d+)?)\s*milh/);
  if (milhoes) return parseFloat(milhoes[1].replace(",", ".")) * 1000000;

  const mil = texto.match(/(\d+(?:[.,]\d+)?)\s*mil\b/);
  if (mil) return parseFloat(mil[1].replace(",", ".")) * 1000;

  const valorDireto = texto.match(/r\$\s*([\d.,]+)/);
  if (valorDireto) return parseFloat(valorDireto[1].replace(/\./g, "").replace(",", "."));

  return null;
}

function extrairQuartos(texto) {
  const match = texto.match(/(\d+)\s*(quarto|dormit)/);
  return match ? parseInt(match[1], 10) : null;
}

function extrairTags(texto) {
  const encontradas = new Set();
  for (const chave in DICIONARIO_TAGS) {
    if (texto.includes(chave)) encontradas.add(DICIONARIO_TAGS[chave]);
  }
  return encontradas;
}

function calcularMatch(imovel, tagsPedidas, orcamento, quartosPedidos) {
  let pontos = 45; // toda busca começa com uma base, para nunca ficar em 0%

  tagsPedidas.forEach((tag) => {
    if (imovel.tags.includes(tag)) pontos += 12;
  });

  if (orcamento) {
    if (imovel.preco <= orcamento) {
      pontos += 20;
      if (imovel.preco <= orcamento * 0.85) pontos += 6;
    } else {
      pontos -= 18;
    }
  }

  if (quartosPedidos) {
    if (imovel.quartos === quartosPedidos) pontos += 15;
    else if (imovel.quartos > quartosPedidos) pontos += 6;
    else pontos -= 10;
  }

  return Math.max(30, Math.min(99, Math.round(pontos)));
}

function formatarPreco(valor) {
  return valor.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
}

/* ==========================================================================
   Ligação com o painel de demo (HTML dentro de #demo)
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

function criarCardImovel(imovel, match) {
  const card = document.createElement("div");
  card.className = "p-card";
  card.innerHTML = `
    <div class="photo" style="background:${imovel.gradiente}">
      <span class="match">${match}% match</span>
    </div>
    <div class="info">
      <div class="name">${imovel.nome}</div>
      <div class="meta">${formatarPreco(imovel.preco)} · ${imovel.quartos} quartos · ${imovel.area}m²</div>
      <div class="why">${imovel.motivo}</div>
    </div>
  `;
  return card;
}

function rodarBusca(texto) {
  // Cada busca começa do zero no painel — mantém a demo compacta e legível.
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

  setTimeout(() => {
    fadeIn(bolhaIa);

    const textoBusca = texto.toLowerCase();
    const tagsPedidas = extrairTags(textoBusca);
    const orcamento = extrairOrcamento(textoBusca);
    const quartosPedidos = extrairQuartos(textoBusca);

    const resultado = IMOVEIS
      .map((imovel) => ({
        imovel,
        match: calcularMatch(imovel, tagsPedidas, orcamento, quartosPedidos)
      }))
      .sort((a, b) => b.match - a.match)
      .slice(0, 3);

    const melhor = resultado[0];
    bolhaIa.textContent = `Encontrei ${resultado.length} boas opções. A que mais combina é "${melhor.imovel.nome}", com ${melhor.match}% de match.`;

    resultado.forEach(({ imovel, match }, indice) => {
      const card = criarCardImovel(imovel, match);
      demo.cards.appendChild(card);
      setTimeout(() => fadeIn(card), 120 * indice);
    });
  }, reduzMovimento ? 0 : 550);
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
