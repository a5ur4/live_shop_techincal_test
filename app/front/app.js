// Front de teste da API do Feed de Novidades. Sem build e sem dependências.
//
// Regras deste arquivo:
// - Todo dado vindo da API entra no DOM por textContent (função `h`), nunca innerHTML.
// - Tokens ficam no sessionStorage (somem ao fechar a aba). O access token expira em
//   30 min; ao receber 401 a página tenta POST /auth/refresh uma vez e repete a chamada.

const CHAVE_SESSAO = "feed-novidades:sessao";
const LIMITE = 10;

const estado = {
  sessao: lerSessao(), // { tipo: "cliente" | "loja", access, refresh }
  conta: null, // GET /me
};

// --- Utilitários de DOM ---------------------------------------------------------------

function h(tag, props = {}, ...filhos) {
  const el = document.createElement(tag);
  for (const [chave, valor] of Object.entries(props)) {
    if (valor === undefined || valor === null || valor === false) continue;
    if (chave.startsWith("on")) el.addEventListener(chave.slice(2), valor);
    else if (chave === "class") el.className = valor;
    else if (chave in el && chave !== "list") el[chave] = valor;
    else el.setAttribute(chave, valor === true ? "" : valor);
  }
  for (const filho of filhos.flat()) {
    if (filho === null || filho === undefined || filho === false) continue;
    el.append(filho instanceof Node ? filho : document.createTextNode(String(filho)));
  }
  return el;
}

function campo(rotulo, props) {
  const entrada = props.multiline
    ? h("textarea", { ...props, multiline: undefined })
    : h("input", props);
  return h("label", {}, rotulo, entrada);
}

const moeda = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const dataHora = new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" });

function formatarData(iso) {
  return dataHora.format(new Date(iso));
}

// --- Sessão ---------------------------------------------------------------------------

function lerSessao() {
  try {
    return JSON.parse(sessionStorage.getItem(CHAVE_SESSAO));
  } catch {
    return null;
  }
}

function salvarSessao(sessao) {
  estado.sessao = sessao;
  try {
    if (sessao) sessionStorage.setItem(CHAVE_SESSAO, JSON.stringify(sessao));
    else sessionStorage.removeItem(CHAVE_SESSAO);
  } catch {
    // Sem storage (aba privada restrita): a sessão vale só enquanto a página estiver aberta.
  }
}

function encerrarSessaoLocal() {
  salvarSessao(null);
  estado.conta = null;
}

// --- Cliente HTTP ---------------------------------------------------------------------

class ErroApi extends Error {
  constructor(status, erro) {
    super(erro?.mensagem ?? `Erro HTTP ${status}`);
    this.status = status;
    this.codigo = erro?.codigo ?? "erro_http";
    this.detalhes = erro?.detalhes ?? [];
  }
}

let renovacaoEmAndamento = null;

async function api(metodo, caminho, { corpo, form, repetir = true } = {}) {
  const headers = {};
  let body;
  if (form) {
    body = new URLSearchParams(form);
  } else if (corpo !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(corpo);
  }
  if (estado.sessao) headers.Authorization = `Bearer ${estado.sessao.access}`;

  const inicio = performance.now();
  let resp;
  try {
    resp = await fetch(caminho, { method: metodo, headers, body });
  } catch {
    registrarChamada(metodo, caminho, "rede", performance.now() - inicio, null);
    throw new ErroApi(0, { codigo: "sem_conexao", mensagem: "Não foi possível falar com a API." });
  }
  const dados = resp.status === 204 ? null : await resp.json().catch(() => null);
  registrarChamada(metodo, caminho, resp.status, performance.now() - inicio, resp.headers.get("X-Cache"));

  if (resp.status === 401 && repetir && estado.sessao?.refresh && dados?.erro?.codigo === "nao_autenticado") {
    if (await renovarSessao()) return api(metodo, caminho, { corpo, form, repetir: false });
    encerrarSessaoLocal();
    avisar("Sua sessão expirou. Entre de novo.", { erro: true });
    renderizar();
  }
  if (!resp.ok) throw new ErroApi(resp.status, dados?.erro);
  return { dados, headers: resp.headers };
}

