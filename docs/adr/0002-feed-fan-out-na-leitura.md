# 0002. Feed montado na leitura (fan-out on read) com LATERAL

- Status: Aceito
- Data: 2026-11-05

## Contexto

Dados do produto (enunciado):

- Cliente abre o feed **várias vezes por dia**; loja publica **poucas vezes por dia**.
- Maioria das lojas tem algumas centenas de seguidores; as maiores passam de **100 mil**.

Há duas estratégias clássicas:

| | Fan-out na escrita (push) | Fan-out na leitura (pull) |
| --- | --- | --- |
| Publicar | 1 insert **por seguidor** (100 mil para loja grande) | 1 insert |
| Ler o feed | `SELECT` simples numa tabela `feed_itens` do cliente | junta novidades das lojas seguidas |
| Armazenamento | cresce com publicações × seguidores | só as novidades |
| Seguir/deixar de seguir | precisa preencher/limpar o feed | imediato, nada a fazer |

## Decisão

**Fan-out na leitura**, com uma query que limita o trabalho por loja:

```sql
SELECT n.*, l.nome
FROM seguidores s
JOIN LATERAL (
    SELECT * FROM novidades n
    WHERE n.loja_id = s.loja_id
    ORDER BY n.criado_em DESC, n.id DESC
    LIMIT :limite                     -- no máximo N por loja
) n ON true
JOIN lojas l ON l.id = s.loja_id
WHERE s.cliente_id = :cliente_id
ORDER BY n.criado_em DESC, n.id DESC
LIMIT :limite;
```

Apoiada no índice `novidades (loja_id, criado_em DESC, id DESC)`: para cada loja seguida o
Postgres faz um *Index Only Scan* que para após N linhas (confirmado com `EXPLAIN`).

Custo por leitura ≈ **lojas seguidas × limite**, independente de quantas novidades existem
no total e de quantos seguidores a loja tem. Publicar custa 1 insert, mesmo para a loja de
100 mil seguidores.

Ordem: `criado_em DESC, id DESC` — o `id` desempata novidades com o mesmo horário e deixa a
ordem total e estável (pré-requisito para paginação por cursor).

## Alternativas consideradas

- **Fan-out na escrita**: leitura mais barata, mas uma publicação de loja grande vira 100 mil
  inserts (precisaria de fila/worker), o armazenamento multiplica, e seguir/deixar de seguir
  exige backfill/limpeza. Complexidade alta para o tamanho do desafio.
- **JOIN simples sem LATERAL** (`seguidores JOIN novidades ORDER BY ... LIMIT`): correto, mas o
  Postgres pode precisar ler *todas* as novidades de todas as lojas seguidas antes de ordenar.
- **Híbrido** (push para lojas pequenas, pull para lojas grandes — modelo usado por redes
  sociais): é a evolução natural se a leitura virar gargalo. Ver "Consequências".

## Consequências

- Cliente que segue muitas lojas (milhares) gera mais trabalho por leitura. Mitigações já
  aplicadas: `limite` máximo 50, `statement_timeout` de 5s nas conexões e cache da primeira
  página no Redis ([ADR 0008](0008-redis-cache-e-rate-limit.md), com benchmark: ~13 ms sem
  cache e ~2 ms com cache para um cliente que segue ~500 lojas). Próximos passos se
  necessário: limitar quantas lojas um cliente pode seguir ou o modelo híbrido.
- Seguir uma loja mostra imediatamente as novidades antigas dela no feed (decisão de produto
  registrada no ADR 0004).
