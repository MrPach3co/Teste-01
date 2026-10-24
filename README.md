# Kaza IA

Protótipo de busca de imóveis por linguagem natural.

```
frontend/   landing page estática (HTML/CSS/JS puro)
backend/    API em FastAPI — busca (com IA opcional), contas, lista de espera
docs/       documentação, incluindo rascunho de política de privacidade
saas/       Kaza Pro — versão SaaS para imobiliárias (app independente)
```

**Kaza Pro** (`saas/`) é o produto B2B: a imobiliária assina e coloca a busca
com IA no próprio site, com os próprios imóveis, e recebe os leads num painel.
Veja [`saas/README.md`](saas/README.md) e [`saas/DEPLOY.md`](saas/DEPLOY.md).

Para rodar tudo localmente, veja `backend/README.md` — o backend também
serve o frontend, então um único comando (`uvicorn app.main:app --reload`)
sobe o site inteiro em `http://localhost:8000`.
