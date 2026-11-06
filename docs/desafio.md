# Desafio Técnico: Feed de Novidades

Construa uma API pequena em que clientes seguem lojas e acompanham, num feed, as novidades que essas lojas publicam.

## Contexto

Imagine uma plataforma em que lojistas divulgam novidades: produto novo, promoção, aviso de live. Clientes seguem as lojas de que gostam e abrem o app para ver um feed com tudo o que essas lojas publicaram, do mais recente para o mais antigo.

Alguns dados do produto:

- Um cliente abre o feed várias vezes por dia. Uma loja publica poucas vezes por dia.
- A maioria das lojas tem algumas centenas de seguidores, mas as maiores passam de 100 mil.

Foque no escopo obrigatório bem feito a muitos extras pela metade.

## O que construir (obrigatório)

Uma API REST com banco relacional e cinco endpoints. Stack livre: use a linguagem e o framework que você domina.

| Método | Rota | O que faz | Regras |
| --- | --- | --- | --- |
| POST | `/lojas` | Cria uma loja (`nome`) | `nome` obrigatório |
| POST | `/clientes` | Cria um cliente (`nome`, `email`) | `email` único e campos obrigatórios |
| POST | `/clientes/{id}/seguindo/{lojaId}` | Cliente passa a seguir a loja | Cliente e loja precisam existir e não pode seguir a mesma loja duas vezes |
| POST | `/lojas/{id}/novidades` | Loja publica uma novidade (`texto`, `preco` opcional) | `texto` com 1 a 500 caracteres e `preco` maior que zero quando informado |
| GET | `/clientes/{id}/feed?limite=20` | Retorna as novidades das lojas que o cliente segue | Da mais recente para a mais antiga; `limite` padrão 20, máximo 50 |

Regras gerais:

- Erros com status HTTP coerente (400/422 para entrada inválida, 404 para recurso inexistente, 409 para conflito) e o mesmo formato de corpo de erro em toda a API.
- Banco relacional, PostgreSQL de preferência. O banco precisa subir com `docker compose up` ou ser criado automaticamente ao rodar o projeto.
- A organização do código e a modelagem do banco são decisão sua.
- Autenticação está fora do escopo: os ids vêm na rota.

## Como entregar o repositório

Trate o repositório como se um colega fosse continuar o trabalho amanhã sem poder falar com você.

**Git e organização**

- Repositório público no GitHub, com histórico de commits pequenos e mensagens que expliquem o que mudou ou o que foi desenvolvido.
- Desenvolva em uma branch e abra um **Pull Request para a `main`** com uma descrição como faria num time: o que foi feito, como testar, pendências. Pode fazer o merge depois.
- Liste as tarefas que você planejou (Issues, GitHub Projects ou um `BACKLOG.md` com checklist).
- Sem arquivos de build, dependências ou `.env` com segredos versionados. Use `.env.example`.

**README.md** com, no mínimo:

1. Como rodar o projeto do zero em poucos comandos (pré-requisitos inclusos).
2. Como rodar os testes.
3. Exemplos de chamada de cada endpoint (curl, arquivo `.http` ou coleção do Postman/Insomnia).
4. Estrutura de pastas e o papel de cada parte, em poucas linhas.
5. Decisões técnicas e o motivo de cada uma (organização do código, modelagem do banco, bibliotecas).
6. O que ficou de fora e o que você faria com mais tempo.

**Testes**

- Testes automatizados cobrindo pelo menos: o feed (só novidades de lojas seguidas, ordem correta, limite) e as validações de seguir e de publicar.
- Um comando de seed que crie lojas, clientes e novidades para facilitar o teste manual é bem-vindo.

## Diferenciais (opcionais)

Só comece algum destes depois que o obrigatório estiver pronto, testado e documentado. A ausência deles não prejudica sua avaliação.

- Deixar de seguir (`DELETE /clientes/{id}/seguindo/{lojaId}`).
- Paginação no feed, além do `limite`.
- Documentação OpenAPI/Swagger.
- CI simples (GitHub Actions rodando os testes a cada push).
- Qualquer melhoria que você considere importante para o produto, justificada no README.

## Prazo, entrega e regras

- **Prazo:** 06/11/2026 às 12h (horário de Brasília). Commits depois desse horário não serão considerados.
- **Entrega:** envie o link do repositório e do Pull Request pelo mesmo canal em que recebeu este desafio.
- **Dúvidas:** pode e deve perguntar pelo mesmo canal. Se algo não for respondido a tempo, decida, siga em frente e registre a decisão no README.
- **Uso de IA:** permitido. 