// Vários 401 simultâneos usam a mesma renovação: o refresh token só vale uma vez.
function renovarSessao() {
  renovacaoEmAndamento ??= (async () => {
    try {
      const resp = await fetch("/auth/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: estado.sessao.refresh }),
      });
      registrarChamada("POST", "/auth/refresh", resp.status, 0, null);
      if (!resp.ok) return false;
      const tokens = await resp.json();
      salvarSessao({ ...estado.sessao, access: tokens.access_token, refresh: tokens.refresh_token });
      return true;
    } catch {
      return false;
    } finally {
      renovacaoEmAndamento = null;
    }
  })();
  return renovacaoEmAndamento;
}

function comParametros(caminho, parametros) {
  const busca = new URLSearchParams();
  for (const [chave, valor] of Object.entries(parametros)) {
    if (valor !== null && valor !== undefined && valor !== "") busca.set(chave, valor);
  }
  const texto = busca.toString();
  return texto ? `${caminho}?${texto}` : caminho;
}

// --- Avisos e erros -------------------------------------------------------------------

function avisar(mensagem, { erro = false, detalhes = [] } = {}) {
  const aviso = h(
    "div",
    { class: erro ? "aviso erro" : "aviso" },
    h("div", {}, mensagem),
    detalhes.length
      ? h("ul", {}, detalhes.map((d) => h("li", {}, d.campo ? `${d.campo}: ${d.mensagem}` : d.mensagem)))
      : null,
  );
  document.getElementById("avisos").append(aviso);
  setTimeout(() => aviso.remove(), erro ? 8000 : 4000);
}

function limparErrosDoForm(form) {
  form.querySelectorAll(".erro-campo").forEach((el) => el.remove());
  form.querySelectorAll("[aria-invalid]").forEach((el) => el.removeAttribute("aria-invalid"));
}

function mostrarErro(erro, form) {
  if (!(erro instanceof ErroApi)) {
    console.error(erro);
    avisar("Erro inesperado na página.", { erro: true });
    return;
  }
  const semCampo = [];
  for (const detalhe of erro.detalhes) {
    const entrada = detalhe.campo && form?.querySelector(`[name="${CSS.escape(detalhe.campo)}"]`);
    if (entrada) {
      entrada.setAttribute("aria-invalid", "true");
      entrada.after(h("span", { class: "erro-campo" }, detalhe.mensagem));
    } else {
      semCampo.push(detalhe);
    }
  }
  avisar(`${erro.message} (${erro.status} ${erro.codigo})`, { erro: true, detalhes: semCampo });
}

// Liga um <form> a uma ação assíncrona: desabilita o botão, limpa e mostra erros.
function aoEnviar(form, acao) {
  form.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    limparErrosDoForm(form);
    const botoes = form.querySelectorAll("button");
    botoes.forEach((b) => (b.disabled = true));
    try {
      await acao(Object.fromEntries(new FormData(form)));
    } catch (erro) {
      mostrarErro(erro, form);
    } finally {
      botoes.forEach((b) => (b.disabled = false));
    }
  });
  return form;
}

async function executar(botao, acao) {
  botao.disabled = true;
  try {
    await acao();
  } catch (erro) {
    mostrarErro(erro);
  } finally {
    botao.disabled = false;
  }
}

// --- Registro de chamadas (rodapé) ------------------------------------------------------

let totalChamadas = 0;

function registrarChamada(metodo, caminho, status, ms, cache) {
  totalChamadas += 1;
  document.getElementById("registro-total").textContent = totalChamadas;
  const ok = typeof status === "number" && status < 400;
  const linha = h(
    "tr",
    {},
    h("td", {}, new Date().toLocaleTimeString("pt-BR")),
    h("td", {}, metodo),
    h("td", {}, caminho),
    h("td", { class: ok ? "status-ok" : "status-erro" }, status),
    h("td", {}, Math.round(ms)),
    h("td", {}, cache ?? ""),
  );
  const corpo = document.getElementById("registro-linhas");
  corpo.prepend(linha);
  while (corpo.children.length > 50) corpo.lastChild.remove();
}

