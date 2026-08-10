# Política de Privacidade — Kaza IA (rascunho técnico)

> **Aviso importante:** este documento foi escrito para descrever, de forma
> técnica e honesta, o que o código deste repositório realmente faz com os
> dados que coleta. Ele **não é** uma política de privacidade juridicamente
> válida. Antes de publicar qualquer versão real voltada a usuários, um
> advogado especializado em LGPD precisa revisar e assinar este texto.

## 1. Quais dados coletamos

| Dado | Quando | Onde fica | Por quê |
|---|---|---|---|
| E-mail | Ao entrar na lista de espera ou criar conta | tabela `lista_espera` ou `usuarios` | Avisar sobre o lançamento / autenticar |
| Senha | Ao criar conta | tabela `usuarios`, como hash bcrypt (nunca em texto puro) | Autenticação |
| Texto da busca | Ao usar o campo de busca | tabela `buscas_salvas`, só se o usuário estiver logado e explicitamente salvar | Permitir retomar buscas anteriores |
| Data/hora e texto do consentimento aceito | Ao aceitar os termos (lista de espera ou cadastro) | colunas `consentimento_lgpd_em` / `consentimento_lgpd_texto` | Provar que houve consentimento explícito, e com qual texto exato |

Buscas feitas no painel de demonstração (`/api/buscar`) por visitantes
**não logados** não são salvas — a busca roda e o resultado é devolvido, sem
gravar o texto digitado em nenhuma tabela.

## 2. Base legal (LGPD, art. 7º)

Usamos o **consentimento explícito** do titular como base legal: tanto o
cadastro de conta quanto a entrada na lista de espera exigem marcar uma
caixa de consentimento antes do envio — o formulário não deixa enviar sem
isso (validado tanto no front quanto no backend).

## 3. Direitos do titular já implementados no código

- **Acesso/portabilidade** — `GET /api/auth/me/dados` devolve tudo que
  temos sobre o usuário logado, em JSON.
- **Eliminação** — `DELETE /api/auth/me` apaga a conta e os dados
  associados (buscas salvas incluídas, via `cascade`). Quem só está na
  lista de espera (sem conta) pode pedir remoção via
  `DELETE /api/lista-espera/{email}`.
- **Minimização** — só pedimos o que é estritamente necessário (e-mail e
  senha). Não coletamos nome, telefone, CPF ou qualquer dado sensível.

## 4. O que ainda falta (fora do escopo deste código)

- Canal formal para o titular pedir seus direitos fora da própria interface
  (ex.: e-mail do encarregado de dados / DPO).
- Prazo de retenção definido e processo de expurgo automático de contas
  inativas.
- Registro de operações de tratamento (RIPD) se a operação crescer.
- Aviso de cookies, caso o site passe a usar analytics ou cookies de
  terceiros (hoje não usa nenhum).

## 5. Terceiros que recebem dados

- **Anthropic (API Claude)** — se `ANTHROPIC_API_KEY` estiver configurada,
  o **texto da busca** (não o e-mail nem a senha do usuário) é enviado à
  API da Anthropic para interpretação da linguagem natural. Sem a chave
  configurada, nenhum dado sai do nosso servidor para terceiros.
