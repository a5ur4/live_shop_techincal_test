# 0008. Redis para cache do feed e rate limit do login, medido com benchmark

- Status: Aceito
- Data: 2026-11-06

## Contexto

O ADR 0002 escolheu montar o feed na leitura. Os dados do produto dizem que o cliente abre o
feed **várias vezes por dia** e que as lojas publicam **poucas vezes por dia**: na maior parte
das aberturas, a primeira página é idêntica à anterior e está sendo recalculada à toa. Além
disso, o login (ADR 0007) precisa de um contador de falhas compartilhado entre instâncias da
API para conter força bruta.

## Decisão

**Redis 7** no `docker compose` (sem persistência: os dados são descartáveis), usado para:

### 1. Cache da primeira página do feed (`app/services/cache_feed.py`)

- Só a primeira página (sem `cursor`). Páginas seguintes são lidas raramente e o keyset já
  as deixa baratas.
- Um hash por cliente (`feed:{cliente_id}`), um campo por `limite`, TTL de 30s
  (`FEED_CACHE_TTL_S`; `0` desliga). O TTL é definido com `EXPIRE ... NX`, então gravar outro
  `limite` não estende a vida do hash.
- **Seguir/deixar de seguir** apaga o cache do cliente na hora, *depois* do commit (se fosse
  antes, uma leitura concorrente poderia repovoar o cache com o estado antigo).
- **Publicar não invalida nada**: invalidar o cache de todos os seguidores de uma loja de 100
  mil seria 100 mil `DEL` por publicação — exatamente o custo de fan-out na escrita que o
  ADR 0002 evitou. A novidade aparece no feed em até 30s. Para um feed de novidades de loja,
  esse atraso é aceitável.
- Header `X-Cache: HIT | MISS | BYPASS` nas respostas do feed, para depuração e testes.

### 2. Rate limit do login (`app/services/rate_limit.py`)

- Janela fixa de 15 min: 5 falhas por e-mail (por tipo de conta) ou 20 por IP → `429
  muitas_tentativas` com `Retry-After`. Login certo zera o contador do e-mail.
- Bloqueia mesmo com a senha certa durante a janela (senão o atacante saberia quando acertou).

### Falha do Redis

O Redis é acessório; a API nunca para por causa dele (`ResilientRedis` em
`app/core/redis.py`, timeouts de 0,5s):

- **Cache**: ignorado; o feed sai do banco (`X-Cache: MISS`).
- **Rate limit**: cai para contadores **em memória do processo**. O limite continua valendo
  (por instância), em vez de "liberar geral" — derrubar o Redis não pode virar passe livre
  para força bruta. Apontado pela revisão de segurança.
- O `/health` público não revela o estado do Redis (seria um oráculo para o atacante); a
  falha vai só para o log.

## Medição (`make benchmark`)

Banco separado (`feed_bench`) com 100 mil clientes, 2.001 lojas (a loja 1 seguida por todos),
~600 mil relações de seguir e ~100 mil novidades. Chamadas pela app real em processo (httpx +
ASGI, sem rede/uvicorn), sequenciais, numa máquina de desenvolvimento:

| Cenário | Requisições | p50 (ms) | p95 (ms) | p99 (ms) |
| --- | --- | --- | --- | --- |
| Publicar na loja de 100 mil seguidores | 200 | 5.7 | 7.6 | 30.5 |
| Feed, cliente típico (6 lojas), sem cache | 300 | 5.7 | 6.7 | 8.0 |
| Feed, pior caso (~500 lojas seguidas), sem cache | 200 | 13.3 | 14.5 | 15.1 |
| Feed, pior caso, 2ª página (cursor) | 200 | 13.5 | 15.4 | 16.8 |
| Feed, pior caso, com cache (HIT) | 300 | 2.3 | 2.8 | 3.2 |
| Detalhe da loja grande (COUNT de 100 mil) | 200 | 11.2 | 12.3 | 13.6 |

`EXPLAIN ANALYZE` do feed no pior caso: ~11 ms de execução no Postgres.

Leitura dos números:

- Publicar custa o mesmo para qualquer loja (1 insert): confirma o ADR 0002.
- O feed cresce com o número de lojas seguidas (6 → ~500 lojas: 5,7 → 13 ms), não com o
  número de seguidores das lojas nem com o total de novidades.
- O cache corta o pior caso em ~6× e tira o banco do caminho nas aberturas repetidas.
- O `COUNT` de seguidores da loja grande (~11 ms) é o próximo candidato a otimizar se
  `GET /lojas/{id}` ficar quente: contador desnormalizado ou cache.

## Alternativas consideradas

- **Feed híbrido (fan-out na escrita para lojas pequenas)**: reduziria o pior caso de leitura,
  mas exige tabela de feed materializado, worker e backfill ao seguir. Os números acima não
  justificam essa complexidade hoje; continua sendo a evolução se o feed sem cache passar de
  algumas dezenas de ms.
- **Invalidar o cache dos seguidores na publicação** (só para lojas pequenas): deixaria o
  feed instantâneo para a maioria, ao custo de um caminho diferente por tamanho de loja.
  Possível evolução se 30s de atraso incomodar o produto.
- **Cache HTTP (`Cache-Control`/ETag)**: o feed é privado e autenticado; cache de borda não
  ajuda, e ETag ainda exigiria calcular o feed.
- **Rate limit no Postgres**: sem nova infraestrutura, mas uma escrita no banco a cada falha
  de login e limpeza de linhas antigas; o Redis faz isso nativamente com TTL.
- **Rate limit que falha fechado (503 sem Redis)**: mais seguro, mas tira o login do ar por
  causa de um componente acessório. O fallback em memória mantém os dois.

## Consequências

- Mais um serviço no compose e no CI (Redis), com `REDIS_URL` vazio desligando tudo.
- Novidade publicada leva até `FEED_CACHE_TTL_S` segundos para aparecer no feed já aberto.
- Com várias instâncias e o Redis fora, cada instância conta as falhas sozinha: o limite
  efetivo vira "5 × número de instâncias" até o Redis voltar.
- Benchmark versionado: rode `make benchmark` antes e depois de mexer na query do feed.