// --- Componentes reutilizáveis -----------------------------------------------------------

// Lista paginada por cursor: `buscar(cursor)` devolve { dados, headers }.
function listaPaginada({ buscar, item, vazio, aoCarregar }) {
  const lista = h("div", { class: "lista" });
  const mais = h("button", { type: "button", hidden: true }, "Carregar mais");
  let cursor = null;

  async function carregar(reiniciar) {
    if (reiniciar) cursor = null;
    const resposta = await buscar(cursor);
    if (reiniciar) lista.replaceChildren();
    for (const dado of resposta.dados.itens) lista.append(item(dado));
    if (!lista.children.length) lista.append(h("p", { class: "vazio" }, vazio));
    cursor = resposta.dados.proximo_cursor;
    mais.hidden = !cursor;
    aoCarregar?.(resposta);
  }

  mais.addEventListener("click", () => executar(mais, () => carregar(false)));
  const recarregar = () => carregar(true).catch((erro) => mostrarErro(erro));
  return { elemento: h("div", {}, lista, h("div", { class: "acoes" }, mais)), recarregar };
}

function cartaoNovidade(novidade, { nomeLoja, acoes } = {}) {
  return h(
    "article",
    { class: "cartao" },
    h(
      "div",
      { class: "item-cabecalho" },
      h("span", { class: "item-loja" }, nomeLoja ?? `Novidade #${novidade.id}`),
      h(
        "span",
        { class: "meta" },
        formatarData(novidade.criado_em),
        novidade.editado_em ? ` · editada ${formatarData(novidade.editado_em)}` : "",
      ),
    ),
    h("p", { class: "item-texto" }, novidade.texto),
    novidade.preco !== null ? h("div", { class: "preco" }, moeda.format(Number(novidade.preco))) : null,
    acoes ? h("div", { class: "acoes" }, acoes) : null,
  );
}

function abas(definicoes) {
  const nav = h("nav", { class: "abas", role: "tablist" });
  const painel = h("section", { role: "tabpanel" });
  const botoes = definicoes.map(([rotulo, montar]) => {
    const botao = h("button", { type: "button", class: "aba", role: "tab" }, rotulo);
    botao.addEventListener("click", () => {
      botoes.forEach((b) => b.setAttribute("aria-selected", String(b === botao)));
      painel.replaceChildren(montar());
    });
    return botao;
  });
  nav.append(...botoes);
  botoes[0].click();
  return h("div", {}, nav, painel);
}

// --- Tela inicial: entrar e criar conta -----------------------------------------------

function escolhaDeTipo(nome) {
  return h(
    "div",
    { class: "escolha", role: "radiogroup" },
    h("label", {}, h("input", { type: "radio", name: nome, value: "cliente", checked: true }), "Sou cliente"),
    h("label", {}, h("input", { type: "radio", name: nome, value: "loja" }), "Sou lojista"),
  );
}

const ROTA_DO_TIPO = { cliente: "clientes", loja: "lojas" };

async function entrar(tipo, email, senha) {
  const { dados } = await api("POST", `/auth/${ROTA_DO_TIPO[tipo]}/token`, {
    form: { username: email, password: senha },
    repetir: false,
  });
  salvarSessao({ tipo, access: dados.access_token, refresh: dados.refresh_token });
}

