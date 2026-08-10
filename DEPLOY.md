# Deploy no Railway

Passo a passo para colocar o Kaza IA no ar com um link público de verdade.
O repositório já está pronto (`Dockerfile` + `railway.toml` na raiz) — o
Railway detecta tudo sozinho, você só precisa criar a conta e clicar em
alguns botões.

## 1. Criar a conta e o projeto

1. Acesse [railway.app](https://railway.app) e entre com sua conta do GitHub.
2. Clique em **New Project** → **Deploy from GitHub repo**.
3. Autorize o Railway a acessar o repositório `MrPach3co/Teste-01` (se for a
   primeira vez, ele vai pedir permissão do GitHub).
4. Selecione o repositório. O Railway vai encontrar o `Dockerfile` na raiz
   automaticamente e começar a construir a imagem — isso já sobe um serviço,
   mas ele ainda não vai funcionar 100% até o passo 2 e 3 abaixo.

## 2. Adicionar um banco Postgres

O SQLite que usamos em desenvolvimento não é persistente em produção (o
disco do container é apagado a cada novo deploy). Por isso:

1. No mesmo projeto, clique em **+ New** → **Database** → **Add PostgreSQL**.
2. Isso cria um segundo serviço no projeto, só com o banco.

## 3. Configurar as variáveis de ambiente

Clique no serviço do **backend** (não no do Postgres) → aba **Variables** →
adicione:

| Variável | Valor |
|---|---|
| `DATABASE_URL` | Clique em "New Variable" → "Add Reference" → selecione o serviço Postgres → escolha `DATABASE_URL`. Isso conecta os dois serviços automaticamente. |
| `JWT_SECRET_KEY` | Gere uma localmente: `python3 -c "import secrets; print(secrets.token_hex(32))"` e cole o resultado aqui. |
| `AMBIENTE` | `producao` |
| `CORS_ORIGENS` | Pode deixar o padrão por enquanto (o backend serve o próprio frontend, então não depende disso). |
| `ANTHROPIC_API_KEY` | Opcional. Só preencha se você já tiver uma chave da Anthropic — sem ela, a busca usa o motor de regras (funciona igual, só que sem IA de verdade interpretando a frase). |

O Railway reinicia o serviço automaticamente sempre que uma variável muda.

## 4. Gerar o link público

1. No serviço do backend, vá em **Settings** → **Networking**.
2. Clique em **Generate Domain**.
3. Em alguns segundos você terá uma URL tipo
   `https://kaza-ia-production.up.railway.app` — esse é o link real da
   plataforma, acessível de qualquer navegador.

## O que acontece automaticamente a cada deploy

O `entrypoint.sh` roda, nesta ordem, toda vez que o container sobe:

1. `alembic upgrade head` — aplica migrações pendentes no banco.
2. `python -m app.services.seed` — garante os 5 imóveis de exemplo (não
   duplica se já existirem).
3. Sobe o servidor (`uvicorn`) escutando na porta que o Railway define.

Ou seja: dar push numa branch conectada ao Railway já é suficiente para
atualizar a plataforma no ar — nenhum passo manual extra.

## Verificando que subiu certo

Depois que o deploy terminar (a Railway mostra o status "Active" em verde):

```bash
curl https://SEU-DOMINIO.up.railway.app/api/saude
# deve responder: {"status":"ok"}
```

E abrindo a URL no navegador, a landing page completa (com a busca
funcionando de verdade) deve aparecer.

## Próxima branch / produção

Este guia assume o deploy a partir da branch atual
(`claude/kaza-ia-visual-prototype-8p9sj8`). Quando o código for mesclado
na branch principal, é só trocar, nas configurações do serviço no Railway,
qual branch ele acompanha (**Settings** → **Source** → **Branch**).
