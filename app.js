/* ==========================================================================
   Kaza IA — protótipo visual (sem back-end)
   Tudo aqui é simulado: os imóveis são fixos e o "match" é calculado
   com regras simples de texto, só para parecer uma busca por IA.
   ========================================================================== */

/* ---- 1. Banco de imóveis fictícios (Rio de Janeiro) ---- */
const IMOVEIS = [
  {
    nome: "Casa em condomínio na Barra",
    bairro: "Barra da Tijuca, Rio de Janeiro",
    preco: 1850000,
    quartos: 4,
    area: 320,
    cor: "#0f766e",
    icone: "🏡",
    tags: ["moderna", "perto-do-mar", "escritorio", "piscina", "condominio-fechado", "pet-friendly"],
    motivo: "Melhor custo-benefício por m² entre as casas da Barra"
  },
  {
    nome: "Casa nova frente ao mar",
    bairro: "Recreio dos Bandeirantes, Rio de Janeiro",
    preco: 2450000,
    quartos: 4,
    area: 380,
    cor: "#115e59",
    icone: "🌊",
    tags: ["perto-do-mar", "vista-mar", "escritorio", "moderna", "investimento"],
    motivo: "Maior valorização histórica da região nos últimos 5 anos"
  },
  {
    nome: "Apartamento reformado com vista mar",
    bairro: "Ipanema, Rio de Janeiro",
    preco: 3200000,
    quartos: 3,
    area: 140,
    cor: "#134e4a",
    icone: "🌅",
    tags: ["vista-mar", "reformado", "perto-do-mar", "investimento"],
    motivo: "Localização mais valorizada do Rio de Janeiro"
  },
  {
    nome: "Apartamento compacto reformado",
    bairro: "Botafogo, Rio de Janeiro",
    preco: 890000,
    quartos: 2,
    area: 78,
    cor: "#0d9488",
    icone: "🏢",
    tags: ["reformado", "escritorio", "investimento"],
    motivo: "Melhor custo-benefício para quem busca praticidade"
  },
  {
    nome: "Cobertura duplex com piscina",
    bairro: "Leblon, Rio de Janeiro",
    preco: 5800000,
    quartos: 4,
    area: 310,
    cor: "#047857",
    icone: "🏙️",
    tags: ["cobertura", "piscina", "vista-mar", "escritorio", "perto-do-mar"],
    motivo: "Padrão de acabamento mais alto entre as opções"
  }
];

/* ---- 2. Palavras-chave que a "IA" reconhece no texto do usuário ---- */
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

const referenciasDom = {
  chat: document.getElementById("chat"),
  form: document.getElementById("form-busca"),
  campo: document.getElementById("campo-busca")
};

/* ---- 3. Extrai orçamento e número de quartos do texto digitado ---- */
function extrairOrcamento(texto) {
  const milhoes = texto.match(/(\d+(?:[.,]\d+)?)\s*milh/);
  if (milhoes) {
    return parseFloat(milhoes[1].replace(",", ".")) * 1000000;
  }
  const mil = texto.match(/(\d+(?:[.,]\d+)?)\s*mil\b/);
  if (mil) {
    return parseFloat(mil[1].replace(",", ".")) * 1000;
  }
  const valorDireto = texto.match(/r\$\s*([\d.,]+)/);
  if (valorDireto) {
    return parseFloat(valorDireto[1].replace(/\./g, "").replace(",", "."));
  }
  return null;
}

function extrairQuartos(texto) {
  const match = texto.match(/(\d+)\s*(quarto|dormit)/);
  return match ? parseInt(match[1], 10) : null;
}

function extrairTags(texto) {
  const encontradas = new Set();
  for (const chave in DICIONARIO_TAGS) {
    if (texto.includes(chave)) {
      encontradas.add(DICIONARIO_TAGS[chave]);
    }
  }
  return encontradas;
}