function telaInicial() {
  const formEntrar = aoEnviar(
    h(
      "form",
      {},
      escolhaDeTipo("tipo"),
      campo("E-mail", { name: "email", type: "email", required: true, autocomplete: "username" }),
      campo("Senha", { name: "senha", type: "password", required: true, autocomplete: "current-password" }),
      h("button", { class: "primario" }, "Entrar"),
    ),
    async ({ tipo, email, senha }) => {
      await entrar(tipo, email, senha);
      await carregarConta();
    },
  );

  const formCriar = aoEnviar(
    h(
      "form",
      {},
      escolhaDeTipo("tipo"),
      campo("Nome", { name: "nome", required: true, maxLength: 120 }),
      campo("E-mail", { name: "email", type: "email", required: true, autocomplete: "username" }),
      campo("Senha (8 a 128 caracteres)", {
        name: "senha",
        type: "password",
        required: true,
        minLength: 8,
        maxLength: 128,
        autocomplete: "new-password",
      }),
      h("button", { class: "primario" }, "Criar conta"),
    ),
    async ({ tipo, nome, email, senha }) => {
      await api("POST", `/${ROTA_DO_TIPO[tipo]}`, { corpo: { nome, email, senha } });
      await entrar(tipo, email, senha);
      avisar("Conta criada.");
      await carregarConta();
    },
  );

  return h(
    "div",
    {},
    h("div", { class: "grade" }, h("div", { class: "cartao" }, h("h2", {}, "Entrar"), formEntrar),
      h("div", { class: "cartao" }, h("h2", {}, "Criar conta"), formCriar)),
    h(
      "p",
      { class: "dica" },
      "Com o seed carregado (automático no make up), há contas de exemplo com a senha senha123: ",
      "clientes carla@example.com, diego@example.com; lojistas modadaana@lojas.example.com, entre outros.",
    ),
  );
}

// --- Cliente --------------------------------------------------------------------------

async function lojasSeguidas() {
  // Até 500 lojas (10 páginas de 50): suficiente para marcar os botões de seguir.
  const ids = new Set();
  let cursor = null;
  for (let pagina = 0; pagina < 10; pagina += 1) {
    const { dados } = await api("GET", comParametros("/me/seguindo", { limite: 50, cursor }));
    dados.itens.forEach((i) => ids.add(i.loja.id));
    cursor = dados.proximo_cursor;
    if (!cursor) break;
  }
  return ids;
}

function abaFeed() {
  const info = h("span", { class: "selo" }, "X-Cache: —");
  const { elemento, recarregar } = listaPaginada({
    buscar: (cursor) => api("GET", comParametros("/me/feed", { limite: LIMITE, cursor })),
    item: (n) => cartaoNovidade(n, { nomeLoja: n.loja.nome }),
    vazio: "Seu feed está vazio. Siga lojas na aba Lojas.",
    aoCarregar: ({ headers }) => (info.textContent = `X-Cache: ${headers.get("X-Cache") ?? "—"}`),
  });
  const atualizar = h("button", { type: "button" }, "Atualizar");
  atualizar.addEventListener("click", () => executar(atualizar, recarregar));
  recarregar();
  return h(
    "div",
    {},
    h(
      "div",
      { class: "barra" },
      h("p", { class: "dica" }, "Novidades das lojas que você segue, da mais recente para a mais antiga. ",
        "A 1ª página fica em cache por até 30s."),
      h("div", { class: "acoes" }, info, atualizar),
    ),
    elemento,
  );
}

function botaoSeguir(lojaId, seguidas, aoMudar) {
  const botao = h("button", { type: "button" });
  const pintar = () => {
    const segue = seguidas.has(lojaId);
    botao.textContent = segue ? "Deixar de seguir" : "Seguir";
    botao.className = segue ? "" : "primario";
  };
  botao.addEventListener("click", () =>
    executar(botao, async () => {
      if (seguidas.has(lojaId)) {
        await api("DELETE", `/me/seguindo/${lojaId}`);
        seguidas.delete(lojaId);
      } else {
        await api("POST", `/me/seguindo/${lojaId}`);
        seguidas.add(lojaId);
      }
      pintar();
      aoMudar?.();
    }),
  );
  pintar();
  return botao;
}

