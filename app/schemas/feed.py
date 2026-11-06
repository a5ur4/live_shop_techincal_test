from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.base import Saida


class LojaResumo(Saida):
    id: int
    nome: str


class FeedItem(Saida):
    id: int
    loja: LojaResumo
    texto: str
    preco: Decimal | None
    criado_em: datetime


class FeedOut(BaseModel):
    itens: list[FeedItem]
    proximo_cursor: str | None = Field(
        description="Envie em `cursor` para buscar a próxima página; `null` quando não há mais."
    )
