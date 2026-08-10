# Kaza IA — backend

API em FastAPI que dá vida real à landing page em `frontend/`: busca de
imóveis (com ou sem IA), contas de usuário e lista de espera, tudo
persistido em banco de dados.

## Rodando localmente

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env               # depois edite o .env com seus valores
alembic upgrade head               # cria as tabelas
python -m app.services.seed        # popula os 5 imóveis de exemplo

uvicorn app.main:app --reload --port 8000
```

Abra `http://localhost:8000` — o próprio backend serve a landing page
(pasta `frontend/`) e a API, sem precisar de um segundo servidor nem de
configurar CORS entre eles.

Documentação interativa da API (Swagger): `http://localhost:8000/docs`.

## Variáveis de ambiente importantes

Veja `.env.example` para a lista completa. As que mais importam:

- `JWT_SECRET_KEY` — assina os tokens de sessão. **Troque o valor padrão**
  antes de qualquer uso real; gere uma chave forte com
  `python -c "import secrets; print(secrets.token_hex(32))"`.
- `ANTHROPIC_API_KEY` — opcional. Sem ela, a busca em linguagem natural usa
  um motor de regras (regex) em vez de um modelo Claude de verdade. Com
  ela, a interpretação do pedido do usuário fica bem mais robusta. Nunca
  coloque essa chave no código do frontend — ela só deve existir no
  ambiente do backend.
- `DATABASE_URL` — `sqlite:///./kaza_ia.db` por padrão (bom para
  desenvolvimento). Em produção, aponte para um Postgres.

## Testes

```bash
source .venv/bin/activate
python -m pytest -v
```

Os testes rodam contra um banco SQLite em memória — não tocam no seu
`kaza_ia.db` local.

## Migrações (Alembic)

Depois de mudar um modelo em `app/models/`, gere a migração:

```bash
alembic revision --autogenerate -m "descreva a mudança"
alembic upgrade head
```

Sempre revise o arquivo gerado em `alembic/versions/` antes de aplicar —
autogenerate erra ocasionalmente em renomeações de coluna.

## Estrutura

```
app/
  core/        configuração, segurança (hash de senha, JWT), textos legais
  db/          conexão com o banco (SQLAlchemy)
  models/      tabelas (Usuario, Imovel, Tag, BuscaSalva, ListaEspera)
  schemas/     validação de entrada/saída (Pydantic)
  routers/     endpoints da API
  services/    lógica de negócio (motor de match, integração com IA, seed)
alembic/       migrações de banco
tests/         pytest
```

## O que falta para produção

Este backend já é funcional e testado, mas antes de ir ao ar com usuários
reais:

1. **Fonte real de imóveis** — hoje o banco só tem os 5 imóveis de exemplo
   semeados por `seed.py`. Isso depende de parceria com portais/imobiliárias
   (fora do escopo deste código).
2. **Banco de produção** — trocar SQLite por Postgres gerenciado (o código
   já está pronto para isso, só muda `DATABASE_URL`).
3. **Hospedagem** — este servidor precisa rodar em algum lugar (Railway,
   Render, Fly.io, AWS etc.) com HTTPS na frente.
4. **Revisão jurídica da LGPD** — o código trata consentimento, exportação e
   exclusão de dados, mas o texto legal (`docs/PRIVACIDADE.md`) deve passar
   por um advogado antes de valer como política oficial.
