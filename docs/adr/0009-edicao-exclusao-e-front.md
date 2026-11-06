# 0009. Edição e exclusão de novidades e contas; front de teste em /app

- Status: Aceito
- Data: 2026-11-06

## Contexto

Até a segunda etapa a API só criava e lia: não havia como corrigir uma novidade, mudar o
nome/e-mail da conta nem sair da plataforma. O time pediu as operações de editar e remover
(novidades, lojas e clientes) e a exclusão de conta. Pediu também um front simples que
consuma a API, para testar e verificar o fluxo sem Swagger, curl nem `requests.http`.

## Decisão

### Novidades

- `PATCH /lojas/{id}/novidades/{nid}` e `PATCH /me/novidades/{nid}`: edição **parcial**
  (só os campos enviados mudam). `preco: null` remove o preço, `texto: null` é 422 e um
  corpo vazio também é 422 (`Informe ao menos um campo`).
- `criado_em` **não muda**: a novidade não "sobe" no feed ao ser editada, porque isso
  deixaria o lojista furar a ordem cronológica editando posts antigos. A coluna nova
  `editado_em` (nula = nunca editada) aparece na resposta e no feed.
- `DELETE` nas mesmas rotas → 204. A remoção é física: a novidade não tem histórico a
  preservar.
- Novidade de **outra loja** responde `404 novidade_nao_encontrada`, igual à inexistente,
  e não 403. Assim não dá para descobrir quais ids existem em outras lojas.
- Cache do feed: editar e remover **não invalidam**, pelo mesmo motivo de publicar
  (ADR 0008: seria um DEL por seguidor). A mudança aparece em até `FEED_CACHE_TTL_S`.

### Contas (cliente e lojista)

- `PATCH /me`, `PATCH /lojas/{id}`, `PATCH /clientes/{id}`: `nome` e/ou `email`.
  - O e-mail também é o login.
  - E-mail já usado por outra conta do mesmo tipo → `409 email_ja_cadastrado`. Quem
    garante é o índice único do banco, sem corrida.
  - Senha não muda por aqui: tem rota própria (`PUT /me/senha`).
- `DELETE /me`, `DELETE /lojas/{id}`, `DELETE /clientes/{id}`:
  - Exigem a **senha atual no corpo** (`{"senha": "..."}`). Um access token roubado não
    basta para apagar a conta. Senha errada → 422 no campo `senha`.
  - A exclusão é física, em uma transação:
    - O banco apaga em cascata as relações de seguir e, numa loja, as novidades.
    - Os refresh tokens são apagados explicitamente, porque não têm FK (apontam para
      duas tabelas).
    - No cliente, o cache do feed é limpo.
  - O e-mail fica livre para um novo cadastro.
  - Um access token já emitido continua sendo um JWT válido até expirar (30 min). As
    rotas respondem `404 cliente_nao_encontrado`/`loja_nao_encontrada` porque a conta
    não existe mais.
  - Ids vêm de `IDENTITY` e nunca são reaproveitados, então esse token não passa a valer
    para outra conta.
- Base `Edicao` (`app/schemas/base.py`) para corpos de `PATCH`:
  - Exige ao menos um campo.
  - Campos obrigatórios no cadastro são declarados como `Tipo = None`, sem `| None`.
    Omitir mantém o valor; `null` falha na validação do tipo.

### Front de teste (`app/front`, servido em `/app`)

- **HTML + JavaScript puro**, sem build nem dependências. A própria API serve os
  arquivos (`StaticFiles`) e `/` redireciona para `/app/`.
  - Mesma origem: sem CORS.
  - Nada a mais para instalar: `docker compose up` já entrega o front.
- Cobre os fluxos dos dois tipos de conta:
  - **Cliente**: feed paginado com o `X-Cache`, lojas com busca e detalhe, seguir e
    deixar de seguir, lojas seguidas.
  - **Lojista**: publicar, editar e remover novidades.
  - **Ambos**: editar perfil, trocar senha e excluir conta.
- **Sessão no `sessionStorage`**: some ao fechar a aba.
  - Ao receber `401 nao_autenticado`, a página chama `POST /auth/refresh` uma vez e repete
    a requisição. Vários 401 simultâneos compartilham a mesma renovação, porque o refresh
    só vale uma vez (rotação, ADR 0007).
- **Erros**: os `detalhes` da API marcam o campo do formulário (`aria-invalid` +
  mensagem). O resto vira aviso.
- O rodapé registra as chamadas feitas: método, caminho, status, tempo e `X-Cache`. Não
  registra corpo nem token. Serve para verificar o que a página faz na API.
- **Segurança**:
  - Dados da API entram no DOM só por `textContent`, nunca `innerHTML`.
  - As respostas de `/app` levam CSP restrita a `'self'`, além de `nosniff`,
    `no-referrer` e `frame-ancestors 'none'`.
  - A CSP vale só em `/app`, porque o Swagger em `/docs` carrega JS de CDN.

## Alternativas consideradas

- **Soft delete** (`excluido_em`): preservaria histórico e permitiria desfazer. Em troca,
  toda query (feed, listas, login, unicidade de e-mail) teria de filtrar os excluídos, o
  que é fácil de esquecer. Sem requisito de auditoria, a exclusão física é mais simples e
  libera os dados de fato.
- **`DELETE` sem corpo, confirmando por re-login**: evitaria corpo em `DELETE`, que
  alguns clientes HTTP antigos não enviam. O OpenAPI 3.1, o `fetch` e o httpx suportam o
  corpo, e pedir a senha na mesma chamada é mais simples para quem integra.
- **`PUT` com o recurso inteiro**: obrigaria a reenviar todos os campos para mudar um;
  `PATCH` parcial é o que o app precisa.
- **Front em React/Vite** (ou outro framework): mais estrutura, mas exige Node, build,
  outro container e CORS. Para uma tela de teste, o custo não se paga.
- **Invalidar o cache dos seguidores ao remover uma novidade**: mesmo argumento do ADR 0008.
  Se uma remoção precisar sumir na hora (conteúdo indevido), a evolução é invalidar só
  nesse caso.

## Consequências

- Novidade removida ou editada pode continuar no feed cacheado de um seguidor por até 30s.
- Excluir uma loja com 100 mil seguidores apaga 100 mil linhas de `seguidores` em uma
  transação. É raro e aceitável. Se virar problema, o caminho é soft delete ou exclusão
  assíncrona em lotes.
- Não há "desfazer" nem recuperação de conta excluída.
- O front é ferramenta de teste e demonstração, não o produto: sem build, sem testes de
  interface automatizados (os testes cobrem que é servido e com quais cabeçalhos).
