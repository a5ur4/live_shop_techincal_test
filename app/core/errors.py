"""Formato único de erro da API.

Todo erro sai como::

    {"erro": {"codigo": "loja_nao_encontrada", "mensagem": "...", "detalhes": [...]}}

- `codigo`: identificador estável, em snake_case, para o cliente tratar por programa.
- `mensagem`: texto legível em português.
- `detalhes`: lista de `{campo, mensagem}` (preenchida em erros de validação).
"""

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class ErroDetalhe(BaseModel):
    campo: str | None = None
    mensagem: str


class Erro(BaseModel):
    codigo: str
    mensagem: str
    detalhes: list[ErroDetalhe] = []


class ErroResponse(BaseModel):
    erro: Erro


class AppError(Exception):
    """Erro de regra de negócio. Services levantam; o handler converte em resposta."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    codigo: str = "requisicao_invalida"

    def __init__(
        self,
        mensagem: str,
        *,
        codigo: str | None = None,
        detalhes: list[ErroDetalhe] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(mensagem)
        self.mensagem = mensagem
        if codigo:
            self.codigo = codigo
        self.detalhes = detalhes or []
        self.headers = headers


class NaoAutenticadoError(AppError):
    """401: sem token, token inválido/expirado ou credenciais erradas no login."""

    status_code = status.HTTP_401_UNAUTHORIZED
    codigo = "nao_autenticado"

    def __init__(self, mensagem: str = "Autenticação necessária.", **kwargs) -> None:
        # RFC 6750: respostas 401 de recursos protegidos por Bearer informam o esquema.
        kwargs.setdefault("headers", {"WWW-Authenticate": "Bearer"})
        super().__init__(mensagem, **kwargs)


class AcessoNegadoError(AppError):
    """403: autenticado, mas o token não pertence ao recurso da URL."""

    status_code = status.HTTP_403_FORBIDDEN
    codigo = "acesso_negado"


class NaoEncontradoError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    codigo = "nao_encontrado"


class ConflitoError(AppError):
    status_code = status.HTTP_409_CONFLICT
    codigo = "conflito"


class EntradaInvalidaError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    codigo = "entrada_invalida"


# Tradução das mensagens mais comuns do Pydantic; o resto cai no texto original.
_MENSAGENS_VALIDACAO: dict[str, str] = {
    "missing": "Campo obrigatório.",
    "string_type": "Deve ser um texto.",
    "string_too_short": "Deve ter pelo menos {min_length} caractere(s).",
    "string_too_long": "Deve ter no máximo {max_length} caracteres.",
    "greater_than": "Deve ser maior que {gt}.",
    "greater_than_equal": "Deve ser maior ou igual a {ge}.",
    "less_than_equal": "Deve ser menor ou igual a {le}.",
    "int_parsing": "Deve ser um número inteiro.",
    "int_type": "Deve ser um número inteiro.",
    "decimal_parsing": "Deve ser um número.",
    "decimal_type": "Deve ser um número.",
    "decimal_max_places": "Deve ter no máximo {decimal_places} casas decimais.",
    "decimal_max_digits": "Deve ter no máximo {max_digits} dígitos.",
    "decimal_whole_digits": "Deve ter no máximo {whole_digits} dígitos antes da vírgula.",
    "json_invalid": "JSON inválido.",
    "model_attributes_type": "O corpo da requisição deve ser um objeto JSON.",
    "dict_type": "O corpo da requisição deve ser um objeto JSON.",
    "value_error": "Valor inválido.",
}


def _campo(loc: tuple[Any, ...]) -> str | None:
    # loc vem como ("body", "email"), ("query", "limite"), ("path", "id")...
    partes = [str(p) for p in loc[1:]] if loc and loc[0] in {"body", "query", "path"} else []
    return ".".join(partes) or None


def _mensagem(erro: dict[str, Any]) -> str:
    modelo = _MENSAGENS_VALIDACAO.get(erro.get("type", ""))
    if erro.get("type") == "value_error" and "email" in erro.get("msg", ""):
        return "E-mail inválido."
    if modelo is None:
        return erro.get("msg", "Valor inválido.")
    try:
        return modelo.format(**(erro.get("ctx") or {}))
    except (KeyError, IndexError):
        return modelo


def _resposta(
    status_code: int, codigo: str, mensagem: str, detalhes=None, headers=None
) -> JSONResponse:
    corpo = ErroResponse(erro=Erro(codigo=codigo, mensagem=mensagem, detalhes=detalhes or []))
    return JSONResponse(
        status_code=status_code, content=corpo.model_dump(mode="json"), headers=headers
    )


async def _app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return _resposta(exc.status_code, exc.codigo, exc.mensagem, exc.detalhes, exc.headers)


async def _validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    detalhes = [ErroDetalhe(campo=_campo(e["loc"]), mensagem=_mensagem(e)) for e in exc.errors()]
    return _resposta(
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        "entrada_invalida",
        "Dados de entrada inválidos.",
        detalhes,
    )


_CODIGOS_HTTP = {
    404: ("rota_nao_encontrada", "Rota não encontrada."),
    405: ("metodo_nao_permitido", "Método não permitido para esta rota."),
}


async def _http_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    codigo, mensagem = _CODIGOS_HTTP.get(exc.status_code, ("erro_http", str(exc.detail)))
    return _resposta(exc.status_code, codigo, mensagem)


async def _unhandled_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("Erro não tratado", exc_info=exc)
    return _resposta(
        status.HTTP_500_INTERNAL_SERVER_ERROR, "erro_interno", "Erro interno do servidor."
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_handler)
    app.add_exception_handler(StarletteHTTPException, _http_handler)
    app.add_exception_handler(Exception, _unhandled_handler)


# --- Documentação OpenAPI ---------------------------------------------------

# Catálogo de erros: código -> (status HTTP, exemplo de mensagem). Alimenta os exemplos
# do Swagger; ao criar um código novo, adicione aqui e na tabela do ADR 0003.
CATALOGO_ERROS: dict[str, tuple[int, str]] = {
    "nao_autenticado": (401, "Token ausente, inválido ou expirado."),
    "credenciais_invalidas": (401, "E-mail ou senha incorretos."),
    "acesso_negado": (403, "Este token não dá acesso a este cliente."),
    "cliente_nao_encontrado": (404, "Cliente 42 não encontrado."),
    "loja_nao_encontrada": (404, "Loja 7 não encontrada."),
    "nao_segue_loja": (404, "Cliente 42 não segue a loja 7."),
    "email_ja_cadastrado": (409, "Já existe um cadastro com o e-mail ana@example.com."),
    "ja_segue_loja": (409, "Cliente 42 já segue a loja 7."),
    "entrada_invalida": (422, "Dados de entrada inválidos."),
    "banco_indisponivel": (503, "Banco de dados indisponível."),
}

_DESCRICOES_STATUS = {
    401: "Não autenticado",
    403: "Sem permissão para este recurso",
    404: "Recurso não encontrado",
    409: "Conflito com o estado atual",
    422: "Entrada inválida",
    503: "Serviço indisponível",
}


def respostas_erro(*codigos: str) -> dict[int | str, dict[str, Any]]:
    """Monta `responses=` de uma rota a partir dos códigos de erro que ela pode devolver."""
    respostas: dict[int | str, dict[str, Any]] = {}
    for codigo in codigos:
        status_code, mensagem = CATALOGO_ERROS[codigo]
        detalhes = (
            [{"campo": "texto", "mensagem": "Deve ter pelo menos 1 caractere(s)."}]
            if codigo == "entrada_invalida"
            else []
        )
        resposta = respostas.setdefault(
            status_code,
            {
                "model": ErroResponse,
                "description": _DESCRICOES_STATUS.get(status_code, "Erro"),
                "content": {"application/json": {"examples": {}}},
            },
        )
        resposta["content"]["application/json"]["examples"][codigo] = {
            "value": {"erro": {"codigo": codigo, "mensagem": mensagem, "detalhes": detalhes}}
        }
    return respostas
