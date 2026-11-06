"""Cursores opacos para paginação por keyset (ver docs/adr/0006).

Dois formatos, ambos base64url de um JSON pequeno:
- posição `(criado_em, id)`: listas em ordem cronológica decrescente (feed, novidades,
  lojas seguidas);
- posição `id`: listas em ordem crescente de id (lojas).
"""

import base64
import binascii
import json
from datetime import datetime
from typing import Any

from app.core.errors import EntradaInvalidaError, ErroDetalhe

Posicao = tuple[datetime, int]


def _codificar(dados: dict[str, Any]) -> str:
    bruto = json.dumps(dados, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(bruto).decode().rstrip("=")


def _decodificar(cursor: str) -> dict[str, Any]:
    bruto = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4))
    dados = json.loads(bruto)
    if not isinstance(dados, dict):
        raise ValueError
    return dados


def _cursor_invalido() -> EntradaInvalidaError:
    return EntradaInvalidaError(
        "Dados de entrada inválidos.",
        detalhes=[ErroDetalhe(campo="cursor", mensagem="Cursor inválido.")],
    )


def codificar_posicao(criado_em: datetime, item_id: int) -> str:
    return _codificar({"c": criado_em.isoformat(), "id": item_id})


def decodificar_posicao(cursor: str) -> Posicao:
    try:
        dados = _decodificar(cursor)
        criado_em = datetime.fromisoformat(dados["c"])
        item_id = dados["id"]
        if criado_em.tzinfo is None or type(item_id) is not int:
            raise ValueError
    except (binascii.Error, UnicodeDecodeError, ValueError, KeyError, TypeError) as exc:
        raise _cursor_invalido() from exc
    return criado_em, item_id


def codificar_id(item_id: int) -> str:
    return _codificar({"id": item_id})


def decodificar_id(cursor: str) -> int:
    try:
        item_id = _decodificar(cursor)["id"]
        if type(item_id) is not int:
            raise ValueError
    except (binascii.Error, UnicodeDecodeError, ValueError, KeyError, TypeError) as exc:
        raise _cursor_invalido() from exc
    return item_id
