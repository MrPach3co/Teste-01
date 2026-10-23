# Como publicar de graça (e conectar um domínio próprio)

Custo total para estar no ar: **R$ 0 de hospedagem** + **cerca de R$ 40 por ano**
pelo domínio `.com.br`.

| Peça | Serviço | Custo |
|---|---|---|
| Hospedagem do site | Cloudflare Pages | grátis (banda ilimitada, HTTPS automático, uso comercial permitido) |
| Domínio `.com.br` | Registro.br | cerca de R$ 40 por ano |
| E-mail `contato@seudominio` | Cloudflare Email Routing (encaminha para o seu Gmail) | grátis |
| Captura de e-mails e entrega da amostra | MailerLite ou Brevo | plano grátis para começar (confira os limites atuais) |
| Venda do e-book | Hotmart ou Kiwify | sem mensalidade; cobram uma porcentagem por venda |

> Os painéis desses serviços mudam de tempos em tempos. Se algum botão estiver com
> outro nome, procure pela função descrita: o caminho é o mesmo.

---

## 1. Colocar o site no ar (Cloudflare Pages)

Antes de tudo, **deixe o repositório do GitHub privado** (Settings → General →
Danger Zone → Change visibility). Ele vai conter as suas receitas.

1. Crie uma conta grátis em [dash.cloudflare.com](https://dash.cloudflare.com).
2. No menu, abra **Workers & Pages** → **Create** → aba **Pages** → **Connect to Git**.
3. Autorize o GitHub e escolha este repositório.
4. Configure o build:

   | Campo | Valor |
   |---|---|
   | Production branch | a branch principal do repositório (ex.: `main`) |
   | Framework preset | `Astro` |
   | Build command | `npm run build` |
   | Build output directory | `dist` |
   | Root directory (em *Advanced*) | `plataforma` |
   | Variável de ambiente | `NODE_VERSION` = `22` |

5. Clique em **Save and Deploy**. Em um ou dois minutos o site fica no ar num
   endereço como `https://nome-do-projeto.pages.dev`.

A partir daí, **todo push na branch principal publica o site sozinho**. Pushes em
outras branches geram um link de prévia, bom para revisar antes de publicar.

---

## 2. Conectar um domínio próprio

### 2.1 Registrar o domínio

1. Em [registro.br](https://registro.br), pesquise o nome desejado (ex.:
   `suamarca.com.br`) e registre (cerca de R$ 40 por ano, com CPF ou CNPJ).

### 2.2 Passar o DNS para a Cloudflare

1. No painel da Cloudflare, clique em **Add a domain** (ou *Add site*), digite
   `suamarca.com.br` e escolha o plano **Free**.
2. A Cloudflare mostra **dois servidores de nome** (algo como
   `ana.ns.cloudflare.com` e `bob.ns.cloudflare.com`).
3. No Registro.br, abra o domínio → **DNS** → **Alterar servidores DNS** e
   troque pelos dois servidores da Cloudflare.
4. Aguarde a propagação, que costuma levar de alguns minutos a algumas horas. A
   Cloudflare avisa por e-mail quando o domínio estiver ativo.

### 2.3 Apontar o domínio para o site

1. Em **Workers & Pages** → seu projeto → **Custom domains** → **Set up a custom domain**.
2. Adicione `www.suamarca.com.br` e depois `suamarca.com.br`. A Cloudflare cria os
   registros de DNS e o certificado HTTPS automaticamente.
3. (Recomendado) Em **Rules** → **Redirect Rules**, use o modelo
   *Redirect from root to www* para mandar `suamarca.com.br` para
   `www.suamarca.com.br`. Assim o Google vê um endereço só.

### 2.4 Atualizar o endereço no site

Em `conteudo/marca.yaml`, troque:

```yaml
url_site: "https://www.suamarca.com.br"
```

Faça commit e push. Isso corrige o sitemap, os links de compartilhamento e os
dados para o Google.

### 2.5 Avisar o Google

1. Entre no [Google Search Console](https://search.google.com/search-console) e
   adicione a propriedade do domínio (a verificação por DNS é feita em um clique
   quando o DNS está na Cloudflare).
2. Em **Sitemaps**, envie `sitemap-index.xml`.

---

## 3. E-mail com o seu domínio (grátis)

1. Na Cloudflare, abra o domínio → **Email** → **Email Routing** → **Get started**.
2. Crie os endereços `contato@` e `privacidade@` (os mesmos de `marca.yaml`) e
   aponte para o seu Gmail.
3. Para também **enviar** como `contato@suamarca.com.br`, configure o "Enviar e-mail
   como" do Gmail com o SMTP da sua ferramenta de e-mail, ou use um serviço pago
   como o Google Workspace.

---

## 4. Formulário de e-mail (MailerLite)

Sem configuração, o formulário da amostra libera o download direto (modo
demonstração). Para capturar os contatos com segurança jurídica:

1. Crie uma conta no [MailerLite](https://www.mailerlite.com) e um **grupo**
   chamado "Amostra grátis".
2. **Forms** → **Embedded forms** → **Create**: campos *Nome* e *E-mail*, ligados
   ao grupo. Ative **double opt-in** (a pessoa confirma o e-mail). Isso registra o
   consentimento com data e hora, o que ajuda muito na LGPD.
3. Abra o formulário em **HTML code** e copie o endereço que aparece em
   `action="…"` (algo como `https://assets.mailerlite.com/jsonp/…/subscribe`).
4. Em `conteudo/marca.yaml`:

   ```yaml
   amostra:
     form_action: "https://assets.mailerlite.com/jsonp/…/subscribe"
     campo_nome: "fields[name]"
     campo_email: "fields[email]"
   ```

   Confira no mesmo código HTML se os campos se chamam `fields[name]` e
   `fields[email]`. No **Brevo**, os nomes e o endereço são diferentes: copie os
   que aparecem no HTML do formulário dele.

5. **Automations** → gatilho "quando alguém entra no grupo Amostra grátis" →
   enviar um e-mail com o link
   `https://www.suamarca.com.br/downloads/amostra-gratis.pdf`.
6. Publique e **faça um teste com o seu próprio e-mail**: preencha o formulário,
   confirme e veja se a amostra chega. O envio ao MailerLite precisa ser testado
   com a sua conta, porque não dá para testar sem ela.

---

## 5. Ligar o checkout (Hotmart ou Kiwify)

1. Crie o produto (e-book, pré-venda) na plataforma e envie o arquivo
   `ebook/saida/ebook-completo.pdf` (gerado com `npm run ebook`).
2. Copie o **link de checkout** do produto.
3. Em `conteudo/marca.yaml`:

   ```yaml
   ebook:
     link_checkout: "https://pay.hotmart.com/…"
     previsao_entrega: "15 de dezembro de 2026"   # opcional
   ```

4. Commit e push: todos os botões "Pré-venda em breve" viram botões de compra.

---

## Checklist antes de divulgar

- [ ] `marca.yaml`: nome, `url_site`, contato, preço, link de checkout, dados da empresa (razão social, CNPJ, cidade)
- [ ] `equipe.yaml`: nome e CRN reais da nutricionista, fotos
- [ ] Receitas reais no lugar das de exemplo (ou `publicada: false` nas de exemplo)
- [ ] Receitas revisadas pela nutricionista (`revisado_por_nutricionista: true` + data)
- [ ] `npm run ebook` rodado depois das receitas finais (amostra do site atualizada)
- [ ] `npm run imagens` rodado depois de definir nome e cores
- [ ] Política de privacidade e termos revisados por um profissional
- [ ] Formulário testado com um e-mail real
- [ ] Compra de teste no checkout (Hotmart e Kiwify permitem reembolsar)
