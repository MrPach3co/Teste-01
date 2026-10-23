# Plataforma [NOME DA MARCA]

Site institucional, páginas de venda e plataforma de receitas de uma marca de
gastronomia saudável, mais um gerador do e-book em PDF. Tudo sai dos mesmos
arquivos de conteúdo: você edita uma receita uma vez e ela aparece no site, no
planejador, na lista de compras e no e-book.

Feito com [Astro](https://astro.build) (páginas estáticas, rápidas e boas para o
Google) e [Preact](https://preactjs.com) nas partes interativas.

---

## Páginas

| Endereço | O que é |
|---|---|
| `/` | Home: hero, problema, método, acervo, plataforma, equipe, como funciona, depoimentos*, FAQ, próximos passos e chamada |
| `/amostra-gratis` | Captura de nome e e-mail com consentimento (LGPD) |
| `/amostra-gratis/obrigado` | Confirmação e download do PDF (fora do Google) |
| `/pre-venda` | Página de vendas: benefícios, sumário, exemplo de página, garantia, FAQ e botão de checkout |
| `/receitas` | Biblioteca com filtros de refeição, objetivo, tempo e custo, mais busca |
| `/receitas/<nome>` | Receita com ajuste de porções, informação nutricional e impressão |
| `/planejador` | Planejador semanal: arrastar e soltar (computador) ou tocar em "+" (celular) |
| `/lista-de-compras` | Lista gerada do planejador, com ingredientes somados por seção do mercado |
| `/privacidade`, `/termos` | Política de privacidade (LGPD) e termos de uso (modelos para revisar) |
| `/estilo` | Guia de estilo interno (fora do Google) |

\* A seção de depoimentos só aparece quando existir algum depoimento cadastrado.

---

## Rodar no seu computador

Precisa do [Node.js](https://nodejs.org) 20 ou mais novo.

```bash
cd plataforma
npm install                    # só na primeira vez
npm run dev                    # site em http://localhost:4321
```

| Comando | O que faz |
|---|---|
| `npm run dev` | Site local, atualizando sozinho a cada alteração |
| `npm run build` | Gera o site final em `dist/` (é o que a hospedagem roda) |
| `npm test` | Confere as regras (soma da lista, formatos) e se o conteúdo está válido |
| `npm run ebook` | Gera os PDFs (veja abaixo) |
| `npm run imagens` | Regera a imagem de compartilhamento e os ícones com as cores da marca |

Na primeira vez que for gerar PDFs ou imagens, instale o navegador usado para
isso: `npx playwright install chromium`.

---

## Onde editar (sem mexer em código)

```
conteudo/
  marca.yaml            nome, slogan, cores, logo, contato, preço, link de checkout,
                        formulário de e-mail, faixas de custo, dados da empresa
  equipe.yaml           nutricionista (nome, CRN, foto, bio), chef (fotos de mãos/pratos)
  depoimentos.yaml      começa VAZIO → a seção de depoimentos fica escondida
  textos/home.yaml      todos os textos da home e o FAQ
  textos/amostra.yaml   textos da amostra grátis e da página de obrigado
  textos/pre-venda.yaml textos da página de vendas
  receitas/*.yaml       uma receita por arquivo (veja _modelo.yaml)
fotos/                  fotos das receitas e da equipe (otimizadas automaticamente)
```

Nos textos, `{marca}`, `{preco}`, `{receitas_ebook}` e outros atalhos são
trocados pelos valores de `marca.yaml`, e `*palavra*` fica em itálico colorido.

Se algum campo estiver errado, o site **não publica** e mostra exatamente o
arquivo e o campo a corrigir. Por exemplo:

```
Erro em conteudo/receitas/torta.yaml:
  • refeicoes.0: refeicao inválido. Use um destes: cafe-da-manha, almoco, lanche, jantar
```

### Adicionar uma receita

1. Copie `conteudo/receitas/_modelo.yaml` para um arquivo novo, como
   `conteudo/receitas/torta-de-frango.yaml`. O nome do arquivo vira o endereço
   (`/receitas/torta-de-frango`).
2. Preencha os campos. Ingredientes com o mesmo nome são somados na lista de
   compras, por isso use sempre o mesmo nome (por exemplo, sempre "limão").
3. Coloque a foto em `fotos/receitas/` e informe `foto: "receitas/torta-de-frango.jpg"`.
   Ela é convertida para AVIF/WebP em vários tamanhos automaticamente.
4. Quando a nutricionista revisar, ela muda `revisado_por_nutricionista: true` e
   preenche `data_revisao`. Só então o site mostra "revisada por".

### Regras de honestidade que o código garante

- **Revisão nutricional.** Sem `revisado_por_nutricionista: true`, a receita
  mostra "valores estimados, aguardando revisão".
- **Depoimentos.** Só aparecem com `autorizado: true`, e a seção some se a lista
  estiver vazia. O site não exibe nenhum número de clientes nem resultado.
- **Receitas de exemplo.** Com `exemplo: true`, levam um selo **EXEMPLO** no site e
  no PDF.
- **Fotos.** Sem foto, aparece um placeholder escrito "imagem ilustrativa · foto
  real em breve".
- **Checkout.** Sem link de checkout, o botão fica desativado ("Pré-venda em breve").

---

## E-book em PDF

```bash
npm run ebook                  # gera as duas versões
npm run ebook -- --amostra     # só a amostra
npm run ebook -- --completo    # só o e-book completo
```

| Versão | Receitas | Arquivo |
|---|---|---|
| Amostra grátis | as com `na_amostra: true` (até o limite de `marca.yaml`) | `public/downloads/amostra-gratis.pdf`, publicado no site |
| E-book completo | todas as publicadas | `ebook/saida/ebook-completo.pdf`, **não** vai para o site nem para o Git |

O PDF tem capa, créditos, aviso educativo, sumário com páginas, o método, aberturas
de capítulo por refeição, cada receita em duas páginas, índice por objetivo,
tempo e custo, e página final (na amostra, a chamada para a pré-venda). Envie o
e-book completo para a Hotmart ou Kiwify como arquivo do produto.

Depois de mudar receitas da amostra, rode `npm run ebook -- --amostra` e
publique, para o PDF do site acompanhar.

---

## Formulário da amostra grátis

Enquanto `amostra.form_action` estiver vazio em `marca.yaml`, o formulário
funciona em **modo demonstração**: valida os campos e libera o download direto.
Para enviar os contatos a uma ferramenta de e-mail (com confirmação e entrega
automática do PDF), siga o passo a passo em [`PUBLICAR.md`](PUBLICAR.md#4-formulário-de-e-mail-mailerlite).

---

## Estrutura do código

```
src/
  lib/comum.mjs        regras compartilhadas: lista de compras, formatos, rótulos
  lib/dados.mjs        leitura e validação de conteudo/ (site e scripts)
  lib/conteudo.ts      acesso ao conteúdo dentro do site
  lib/plano.ts         planejador salvo no navegador
  layouts/             estrutura das páginas
  components/          blocos visuais (cartão de receita, FAQ, capa do livro…)
  ilhas/               componentes interativos (planejador, lista, adicionar)
  pages/               uma página por arquivo
  styles/              sistema de design
scripts/
  gerar-ebook.mjs      gerador do PDF (Playwright + Paged.js)
  ebook/               modelo e estilo do PDF
  gerar-imagens.mjs    imagem de compartilhamento e ícones
testes/                testes automáticos (npm test)
```

## Próximos passos possíveis

- **Login e plano salvo na conta.** Hoje o planejador fica salvo no navegador;
  com contas, ele passa a acompanhar a pessoa em qualquer aparelho. É a base do
  clube por assinatura.
- **Clube por assinatura.** Cardápio semanal pronto, que reaproveita o planejador
  e a lista de compras.
- **Personalização com IA.** Sugerir receitas a partir dos ingredientes em casa e
  do objetivo, sempre dentro do acervo revisado.
- **Estatísticas.** Uma ferramenta sem cookies (como Plausible ou Cloudflare Web
  Analytics), para não precisar de banner de cookies.
