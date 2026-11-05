# Pondo a Homeclue no ar (Railway + Postgres + Stripe)

O repositório tem dois produtos: na raiz, o protótipo antigo (Kaza IA, um
portal); em `homeclue/`, a Homeclue. No Railway, a Homeclue é um serviço
próprio apontando para a pasta `homeclue`.

## 1. Serviço

1. [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo** → `MrPach3co/Teste-01`.
2. No serviço: **Settings → Source → Root Directory** = `homeclue`. O Railway usa
   `homeclue/Dockerfile` e `homeclue/railway.toml`.
3. **Settings → Source → Branch**: a branch que deve ir ao ar.

## 2. Banco

**+ New → Database → Add PostgreSQL**. No serviço da Homeclue, crie
`DATABASE_URL` com **Add Reference** → Postgres → `DATABASE_URL`.

A cada deploy o container aplica as migrações, garante a imobiliária de
demonstração e sobe o servidor (com a fila de tarefas dentro dele).

## 3. Variáveis de ambiente

| Variável | Valor |
|---|---|
| `DATABASE_URL` | referência ao Postgres |
| `JWT_SECRET_KEY` | `python3 -c "import secrets; print(secrets.token_hex(32))"` |
| `AMBIENTE` | `producao` |
| `URL_PUBLICA` | domínio final, ex. `https://homeclue.com.br` (sem `/` no fim) — vai nos links dos e-mails |
| `ADMIN_EMAILS` | seu e-mail (acesso ao `/admin.html`) |
| `ANTHROPIC_API_KEY` | chave da Anthropic (console.anthropic.com) — liga a IA |
| `ANTHROPIC_MODELO` | `claude-opus-5-5` (padrão). Compare o custo com `claude-haiku-5-5` (ver PENDENCIAS.md) |
| `PRECO_PLANO_ESSENCIAL`, `PRECO_PLANO_PROFISSIONAL`, `PRECO_PLANO_PREMIUM` | preços exibidos (R$/mês) |
| `SMTP_HOST`, `SMTP_PORTA`, `SMTP_USUARIO`, `SMTP_SENHA`, `EMAIL_REMETENTE` | passo 6 (e-mail) |
| `STRIPE_*` | passo 5 (opcional) |

## 4. Domínio

**Settings → Networking → Generate Domain** (ou domínio próprio). Atualize
`URL_PUBLICA`. Teste: `https://SEU-DOMINIO/api/saude` deve responder
`{"status":"ok","ia":true,...}`.

## 5. Stripe

1. Conta em [stripe.com](https://stripe.com).
2. **Produtos**: três preços recorrentes mensais (Essencial, Profissional,
   Premium) → `STRIPE_PRECO_ESSENCIAL`, `STRIPE_PRECO_PROFISSIONAL`,
   `STRIPE_PRECO_PREMIUM`.
3. **Valor por lead (opcional)**: em **Billing → Meters**, crie um medidor com
   o nome de evento `homeclue_lead` (soma). Crie um preço **por uso** ligado a
   ele → `STRIPE_PRECO_POR_LEAD`. Cada lead vira um evento, sem duplicar.
4. **Maquete avulsa (opcional)**: preço de **pagamento único** →
   `STRIPE_PRECO_MAQUETE`.
5. **Webhook**: `https://SEU-DOMINIO/api/assinatura/webhook`, eventos
   `checkout.session.completed`, `customer.subscription.updated`,
   `customer.subscription.deleted` → segredo em `STRIPE_WEBHOOK_SECRET`.
6. **Portal do cliente**: ative em **Configurações → Billing**.
7. Chave secreta → `STRIPE_SECRET_KEY` (teste com `sk_test_…` e o cartão
   `4242 4242 4242 4242`).

## 6. E-mail ("esqueci minha senha" e aviso de lead)

Sem e-mail, a Homeclue funciona, mas ninguém recupera a senha sozinho e os
leads do formulário só aparecem no painel. Qualquer provedor SMTP serve:

- **Resend** ([resend.com](https://resend.com)): `SMTP_HOST=smtp.resend.com`,
  `SMTP_PORTA=465`, `SMTP_USUARIO=resend`, `SMTP_SENHA=` a chave da API.
- **Brevo** ([brevo.com](https://www.brevo.com)): `SMTP_HOST=smtp-relay.brevo.com`,
  `SMTP_PORTA=587`, usuário e senha SMTP do painel deles.

Em qualquer um, **verifique o domínio** do remetente (registros SPF e DKIM que
o provedor mostra, no DNS do domínio) e use um remetente desse domínio em
`EMAIL_REMETENTE`, por exemplo `Homeclue <nao-responda@homeclue.com.br>`.
Sem isso, os e-mails caem no spam.

## 7. OpenStreetMap (contexto do bairro)

Funciona sem configuração: usa o Overpass público (com uma segunda instância
de reserva) e, se ele cair, o Nominatim. Os resultados ficam em cache por 30
dias. Com muitos clientes, contrate um provedor de Overpass ou hospede um
(ver PENDENCIAS.md).

Na primeira importação de um feed grande, o contexto é calculado imóvel a
imóvel em segundo plano (para 1.000+ imóveis, pode levar uma hora). A busca
funciona desde o primeiro minuto; o contexto vai aparecendo. E-mails e
cobrança passam na frente dessa fila.

## 8. Testes automáticos (GitHub Actions)

`.github/workflows/homeclue.yml` roda a cada push que mexe em `homeclue/`:
os testes em SQLite e em Postgres, as migrações e as 30 buscas da trava
contra invenção. Se ficar vermelho, não publique.

## 9. Se o site da imobiliária tiver política de segurança (CSP)

Alguns sites bloqueiam scripts de outros domínios. Nesse caso, o site precisa
liberar o domínio da Homeclue em `script-src` e `frame-src`. Se o sistema do
site não deixar colar script nenhum, use o **link direto da busca**
(`https://SEU-DOMINIO/embed.html?k=CHAVE`) num botão ou no menu.

## Checklist antes da primeira demonstração

- [ ] `/api/saude` mostra `"ia": true`
- [ ] "Esqueci minha senha" chega no e-mail (SMTP configurado e domínio verificado)
- [ ] `python -m app.avaliacao --chave pk_…` com o estoque real: 0 violações, e você leu o relatório
- [ ] Feed XML da imobiliária conectado em **Integração XML**
- [ ] WhatsApp da imobiliária e dos corretores preenchidos
- [ ] Um imóvel com planta desenhada (vitrine da maquete 3D)
- [ ] Termos e Política de Privacidade revisados por advogado
