# O que do documento de produto depende de algo fora do código

Legenda: ✅ pronto e testado · ⚠️ pronto, mas depende de algo externo ·
❌ não dá para resolver com software.

## Fase 1 — Núcleo

| Item | Situação | O que falta |
|---|---|---|
| Busca conversacional | ✅ texto, conversa em turnos, voz ⚠️ | Voz usa o reconhecimento do navegador: funciona no Chrome, Edge e Safari; **não no Firefox** e em alguns navegadores embutidos (ex.: dentro do Instagram). Para voz em qualquer navegador, é preciso um serviço de transcrição pago no servidor. |
| Match explicado | ✅ | — |
| Trava contra invenção | ✅ | Testado nas 30 buscas da demonstração (227 afirmações, 0 sem prova). Falta rodar **com a IA ligada e o estoque real da Correta** (precisa da chave da Anthropic e do feed). |
| Integração por feed XML | ✅ VRSync e Carga/Imóvel | O feed da Correta (ver COMERCIAL.md). |
| Botão de lead (WhatsApp) | ✅ | Cadastrar os WhatsApps da imobiliária e dos corretores no painel. |
| Widget com logo e cores | ✅ | — |
| Funciona bem no celular | ✅ testado em 390 px | — |

## Fase 2 — Para cobrar e reter

| Item | Situação | O que falta |
|---|---|---|
| Painel da imobiliária | ✅ | — |
| Relatório de demanda | ✅ + anúncios que precisam melhorar | — |
| Comparador | ✅ | — |
| Rankings | ✅ melhor escolha, custo-benefício, família, investimento ⚠️ valorização | Valorização automática precisa de dado de mercado que não é público para Nova Friburgo (o índice FipeZap não cobre a cidade; dados de ITBI da prefeitura ou bases pagas como DataZAP). Hoje o ranking usa a avaliação que a **própria imobiliária** registra por bairro, sempre mostrada como "segundo a imobiliária". |
| Contexto do bairro | ✅ ⚠️ | Vem do OpenStreetMap, que pode estar incompleto no interior — por isso "nada encontrado" vira "não informado", nunca "não tem". "Segurança" mostra polícia e bombeiros por perto; **índice de criminalidade** precisaria dos dados do ISP-RJ, que são por delegacia (área grande demais para comparar bairros). Com muitos clientes, o Overpass público tem limite: contratar ou hospedar um. |
| Cobrança | ✅ assinatura, valor por lead, maquete avulsa ⚠️ | Conta no Stripe (com CNPJ). **Nota fiscal de serviço (NFS-e)** depende do CNPJ e da prefeitura — usar um emissor (ex.: integração do próprio Stripe ou serviço como Nfe.io/Focus NFe). |
| Termos e LGPD | ✅ ⚠️ | **Revisão por advogado** de `termos.html` e `privacidade.html`, com razão social, CNPJ e contato do encarregado (DPO). |

## Fase 3 — Premium

| Item | Situação | O que falta |
|---|---|---|
| Planta interativa | ✅ | A imobiliária envia a imagem da planta e desenha os cômodos (uns 10 minutos por imóvel). A detecção automática dos cômodos pela IA não foi feita: errar um cômodo é o tipo de invenção que a trava existe para evitar. |
| Maquete 3D | ✅ esquemática ⚠️ | A maquete é gerada a partir dos cômodos desenhados (pisos, paredes baixas, nomes e fotos de cada cômodo). Uma maquete **fotorrealista** (paredes exatas, portas, móveis, texturas) exige um arquiteto 3D ou serviço especializado — é esse o "custo por planta processada" do documento. |
| Espelho 3D de lançamentos | ✅ | — |
| Busca por foto | ✅ ⚠️ | Precisa da chave da Anthropic (e plano Premium). A análise das fotos dos anúncios é opcional por imobiliária e tem custo por anúncio. |
| Visita de drone | ⚠️ parte de software pronta · ❌ filmagem | O widget mostra o vídeo de drone de cada imóvel. A filmagem é um serviço físico: drone, piloto, registro do equipamento na ANAC, autorização de voo no DECEA e seguro para uso profissional. Pode ser terceirizada e vendida no plano Premium. |

