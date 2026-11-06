from datetime import datetime
from decimal import Decimal

from app.schemas.base import Pagina, Saida


class LojaResumo(Saida):
    id: int
    nome: str


class FeedItem(Saida):
    id: int
    loja: LojaResumo
    texto: str
    preco: Decimal | None
    criado_em: datetime


class FeedOut(Pagina[FeedItem]):
    pass
