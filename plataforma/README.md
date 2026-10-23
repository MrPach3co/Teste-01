# Plataforma — [NOME DA MARCA]

Site institucional + plataforma de receitas de gastronomia saudável.
Feito com [Astro](https://astro.build): gera páginas estáticas, rápidas e
boas para o Google.

## Rodar no seu computador

Precisa do [Node.js](https://nodejs.org) 20 ou mais novo.

```bash
cd plataforma
npm install      # só na primeira vez
npm run dev      # abre em http://localhost:4321
```

`npm run build` gera o site final na pasta `dist/`.

## Onde editar (sem mexer em código)

| Arquivo | O que tem |
|---|---|
| `conteudo/marca.yaml` | nome, slogan, cores, logo, contato, preço, link de checkout |
| `conteudo/equipe.yaml` | nutricionista (nome, CRN, foto), chef (fotos de mãos/pratos) |
| `public/imagens/` | fotos e logo |

Se algum campo estiver errado, o build para e diz exatamente qual arquivo e
qual campo corrigir.

A página `/estilo` é um guia de estilo interno (fora do Google e do sitemap)
para conferir cores, fontes e componentes.
