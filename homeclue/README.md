# Homeclue — busca com IA no site da imobiliária

A Homeclue é um motor de busca com IA instalado no site de cada imobiliária.
O comprador descreve em linguagem normal o imóvel que quer (escrevendo,
falando ou mandando uma foto), e a IA mostra os imóveis **daquela
imobiliária** com a taxa de compatibilidade e a explicação de cada ponto.
Quem gostou chama o corretor no WhatsApp, já com o resumo do que procura.

A Homeclue não é imobiliária, não é portal e não é dona da transação.

```
homeclue/
  backend/     API (FastAPI): busca, match explicado, feed XML, leads, painel, lançamentos, IA
  frontend/    site, widget, painel da imobiliária e /admin.html (HTML/CSS/JS, sem build)
  Dockerfile   imagem única (o backend serve o frontend)
  DEPLOY.md    como pôr no ar (Railway + Postgres + Stripe)
  PENDENCIAS.md  o que do documento de produto depende de algo fora do código
  COMERCIAL.md   Correta, imobiliárias da região e roteiro da demonstração
```

## Como o documento de produto virou software

| Documento | Onde está |
|---|---|
| Busca conversacional (escreve ou fala) | Widget (`frontend/js/widget/`), conversa em turnos que refina, troca e tira critérios; voz pelo reconhecimento de fala do navegador |
| Match explicado | `backend/app/services/busca/avaliacao.py`: cada pedido vira um ponto com status (atende, quase, parece ter, não informado, não atende) e a **prova** |
| Trava contra invenção | Prova obrigatória para cada afirmação; a IA cita trechos e `busca/evidencia.py` confere no texto real; negações ("não aceita animais") viram "não atende"; o que falta vira "não informado". `python -m app.avaliacao` confere 30 buscas afirmação por afirmação |
| Integração por feed XML | `services/feed/`: VRSync (ZAP/VivaReal/OLX) e "Carga/Imóvel"; download seguro; sincroniza a cada 6 h; feed vazio nunca apaga estoque |
| Botão de lead | WhatsApp do corretor responsável (ou da imobiliária) com o imóvel, o resumo da busca e um **código**; o lead cai no painel sem dado pessoal; formulário com consentimento para quem prefere |
| Widget instalável | `frontend/widget.js`: uma linha de código, botão flutuante ou embutido, logo e cores da imobiliária |
| Funciona bem no celular | Widget pensado primeiro para tela pequena (testado em 390 px) |
| Painel da imobiliária | Buscas, conversas, leads por origem, conversão, imóveis mais vistos, negócios fechados |
| Relatório de demanda | O que procuram, o que acham, o que não acham, itens sem oferta e **anúncios que precisam melhorar** |
| Comparador e rankings | Até 3 imóveis lado a lado; melhor escolha, custo-benefício, família, investimento e valorização, todos com o motivo |
| Contexto do bairro | Escolas, saúde, comércio, transporte, natureza, segurança e praia, a partir do OpenStreetMap |
| Cobrança, termos e LGPD | Stripe (assinatura, valor por lead, maquete avulsa), termos e privacidade, consentimento versionado, exportar/excluir dados |
| Planta interativa | Editor no painel (desenha cômodos sobre a planta); no widget, destaca os cômodos que bateram com o pedido |
| Maquete 3D | Gerada a partir da planta (three.js), com as fotos de cada cômodo |
| Espelho 3D de lançamentos | Torres × andares × unidades por status, em grade e em 3D |
| Busca por foto | O comprador manda uma foto; a IA descreve e a busca usa como critério (a foto não é guardada) |
| Visita de drone | Campo de vídeo de drone no imóvel, exibido no widget (a filmagem em si é serviço físico — ver PENDENCIAS.md) |
| Custo de IA por busca | Medido em toda busca (tokens e US$) e mostrado em `/admin.html` |

## Rodando localmente

```bash
cd homeclue/backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env               # opcional: chaves de IA e Stripe
alembic upgrade head
python -m app.services.seed        # imobiliária de demonstração (Serra e Lagos)
uvicorn app.main:app --reload --port 8000
```

- Site: http://localhost:8000 · Painel: http://localhost:8000/entrar.html
- Busca da demonstração: http://localhost:8000/embed.html?k=pk_demo
- Admin (custo de IA): http://localhost:8000/admin.html (e-mail em `ADMIN_EMAILS`)
- API: http://localhost:8000/docs

Sem `ANTHROPIC_API_KEY`, tudo funciona com o motor de regras; com a chave,
a Claude interpreta a conversa e confere os pedidos livres nos anúncios.

## Testes e avaliação

```bash
cd homeclue/backend && source .venv/bin/activate
python -m pytest -q                       # 76 testes, sem rede e sem IA de verdade
TESTE_DATABASE_URL=postgresql+psycopg2://usuario@localhost/banco_vazio python -m pytest -q  # os mesmos, no Postgres
python -m app.avaliacao --saida avaliacao.html          # 30 buscas na demonstração
python -m app.avaliacao --chave pk_DA_IMOBILIARIA       # 30 buscas no estoque real
python -m app.avaliacao --buscas minhas-buscas.txt      # suas buscas, uma por linha
```

A avaliação termina com erro se qualquer afirmação não tiver prova no
anúncio. Com a IA ligada, ela também mostra o custo das 30 buscas — sem
cache, para medir o que cada busca custa de fato (cada rodada paga as chamadas).

## Arquitetura (resumo)

- **Busca** (`services/busca/motor.py`): interpreta (IA com cache, ou regras) →
  filtra por finalidade → avalia cada imóvel ponto a ponto → a IA confere os
  pedidos livres dos 8 melhores (com verificação dos trechos; cada par pedido ×
  anúncio já conferido sai do cache, então a conversa não paga de novo) → ordena →
  rankings → mensagem, avisos ("nenhum anúncio informa…") e sugestões.
- **Tarefas em segundo plano** (`services/tarefas.py`): fila no próprio banco,
  sem Redis; sincroniza feeds, calcula contexto do bairro, analisa fotos e
  registra leads no Stripe.
- **Multi-imobiliária**: todo dado é filtrado pela imobiliária do usuário;
  há testes de isolamento.
- **Imagens**: reprocessadas pelo Pillow (sem metadados, tamanho limitado) e
  guardadas no banco (ver PENDENCIAS.md sobre storage em escala).
