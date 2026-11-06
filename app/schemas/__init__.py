"""Contratos de entrada e saída da API (Pydantic). Um módulo por recurso."""

from app.schemas.cliente import ClienteCriar, ClienteOut, SeguindoOut
from app.schemas.feed import FeedItem, FeedOut, LojaResumo
from app.schemas.loja import LojaCriar, LojaOut
from app.schemas.novidade import NovidadeCriar, NovidadeOut

__all__ = [
    "ClienteCriar",
    "ClienteOut",
    "FeedItem",
    "FeedOut",
    "LojaCriar",
    "LojaOut",
    "LojaResumo",
    "NovidadeCriar",
    "NovidadeOut",
    "SeguindoOut",
]
