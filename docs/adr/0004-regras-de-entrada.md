# 0004. Regras de validação e pontos ambíguos do enunciado

- Status: Aceito
- Data: 2026-11-05

## Contexto

O enunciado define as regras principais, mas deixa alguns detalhes em aberto. A orientação é
"decida, siga em frente e registre". Cada decisão abaixo tem teste correspondente.

## Decisões

| Tema | Decisão | Motivo |
| --- | --- | --- |
| Espaços em `nome`/`texto` | Removidos nas pontas antes de validar; `"   "` conta como vazio | Evita lojas e novidades "em branco" |
| Tamanho de `nome` | 1 a 120 caracteres | Limite razoável; o enunciado não define |
| `email` | Validado (formato), salvo em minúsculas, único sem diferenciar maiúsculas | `Ana@x.com` e `ana@x.com` são o mesmo endereço na prática |
| `preco` | `> 0`, até 2 casas decimais, até 12 dígitos; `NUMERIC(12,2)` no banco | Dinheiro não usa float |
| `preco` na resposta | String (`"199.90"`) | Evita perda de precisão de `float` em clientes JSON |
| `limite` fora de 1–50 | **422** (não ajusta para o máximo em silêncio) | Erro explícito é mais fácil de depurar que um corte silencioso |
| Campos desconhecidos no corpo | **422** (`extra="forbid"`) | `{"texto": "...", "preço": 10}` (com acento) seria salvo sem preço sem ninguém perceber |
| Seguir: ordem das checagens | token (401/403) → loja (404) → duplicado (409) | Autorização antes de revelar qualquer dado; cliente inexistente vira 403 (ADR 0007) |
| `senha` | 8 a 128 caracteres, sem regra de composição | Tamanho importa mais que composição (NIST 800-63B); teto limita custo do hash |
| E-mail de cliente vs. loja | Únicos dentro de cada tipo; o mesmo e-mail pode ser cliente e loja | Contas e logins independentes (ADR 0007) |
| Novidades antigas ao seguir | Aparecem no feed | Feed mostra tudo da loja, não só o que veio depois do seguir |
| Unicidade (e-mails, seguir) | Garantida no banco com `INSERT ... ON CONFLICT DO NOTHING` | Sem corrida entre "checar" e "inserir" com requisições simultâneas |
| Validação no banco | `CHECK` de `texto` e `preco` também no Postgres | Última linha de defesa se alguém inserir por fora da API |
| Formato do feed | Objeto `{"itens": [...], "proximo_cursor": ...}` em vez de lista pura | Permite paginação (ADR 0006) e novos metadados sem quebrar clientes |
| Item do feed | Inclui `loja: {id, nome}` | O app precisa mostrar de quem é a novidade sem outra chamada |

## Consequências

Mudar qualquer uma destas regras exige atualizar o teste correspondente e esta tabela.