function detalheDaLoja(loja) {
  const caixa = h("div", { class: "detalhe" }, h("p", { class: "meta" }, "Carregando…"));
  (async () => {
    const [{ dados: detalhe }, { dados: novidades }] = await Promise.all([
      api("GET", `/lojas/${loja.id}`),
      api("GET", comParametros(`/lojas/${loja.id}/novidades`, { limite: 5 })),
    ]);
    caixa.replaceChildren(
      h("p", { class: "meta" }, `${detalhe.total_seguidores} seguidor(es) · últimas novidades:`),
      novidades.itens.length
        ? h("div", { class: "lista" }, novidades.itens.map((n) => cartaoNovidade(n, { nomeLoja: loja.nome })))
        : h("p", { class: "vazio" }, "Esta loja ainda não publicou nada."),
    );
  })().catch((erro) => {
    caixa.replaceChildren();
    mostrarErro(erro);
  });
  return caixa;
}

function cartaoLoja(loja, seguidas) {
  const ver = h("button", { type: "button" }, "Ver novidades");
  const cartao = h(
    "article",
    { class: "cartao" },
    h(
      "div",
      { class: "item-cabecalho" },
      h("span", { class: "item-loja" }, loja.nome),
      h("span", { class: "meta" }, `loja #${loja.id} · desde ${formatarData(loja.criado_em)}`),
    ),
    h("div", { class: "acoes" }, botaoSeguir(loja.id, seguidas), ver),
  );
  let detalhe = null;
  ver.addEventListener("click", () => {
    if (detalhe) {
      detalhe.remove();
      detalhe = null;
      ver.textContent = "Ver novidades";
    } else {
      detalhe = detalheDaLoja(loja);
      cartao.append(detalhe);
      ver.textContent = "Esconder";
    }
  });
  return cartao;
}

function abaLojas() {
  let seguidas = new Set();
  let busca = "";
  const { elemento, recarregar } = listaPaginada({
    buscar: (cursor) => api("GET", comParametros("/lojas", { limite: LIMITE, cursor, q: busca })),
    item: (loja) => cartaoLoja(loja, seguidas),
    vazio: "Nenhuma loja encontrada.",
  });
  const form = aoEnviar(
    h(
      "form",
      { class: "linha" },
      campo("Buscar por nome", { name: "q", type: "search", maxLength: 120 }),
      h("button", {}, "Buscar"),
    ),
    async ({ q }) => {
      busca = q.trim();
      await recarregar();
    },
  );
  lojasSeguidas()
    .then((ids) => {
      seguidas = ids;
      return recarregar();
    })
    .catch((erro) => mostrarErro(erro));
  return h("div", {}, h("div", { class: "barra" }, form), elemento);
}

function abaSeguindo() {
  const seguidas = new Set();
  const { elemento, recarregar } = listaPaginada({
    buscar: (cursor) => api("GET", comParametros("/me/seguindo", { limite: LIMITE, cursor })),
    item: ({ loja, seguindo_desde }) => {
      seguidas.add(loja.id);
      return h(
        "article",
        { class: "cartao" },
        h(
          "div",
          { class: "item-cabecalho" },
          h("span", { class: "item-loja" }, loja.nome),
          h("span", { class: "meta" }, `seguindo desde ${formatarData(seguindo_desde)}`),
        ),
        h("div", { class: "acoes" }, botaoSeguir(loja.id, seguidas)),
      );
    },
    vazio: "Você ainda não segue nenhuma loja.",
  });
  recarregar();
  return elemento;
}

// --- Lojista --------------------------------------------------------------------------

function precoParaApi(texto) {
  const limpo = texto.trim().replace(",", ".");
  return limpo === "" ? null : limpo;
}

function campoPreco(valor = "") {
  return campo("Preço (opcional, em R$)", {
    name: "preco",
    inputMode: "decimal",
    placeholder: "199,90",
    value: valor,
    autocomplete: "off",
  });
}

function campoTexto(valor = "") {
  const contador = h("span", { class: "meta" }, `${valor.length}/500`);
  const rotulo = campo("Texto", { name: "texto", multiline: true, required: true, maxLength: 500, value: valor });
  rotulo.querySelector("textarea").addEventListener("input", (e) => {
    contador.textContent = `${e.target.value.length}/500`;
  });
  rotulo.append(contador);
  return rotulo;
}

