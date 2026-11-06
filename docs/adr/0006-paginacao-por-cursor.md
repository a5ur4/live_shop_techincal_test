# 0006. Paginação do feed por cursor (keyset)

- Status: Aceito
- Data: 2026-11-05

## Contexto

O feed é lido várias vezes por dia e está sempre recebendo novidades no topo. O cliente
precisa rolar além do `limite` sem ver itens repetidos ou pulados.

## Decisão

Paginação por **keyset** com cursor opaco:

- A resposta traz `proximo_cursor` (ou `null` quando acabou). O cliente repete a chamada com
  `?cursor=<proximo_cursor>` e o mesmo `limite` (ou outro).
- O cursor é `base64url({"c": criado_em ISO 8601, "id": id})` do último item entregue. É
  opaco para o cliente: o formato pode mudar sem quebrar o contrato.
- A próxima página é `WHERE (criado_em, id) < (:c, :id)`, aplicada **dentro** do LATERAL de
  cada loja. O Postgres usa a comparação de linha como condição do índice
  `ix_novidades_loja_feed` (confirmado com `EXPLAIN`: aparece em `Index Cond`).
- Para saber se há próxima página, busca `limite + 1` itens e devolve `limite`.
- Cursor malformado → 422 `entrada_invalida` com `detalhes: [{campo: "cursor"}]`.

## Alternativas consideradas

- **`offset`/`pagina`**: simples, mas uma novidade nova no topo desloca tudo e o cliente vê
  um item repetido na página seguinte; e `OFFSET` alto obriga o banco a ler e descartar linhas.
- **Cursor só com `criado_em`**: quebra quando duas novidades têm o mesmo horário (itens
  pulados). Por isso o `id` entra como desempate.
- **Cursor assinado (HMAC)**: impediria cursores forjados, mas um cursor forjado aqui só
  permite ler o próprio feed a partir de outro ponto — sem ganho de segurança real.

## Outras listas

O mesmo padrão vale para `GET /lojas/{id}/novidades` e `GET /clientes/{id}/seguindo`
(posição `(criado_em, id)`) e para `GET /lojas` (posição `id`, ordem crescente). O codec
fica em `app/core/paginacao.py`; ids do cursor fora de `1..2^63-1` dão 422 (senão estourariam
o `BIGINT` no Postgres — apontado pela revisão de segurança).

## Consequências

- Navegação só para frente (o caso de uso de um feed). Para "voltar ao topo", basta chamar
  sem cursor.
- Novidades publicadas durante a rolagem não aparecem nas próximas páginas; aparecem ao
  recarregar o feed sem cursor (comportamento esperado de feed).