/* ---- 4. Calcula a % de "match" de um imóvel com o pedido do usuário ---- */
function calcularMatch(imovel, tagsPedidas, orcamento, quartosPedidos) {
  let pontos = 45; // toda busca começa com uma base, para nunca ficar em 0%

  tagsPedidas.forEach((tag) => {
    if (imovel.tags.includes(tag)) pontos += 12;
  });

  if (orcamento) {
    if (imovel.preco <= orcamento) {
      pontos += 20;
      // se ainda sobrar bastante orçamento, ganha um empurrão extra
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

/* ---- 5. Formata número para reais (R$) ---- */
function formatarPreco(valor) {
  return valor.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
}

/* ---- 6. Funções que desenham coisas na tela ---- */
function rolarParaFinal() {
  referenciasDom.chat.scrollTop = referenciasDom.chat.scrollHeight;
}

function adicionarMensagemUsuario(texto) {
  const div = document.createElement("div");
  div.className = "mensagem mensagem-usuario";
  div.textContent = texto;
  referenciasDom.chat.appendChild(div);
  rolarParaFinal();
}

function mostrarDigitando() {
  const div = document.createElement("div");
  div.className = "digitando";
  div.id = "indicador-digitando";
  div.innerHTML = "<span></span><span></span><span></span>";
  referenciasDom.chat.appendChild(div);
  rolarParaFinal();
}

function removerDigitando() {
  const el = document.getElementById("indicador-digitando");
  if (el) el.remove();
}

function criarCartaoImovel(imovel, match) {
  const cartao = document.createElement("div");
  cartao.className = "cartao-imovel";
  cartao.innerHTML = `
    <div class="cartao-foto" style="background:${imovel.cor}">${imovel.icone}</div>
    <div class="cartao-corpo">
      <div class="cartao-topo">
        <div>
          <div class="cartao-nome">${imovel.nome}</div>
          <div class="cartao-bairro">${imovel.bairro}</div>
        </div>
        <span class="cartao-match">${match}% match</span>
      </div>
      <div class="cartao-specs">
        <span>🛏️ ${imovel.quartos} quartos</span>
        <span>📐 ${imovel.area} m²</span>
      </div>
      <div class="cartao-preco">${formatarPreco(imovel.preco)}</div>
      <div class="cartao-motivo">${imovel.motivo}</div>
    </div>
  `;
  return cartao;
}

function adicionarRespostaIA(textoIntro, imoveisOrdenados) {
  const container = document.createElement("div");
  container.className = "mensagem mensagem-ia";
  container.textContent = textoIntro;
  referenciasDom.chat.appendChild(container);

  const listaResultados = document.createElement("div");
  listaResultados.className = "resultados";
  imoveisOrdenados.forEach(({ imovel, match }) => {
    listaResultados.appendChild(criarCartaoImovel(imovel, match));
  });
  referenciasDom.chat.appendChild(listaResultados);
  rolarParaFinal();
}

/* ---- 7. Mensagem inicial de boas-vindas, com sugestões clicáveis ---- */
function mostrarBoasVindas() {
  const div = document.createElement("div");
  div.className = "mensagem mensagem-ia";
  div.innerHTML = `
    Olá! Eu sou a Kaza IA 👋 Me conte o que você procura: bairro, preço, quartos, estilo...
    <div class="chips">
      <button class="chip" type="button">Casa moderna perto do mar, até 2 milhões, 4 quartos</button>
      <button class="chip" type="button">Apartamento reformado até 1 milhão com escritório</button>
      <button class="chip" type="button">Cobertura com piscina e vista para o mar</button>
    </div>
  `;
  referenciasDom.chat.appendChild(div);

  div.querySelectorAll(".chip").forEach((botao) => {
    botao.addEventListener("click", () => {
      referenciasDom.campo.value = botao.textContent;
      referenciasDom.form.requestSubmit();
    });
  });
}

/* ---- 8. Processa o pedido do usuário e "responde" como uma IA ---- */
function processarBusca(textoOriginal) {
  const texto = textoOriginal.toLowerCase();
  const tagsPedidas = extrairTags(texto);
  const orcamento = extrairOrcamento(texto);
  const quartosPedidos = extrairQuartos(texto);

  const resultado = IMOVEIS
    .map((imovel) => ({
      imovel,
      match: calcularMatch(imovel, tagsPedidas, orcamento, quartosPedidos)
    }))
    .sort((a, b) => b.match - a.match)
    .slice(0, 4);

  const melhor = resultado[0];
  const textoIntro = `Encontrei ${resultado.length} imóveis que combinam com o que você pediu. O destaque é "${melhor.imovel.nome}", com ${melhor.match}% de match:`;

  removerDigitando();
  adicionarRespostaIA(textoIntro, resultado);
}

/* ---- 9. Liga tudo: envio do formulário ---- */
referenciasDom.form.addEventListener("submit", (evento) => {
  evento.preventDefault();
  const texto = referenciasDom.campo.value.trim();
  if (!texto) return;

  adicionarMensagemUsuario(texto);
  referenciasDom.campo.value = "";
  mostrarDigitando();

  // Pequeno atraso para simular a IA "pensando"
  setTimeout(() => processarBusca(texto), 700);
});

/* ---- 10. Inicialização ---- */
mostrarBoasVindas();