## Modelo de negócio

| Item | Situação | O que falta |
|---|---|---|
| Assinatura mensal por faixa de estoque | ✅ 4 planos | **Preços**: os valores (R$ 297 / 497 / 997) são provisórios e mudam por variável de ambiente, sem mexer no código. Defina depois de medir o custo (abaixo). Atenção: a Correta tem ~1.107 imóveis no site, então só cabe no Premium (ilimitado) — vale um plano "Rede" negociado. |
| Valor por resultado | ✅ cobrança por lead entregue (Stripe) | **Comissão por contrato fechado não dá para comprovar por software**: o fechamento acontece fora do sistema. O que existe: cada lead tem um código que vai na mensagem do WhatsApp, e o corretor marca "fechado" e o valor no painel — isso serve de base para um contrato de comissão, mas depende da boa-fé da imobiliária. Cobrar por lead entregue é mensurável e já está pronto. |
| Premium por imóvel (maquete) | ✅ pagamento avulso por imóvel | Conta no Stripe. |

## Custo de IA por busca (estimativa antes de medir)

Uma "busca" é cada mensagem que o comprador manda (é o que conta no limite do
plano). Cada uma faz 1 chamada de interpretação (~2.400 tokens de entrada e
~500 de saída). Quando a conversa tem pedidos livres ("sala com luz da
manhã"), vem mais 1 chamada que confere esses pedidos nos 8 melhores anúncios
(~3.800 de entrada e ~1.500 de saída). Mensagem repetida e conferência já
feita (mesmo pedido no mesmo anúncio) saem do cache e custam zero. Conta feita
com a tabela de preços atual da Anthropic, cotação de R$ 5,60 e pedidos livres
em 40% das buscas:

| Modelo | Por busca | 3.000 buscas (Essencial, R$ 297) | 10.000 (Profissional, R$ 497) | 30.000 (Premium, R$ 997) |
|---|---|---|---|---|
| Claude Opus 5.5 (o padrão hoje) | ~R$ 0,21 | ~R$ 630 | ~R$ 2.100 | ~R$ 6.300 |
| Claude Sonnet 5.5 | ~R$ 0,11 | ~R$ 315 | ~R$ 1.050 | ~R$ 3.150 |
| Claude Haiku 5.5 | ~R$ 0,005 | ~R$ 16 | ~R$ 53 | ~R$ 158 |

O teste grátis também usa a IA: até 300 buscas por mês, ~R$ 63 por conta no Opus.

**Conclusão:** com o modelo mais forte, os planos dão prejuízo se o cliente
usar o limite todo. Antes de definir preço: (1) ligue a IA, (2) rode
`python -m app.avaliacao` com o estoque real em Opus e em Haiku
(`ANTHROPIC_MODELO=claude-haiku-5-5`) e compare a qualidade das explicações,
(3) veja o custo real em `/admin.html`. Se o Haiku mantiver a qualidade, a
conta fecha com folga. Trocar de modelo é só mudar essa variável.

Os tokens foram estimados pelo tamanho dos textos enviados, então o custo
real pode ficar entre a metade e o dobro disso. O valor certo aparece no
admin assim que houver buscas com a IA ligada.

## Outros itens fora do documento, mas necessários para operar

- **Domínio, Railway e chave da Anthropic** (ver DEPLOY.md).
- **E-mail transacional** (Resend, SES…): hoje não há "esqueci minha senha" nem aviso de lead por e-mail — o lead chega no WhatsApp do corretor e no painel.
- **Armazenamento de imagens em escala**: plantas e fotos enviadas ficam no banco. Para centenas de imobiliárias, mover para um storage (S3/R2).
- **Fotos reais na vitrine**: a casa de demonstração com planta e 3D é fictícia e não tem fotos. Para a reunião, faça a planta de um imóvel real da Correta com as fotos dele.
