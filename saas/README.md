# Kaza Pro — SaaS de busca com IA para imobiliárias

Versão B2B do Kaza IA. Em vez de ser um portal de imóveis, o Kaza Pro é um
**software que a imobiliária assina** para colocar a busca por linguagem
natural **no site dela**, com os **imóveis dela**, e receber os leads num
painel.

```
saas/
  backend/    API FastAPI (multi-tenant, IA, Stripe, LGPD) + testes
  frontend/   landing, login, painel e o widget (HTML/CSS/JS puro, sem build)
  Dockerfile  imagem única (backend serve o frontend)
  DEPLOY.md   passo a passo para pôr no ar (Railway + Stripe)
```

## O que o produto faz

| Para quem | O quê |
|---|---|
| **Visitante do site da imobiliária** | Escreve "apê de 2 quartos perto do metrô até 900 mil", vê os imóveis que mais combinam com % de match e o motivo, e clica em "Tenho interesse" ou "WhatsApp". |
| **Imobiliária (painel)** | Cadastra imóveis (um a um ou por planilha CSV), gera descrição de anúncio com IA, copia o código do widget, acompanha métricas, gerencia leads num funil (Novo → Em contato → Visita → Proposta → Fechado/Perdido), exporta para Excel, cadastra corretores e assina um plano. |
| **Você (dono do SaaS)** | Recebe as assinaturas pelo Stripe. Os limites de cada plano são aplicados automaticamente. |

### Planos (em `backend/app/core/planos.py`)

| Plano | Preço | Imóveis | Buscas/mês | Usuários | Selo "Kaza Pro" no widget |
|---|---|---|---|---|---|
| Grátis | R$ 0 | 15 | 300 | 1 | sim |
| Pro | R$ 197 | 300 | 5.000 | 5 | não |
| Escala | R$ 497 | ilimitados | 30.000 | 25 | não |

Para mudar preço ou limite, edite esse arquivo **e** o preço correspondente no Stripe.

### Integrações opcionais

O produto funciona **sem nenhuma chave externa**: dá para rodar, demonstrar e
até vender no manual.

- **`ANTHROPIC_API_KEY`**: com ela, a busca usa a Claude para interpretar o
  pedido (saída estruturada em JSON Schema) e o botão "Gerar com IA" escreve
  descrições de anúncio. Sem ela, a busca usa um motor de regras em português
  (orçamento, quartos por extenso, tipo, compra/aluguel, bairro, ~20
  características) e a descrição usa um modelo pronto. Se a IA falhar ou
  recusar, o sistema cai sozinho no plano B, sem erro para o visitante.
- **Stripe** (`STRIPE_*`): com as chaves, o painel abre o checkout de
  assinatura e o portal de faturas. O plano só muda quando chega o webhook
  assinado do Stripe, nunca porque o navegador voltou da página de sucesso.

## Rodando localmente

```bash
cd saas/backend
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env                 # edite se quiser IA/Stripe
alembic upgrade head                 # cria as tabelas
python -m app.services.seed          # imobiliária de demonstração (widget da landing)

uvicorn app.main:app --reload --port 8000
```

- Landing: http://localhost:8000
- Criar conta / entrar: http://localhost:8000/entrar.html
- Painel: http://localhost:8000/app.html
- Busca da imobiliária demo: http://localhost:8000/embed.html?k=pk_demo
- Documentação da API (Swagger): http://localhost:8000/docs

## Testes

```bash
cd saas/backend && source .venv/bin/activate
python -m pytest -q
```

São 33 testes, rodando em SQLite em memória e sem rede (a IA é simulada).
Cobrem cadastro/login, isolamento entre imobiliárias, papéis (dono e
corretor), limites de plano, CRUD e importação CSV, busca, leads com
consentimento, métricas, exportação e a integração com a IA (saída
estruturada, recusa e JSON inválido).

## Como o widget funciona

A imobiliária cola isto no site:

```html
<script src="https://SEU-DOMINIO/widget.js" data-chave="pk_..." async></script>
```

O `widget.js` cria um botão flutuante (dentro de Shadow DOM) que abre um
iframe com `embed.html`. Assim, o CSS do site do cliente não interfere na
busca e vice-versa. Também existe o modo embutido (`data-modo="inline"`) e o
link direto (`/embed.html?k=pk_...`) para quem não tem site.

A chave `pk_...` é pública por natureza (fica no HTML do cliente). Por isso
ela só permite buscar imóveis ativos e enviar leads, com limite de
requisições por IP. Se alguém copiar a chave, o dono gera outra no painel.

## Segurança e LGPD já implementadas

- Senhas com bcrypt, sessão por JWT (header Bearer, sem cookie). Por isso o
  CORS aberto do widget não expõe o painel.
- Todo dado é filtrado pela imobiliária do usuário logado, e há testes de
  isolamento entre clientes.
- Rate limit em login, cadastro, busca e envio de leads.
- O lead só é aceito com a caixa de consentimento marcada. Guardamos a data e
  o texto exato aceito.
- O dono exporta os próprios dados e exclui a conta (o que apaga a imobiliária
  inteira). Leads podem ser excluídos a pedido do titular.
- Em produção, o servidor se recusa a subir com a `JWT_SECRET_KEY` padrão.

## O que falta antes de vender (fora do código)

1. **Revisão jurídica** de `frontend/termos.html` e `frontend/privacidade.html`,
   com razão social, CNPJ e contato do encarregado (DPO).
2. **Recuperação de senha por e-mail.** Exige um provedor de e-mail (Resend,
   SES etc.). Hoje o dono pode recriar o acesso de um corretor pelo painel.
3. **Upload de fotos.** Hoje o imóvel aceita a URL de uma foto já hospedada
   (no próprio site da imobiliária, por exemplo). Upload próprio exige um
   storage (S3/R2).
4. **Nota fiscal de serviço (NFS-e)** das assinaturas, que depende do seu
   CNPJ e município.
