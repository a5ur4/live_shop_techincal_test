# Registros de decisão (ADR)

Cada arquivo registra **uma** decisão técnica: contexto, decisão, alternativas e consequências.
Quando uma decisão mudar, não edite o ADR antigo — crie um novo e marque o anterior como
"Substituído por NNNN".

| # | Decisão | Status |
| --- | --- | --- |
| [0001](0001-stack-e-organizacao.md) | Stack e organização do código em camadas | Aceito |
| [0002](0002-feed-fan-out-na-leitura.md) | Feed montado na leitura (fan-out on read) com LATERAL | Aceito |
| [0003](0003-formato-unico-de-erro.md) | Formato único de erro | Aceito |
| [0004](0004-regras-de-entrada.md) | Regras de validação e pontos ambíguos do enunciado | Aceito |
| [0005](0005-testes-com-postgres-real.md) | Testes de integração contra Postgres real | Aceito |
| [0006](0006-paginacao-por-cursor.md) | Paginação do feed por cursor (keyset) | Aceito |
| [0007](0007-autenticacao-oauth2-jwt.md) | Autenticação OAuth2 (password flow) com JWT, refresh token e `/me` | Aceito |
| [0008](0008-redis-cache-e-rate-limit.md) | Redis para cache do feed e rate limit, medido com benchmark | Aceito |
| [0009](0009-edicao-exclusao-e-front.md) | Edição e exclusão de novidades e contas; front de teste em /app | Aceito |

Modelo para novos ADRs:

```markdown
# NNNN. Título curto

- Status: Proposto | Aceito | Substituído por NNNN
- Data: AAAA-MM-DD

## Contexto
## Decisão
## Alternativas consideradas
## Consequências
```
