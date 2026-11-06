# 0007. Autenticação OAuth2 (password flow) com JWT

- Status: Aceito
- Data: 2026-11-05

## Contexto

O enunciado deixa autenticação fora do escopo ("os ids vêm na rota"). Sem ela, qualquer um
segue lojas, lê o feed ou publica em nome de qualquer conta só trocando o id da URL. Por
decisão do time (em conversa no desenvolvimento), a API passou a ter autenticação no padrão
de mercado, **sem mudar as rotas do enunciado**.

## Decisão

- **Quem faz login**: clientes e lojistas, com contas independentes. Cada loja tem
  `email` + `senha` próprios; o mesmo e-mail pode existir como cliente e como loja.
- **Fluxo**: OAuth2 *Resource Owner Password Credentials* (RFC 6749, seção 4.3), que é o
  fluxo nativo do FastAPI e do botão **Authorize** do Swagger:
  - `POST /auth/clientes/token` e `POST /auth/lojas/token`, corpo
    `application/x-www-form-urlencoded` com `username` (e-mail) e `password`;
  - resposta `{"access_token", "token_type": "bearer", "expires_in"}` (nomes da RFC).
- **Token**: JWT HS256 (PyJWT) com `sub` (id), `tipo` (`cliente`/`loja`), `iat`, `exp`.
  Validade padrão 30 min (`JWT_EXPIRA_MINUTOS`). Só *access token*, sem refresh.
- **Chave**: `JWT_SECRET` (mínimo 32 caracteres). Sem ela, a API gera uma chave aleatória
  a cada start e loga um aviso — `docker compose up` continua funcionando sem configuração,
  mas os tokens deixam de valer ao reiniciar e não funcionaria com várias instâncias.
- **Senhas**: argon2id via `pwdlib` (recomendação atual da documentação do FastAPI).
  8 a 128 caracteres; o teto limita o custo de hash de senhas gigantes.
- **Autorização** — as rotas mantêm o id na URL, e o token precisa ser do dono:

  | Rota | Exige |
  | --- | --- |
  | `POST /lojas`, `POST /clientes`, `POST /auth/*/token`, `GET /health` | nada (público) |
  | `POST/DELETE /clientes/{id}/seguindo/{lojaId}`, `GET /clientes/{id}/feed` | token de **cliente** com `sub == id` |
  | `POST /lojas/{id}/novidades` | token de **loja** com `sub == id` |

  Implementado como dependências `ClienteAutenticado` / `LojaAutenticada` em
  `app/routes/deps.py`, usadas no lugar do parâmetro de id da rota.
- **Erros** (formato padrão, ADR 0003):
  - `401 nao_autenticado` — sem token, malformado, assinatura inválida ou expirado; com
    header `WWW-Authenticate: Bearer` (RFC 6750);
  - `401 credenciais_invalidas` — login com e-mail inexistente **ou** senha errada (mesma
    mensagem e mesmo custo de verificação, para não revelar quais e-mails existem);
  - `403 acesso_negado` — token válido, mas de outra conta ou de outro tipo.

## Alternativas consideradas

- **Rotas `/me/...` derivando o id do token**: padrão comum, mas exigiria duplicar ou trocar
  as rotas do enunciado. Fica como evolução (o id da URL vira redundante com o token).
- **Refresh token**: melhor experiência em produção; exige armazenamento, rotação e
  revogação. Fora do escopo do desafio.
- **Authorization Code + provedor externo (Keycloak, Auth0, Cognito)**: o certo para um
  produto real com app e terceiros; desproporcional aqui. A validação de JWT já isolada em
  `app/core/security.py` facilita trocar HS256 por RS256/JWKS de um provedor.
- **Uma tabela `usuarios` com papel**: unificaria login, mas mistura dois públicos com
  dados diferentes. Com contas separadas, cada login tem seu endpoint e esquema no Swagger.
- **Auth ligável por variável**: manteria o contrato original com a flag desligada, mas
  dobra os caminhos a testar.

## Consequências

- Mudança de contrato em relação ao enunciado: cadastros exigem `senha` (e loja, `email`) e
  as rotas protegidas exigem `Authorization: Bearer`. README e `requests.http` mostram o
  fluxo completo; o seed cria contas com senha conhecida.
- "Cliente/loja inexistente" nas rotas protegidas vira `403` (o token nunca é de um id que
  não existe), o que também evita enumerar ids.
- Sem refresh nem revogação: um token vazado vale até expirar. Mitigação: validade curta.
- Pendências naturais: rate limiting no login, refresh token, rotas `/me`, troca de senha.
