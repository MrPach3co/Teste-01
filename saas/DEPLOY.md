# Pondo o Kaza Pro no ar (Railway + Stripe)

O Kaza Pro é um serviço separado da plataforma Kaza IA (que fica na raiz do
repositório). No Railway, ele vira um serviço próprio apontando para a pasta
`saas/`.

## 1. Serviço no Railway

1. Em [railway.app](https://railway.app), clique em **New Project** →
   **Deploy from GitHub repo** e escolha `MrPach3co/Teste-01`. Se já existe um
   projeto com o Kaza IA, use **+ New** → **GitHub Repo** dentro dele.
2. No serviço criado, vá em **Settings** → **Source** → **Root Directory** e
   coloque `saas`. O Railway passa a usar o `saas/Dockerfile` e o
   `saas/railway.toml`.
3. Em **Settings** → **Source** → **Branch**, escolha a branch que deve ir ao ar.

## 2. Banco Postgres

**+ New** → **Database** → **Add PostgreSQL**. Depois, no serviço do Kaza Pro,
crie a variável `DATABASE_URL` com **Add Reference** → Postgres →
`DATABASE_URL`. O app aceita tanto `postgres://` quanto `postgresql://`.

## 3. Variáveis de ambiente

| Variável | Valor |
|---|---|
| `DATABASE_URL` | referência ao Postgres (passo 2) |
| `JWT_SECRET_KEY` | gere com `python3 -c "import secrets; print(secrets.token_hex(32))"` |
| `AMBIENTE` | `producao` |
| `URL_PUBLICA` | o domínio final, ex. `https://kazapro.up.railway.app` (sem `/` no fim) |
| `ANTHROPIC_API_KEY` | opcional: ativa a IA na busca e nas descrições |
| `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRECO_PRO`, `STRIPE_PRECO_ESCALA` | opcionais: veja o passo 5 |

## 4. Domínio

**Settings** → **Networking** → **Generate Domain** (ou conecte um domínio
próprio). Atualize `URL_PUBLICA` com ele.

Teste: `curl https://SEU-DOMINIO/api/saude` deve responder
`{"status":"ok","ia":...,"pagamentos":...}`. Os dois últimos campos mostram
se a IA e os pagamentos foram reconhecidos.

A cada deploy, o container roda as migrações (`alembic upgrade head`),
garante a imobiliária de demonstração e sobe o servidor.

## 5. Stripe (cobrança das assinaturas)

1. Crie a conta em [stripe.com](https://stripe.com) (aceita CNPJ e CPF no Brasil).
2. **Produtos** → crie "Kaza Pro — Pro" com preço **recorrente mensal de
   R$ 197** e "Kaza Pro — Escala" com **R$ 497**. Copie os IDs de preço
   (`price_...`) para `STRIPE_PRECO_PRO` e `STRIPE_PRECO_ESCALA`.
3. **Desenvolvedores** → **Chaves de API**: copie a chave secreta
   (`sk_live_...` ou `sk_test_...` para testar) para `STRIPE_SECRET_KEY`.
4. **Desenvolvedores** → **Webhooks** → **Adicionar endpoint**:
   - URL: `https://SEU-DOMINIO/api/assinatura/webhook`
   - Eventos: `checkout.session.completed`, `customer.subscription.updated`,
     `customer.subscription.deleted`
   - Copie o "segredo de assinatura" (`whsec_...`) para `STRIPE_WEBHOOK_SECRET`.
5. **Configurações** → **Billing** → **Portal do cliente**: ative o portal
   para os clientes poderem cancelar e baixar faturas sozinhos.

Para testar sem cobrar ninguém, use as chaves `sk_test_...` e o cartão
`4242 4242 4242 4242` com qualquer data futura e qualquer CVC.

## Checklist antes de anunciar

- [ ] `/api/saude` mostra `"ia": true` e `"pagamentos": true` (se configurou)
- [ ] Criou uma conta real, cadastrou um imóvel e buscou pelo link direto
- [ ] Assinou o plano Pro em modo teste e viu o plano mudar no painel
- [ ] Termos e Política de Privacidade revisados por advogado
