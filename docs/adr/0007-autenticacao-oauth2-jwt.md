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
  Validade padrão 30 min (`JWT_EXPIRA_MINUTOS`).
- **Refresh token** (adicionado depois, ver "Sessões" abaixo): opaco, 256 bits, 30 dias.
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

## Sessões, `/me` e troca de senha (segunda etapa)

- **Rotas `/me/...`**: mesma autorização, mas a conta vem do token, não da URL.
  `GET /me` (perfil; cliente ou lojista), `GET /me/feed`, `GET /me/seguindo`,
  `POST/DELETE /me/seguindo/{lojaId}` (cliente), `POST/GET /me/novidades` (lojista),
  `PUT /me/senha` (ambos). Token do tipo errado → 403. As rotas com `{id}` continuam.
- **Refresh token**: o login devolve também `refresh_token` + `refresh_expires_in`.
  - Guardado só como SHA-256 na tabela `refresh_tokens` (alta entropia dispensa hash lento).
  - `POST /auth/refresh` faz **rotação**: o token usado é revogado e um novo é emitido na
    mesma `familia` (a "sessão"). O `UPDATE ... WHERE revogado_em IS NULL RETURNING` torna
    o uso atômico mesmo com pedidos simultâneos.
  - **Reuso** de um refresh já trocado indica vazamento: a família inteira é revogada (o
    usuário legítimo precisa logar de novo; outras sessões da conta não são afetadas).
  - `POST /auth/logout` revoga a família; sempre 204 (idempotente, não revela nada).
- **Rate limit no login**: 5 falhas por e-mail ou 20 por IP em 15 min → `429` com
  `Retry-After` (detalhes e comportamento sem Redis no ADR 0008).
- **Troca de senha** (`PUT /me/senha`): exige a senha atual (um access token roubado não
  basta) e revoga todos os refresh tokens da conta.

## Alternativas consideradas

- **Refresh token como JWT** (sem tabela): não permitiria revogar nem detectar reuso.
- **Revogar access tokens** na troca de senha/logout (lista de bloqueio ou "versão" da conta
  checada a cada requisição): custaria uma consulta por requisição; com access de 30 min,
  preferi aceitar essa janela.
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
- Access token vazado vale até expirar (30 min), mesmo após logout ou troca de senha.
- Pendências naturais: recuperação de senha por e-mail, MFA, listar/encerrar sessões ativas,
  limpeza periódica de refresh tokens expirados.