function cartaoMinhaNovidade(novidade, recarregar) {
  const editar = h("button", { type: "button" }, "Editar");
  const remover = h("button", { type: "button", class: "perigo" }, "Remover");
  const cartao = cartaoNovidade(novidade, { acoes: [editar, remover] });

  remover.addEventListener("click", () => {
    if (!confirm("Remover esta novidade? Não dá para desfazer.")) return;
    executar(remover, async () => {
      await api("DELETE", `/me/novidades/${novidade.id}`);
      avisar("Novidade removida.");
      await recarregar();
    });
  });

  editar.addEventListener("click", () => {
    const precoAtual = novidade.preco === null ? "" : String(novidade.preco).replace(".", ",");
    const cancelar = h("button", { type: "button" }, "Cancelar");
    const form = aoEnviar(
      h(
        "form",
        { class: "cartao" },
        h("h3", {}, `Editando novidade #${novidade.id}`),
        campoTexto(novidade.texto),
        campoPreco(precoAtual),
        h("p", { class: "dica" }, "Deixe o preço vazio para remover."),
        h("div", { class: "acoes" }, h("button", { class: "primario" }, "Salvar"), cancelar),
      ),
      async ({ texto, preco }) => {
        await api("PATCH", `/me/novidades/${novidade.id}`, { corpo: { texto, preco: precoParaApi(preco) } });
        avisar("Novidade atualizada.");
        await recarregar();
      },
    );
    cancelar.addEventListener("click", () => form.replaceWith(cartao));
    cartao.replaceWith(form);
  });
  return cartao;
}

function abaMinhasNovidades() {
  let recarregarLista;
  const { elemento, recarregar } = listaPaginada({
    buscar: (cursor) => api("GET", comParametros("/me/novidades", { limite: LIMITE, cursor })),
    item: (n) => cartaoMinhaNovidade(n, () => recarregarLista()),
    vazio: "Nenhuma novidade publicada ainda.",
  });
  recarregarLista = recarregar;

  const publicar = aoEnviar(
    h(
      "form",
      { class: "cartao" },
      h("h2", {}, "Publicar novidade"),
      campoTexto(),
      campoPreco(),
      h("div", { class: "acoes" }, h("button", { class: "primario" }, "Publicar")),
    ),
    async ({ texto, preco }) => {
      const corpo = { texto };
      const valor = precoParaApi(preco);
      if (valor !== null) corpo.preco = valor;
      await api("POST", "/me/novidades", { corpo });
      publicar.reset();
      publicar.querySelector(".meta").textContent = "0/500";
      avisar("Novidade publicada. Nos feeds já abertos, aparece em até 30s (cache).");
      await recarregar();
    },
  );

  recarregar();
  return h("div", { class: "lista" }, publicar, h("h2", {}, "Minhas novidades"), elemento);
}

// --- Minha conta (cliente e lojista) -------------------------------------------------

