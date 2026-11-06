# 0003. Formato único de erro

- Status: Aceito
- Data: 2026-11-05

## Contexto

O enunciado exige status HTTP coerente e o mesmo corpo de erro em toda a API. Por padrão o
FastAPI devolve formatos diferentes: `{"detail": "..."}` para `HTTPException` e
`{"detail": [{loc, msg, type}]}` para validação.

## Decisão

Todo erro sai como:

```json
{
  "erro": {
    "codigo": "entrada_invalida",
    "mensagem": "Dados de entrada inválidos.",
    "detalhes": [{"campo": "preco", "mensagem": "Deve ser maior que 0."}]
  }
}
```

- `codigo`: string estável em snake_case, para o cliente tratar por programa (ex.:
  `loja_nao_encontrada` vs `cliente_nao_encontrado`, ambos 404).
- `mensagem`: texto em português para humanos.
- `detalhes`: sempre presente (lista vazia quando não se aplica).

Implementação em `app/core/errors.py`: services levantam `NaoEncontradoError` (404),
`ConflitoError` (409) ou `EntradaInvalidaError` (422); handlers globais convertem essas
exceções, além de `RequestValidationError`, `HTTPException` do Starlette (404/405 de rota) e
qualquer `Exception` (500, sem vazar detalhes internos).

Códigos usados hoje:

| HTTP | codigo |
| --- | --- |
| 404 | `cliente_nao_encontrado`, `loja_nao_encontrada`, `rota_nao_encontrada` |
| 405 | `metodo_nao_permitido` |
| 409 | `email_ja_cadastrado`, `ja_segue_loja` |
| 422 | `entrada_invalida` |
| 500 | `erro_interno` |

## Alternativas consideradas

- **RFC 9457 (Problem Details, `application/problem+json`)**: padrão de mercado; seria a
  escolha numa API pública. Optei por um envelope simples e em português, consistente com o
  resto da API. Migrar é trocar só `app/core/errors.py`.
- **400 para entrada inválida**: o enunciado aceita 400 ou 422; 422 é o padrão do FastAPI
  e distingue "JSON ok mas valor inválido" de requisição malformada. JSON malformado também
  sai como 422 para manter um único código de validação.

## Consequências

- Novo erro de negócio = nova subclasse ou `codigo=` específico; nunca `HTTPException` solta.
- Testes usam `assert_erro()` (`tests/helpers.py`), que valida status, formato e código.