function abaConta() {
  const conta = estado.conta;

  const perfil = aoEnviar(
    h(
      "form",
      { class: "cartao" },
      h("h2", {}, "Perfil"),
      h("p", { class: "meta" }, `${conta.tipo === "loja" ? "Loja" : "Cliente"} #${conta.id} · desde ${formatarData(conta.criado_em)}`),
      campo("Nome", { name: "nome", required: true, maxLength: 120, value: conta.nome }),
      campo("E-mail (também é o login)", { name: "email", type: "email", required: true, value: conta.email }),
      h("div", { class: "acoes" }, h("button", { class: "primario" }, "Salvar")),
    ),
    async ({ nome, email }) => {
      // PATCH parcial: só manda o que mudou.
      const atual = estado.conta;
      const corpo = {};
      if (nome.trim() !== atual.nome) corpo.nome = nome;
      if (email.trim().toLowerCase() !== atual.email) corpo.email = email;
      if (!Object.keys(corpo).length) {
        avisar("Nada mudou.");
        return;
      }
      const { dados } = await api("PATCH", "/me", { corpo });
      estado.conta = dados;
      avisar("Perfil atualizado.");
      renderizarTopo();
    },
  );

  const senha = aoEnviar(
    h(
      "form",
      { class: "cartao" },
      h("h2", {}, "Trocar senha"),
      campo("Senha atual", { name: "senha_atual", type: "password", required: true, autocomplete: "current-password" }),
      campo("Nova senha (8 a 128)", {
        name: "nova_senha",
        type: "password",
        required: true,
        minLength: 8,
        maxLength: 128,
        autocomplete: "new-password",
      }),
      h("p", { class: "dica" }, "Encerra todas as sessões; esta página entra de novo com a senha nova."),
      h("div", { class: "acoes" }, h("button", { class: "primario" }, "Trocar senha")),
    ),
    async ({ senha_atual, nova_senha }) => {
      await api("PUT", "/me/senha", { corpo: { senha_atual, nova_senha } });
      await entrar(estado.conta.tipo, estado.conta.email, nova_senha);
      senha.reset();
      avisar("Senha trocada.");
    },
  );

  const oQueSome =
    conta.tipo === "loja"
      ? "a loja, todas as novidades publicadas e os seguidores"
      : "a conta e a lista de lojas seguidas";
  const excluir = aoEnviar(
    h(
      "form",
      { class: "cartao zona-perigo" },
      h("h2", {}, "Excluir conta"),
      h("p", { class: "dica" }, `Definitivo: apaga ${oQueSome}. Confirme com a senha.`),
      campo("Senha atual", { name: "senha", type: "password", required: true, autocomplete: "current-password" }),
      h("div", { class: "acoes" }, h("button", { class: "perigo" }, "Excluir minha conta")),
    ),
    async ({ senha: senhaAtual }) => {
      if (!confirm("Excluir a conta definitivamente?")) return;
      await api("DELETE", "/me", { corpo: { senha: senhaAtual } });
      encerrarSessaoLocal();
      avisar("Conta excluída.");
      renderizar();
    },
  );

  return h("div", { class: "grade" }, perfil, senha, excluir);
}

// --- Montagem -------------------------------------------------------------------------

async function sair() {
  const refresh = estado.sessao?.refresh;
  encerrarSessaoLocal();
  renderizar();
  if (refresh) {
    await api("POST", "/auth/logout", { corpo: { refresh_token: refresh }, repetir: false }).catch(() => {});
  }
}

function renderizarTopo() {
  const sessao = document.getElementById("sessao");
  if (!estado.conta) {
    sessao.replaceChildren();
    return;
  }
  const botaoSair = h("button", { type: "button" }, "Sair");
  botaoSair.addEventListener("click", sair);
  sessao.replaceChildren(
    h("span", {}, `${estado.conta.nome} (${estado.conta.tipo === "loja" ? "lojista" : "cliente"})`),
    botaoSair,
  );
}

function renderizar() {
  renderizarTopo();
  const app = document.getElementById("app");
  if (!estado.conta) {
    app.replaceChildren(telaInicial());
  } else if (estado.conta.tipo === "cliente") {
    app.replaceChildren(
      abas([
        ["Feed", abaFeed],
        ["Lojas", abaLojas],
        ["Seguindo", abaSeguindo],
        ["Minha conta", abaConta],
      ]),
    );
  } else {
    app.replaceChildren(
      abas([
        ["Minhas novidades", abaMinhasNovidades],
        ["Minha conta", abaConta],
      ]),
    );
  }
}

async function carregarConta() {
  try {
    estado.conta = estado.sessao ? (await api("GET", "/me")).dados : null;
  } catch (erro) {
    // Token inválido ou conta excluída em outra aba: volta para a tela de entrada.
    if (erro instanceof ErroApi && [401, 403, 404].includes(erro.status)) encerrarSessaoLocal();
    else mostrarErro(erro);
  }
  renderizar();
}

carregarConta();
