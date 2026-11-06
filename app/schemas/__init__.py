"""Contratos de entrada e saída da API (Pydantic). Um módulo por recurso."""

from app.schemas.auth import ContaOut, TokenOut
from app.schemas.base import Pagina
from app.schemas.cliente import ClienteCriar, ClienteOut, LojaSeguida, SeguindoOut
from app.schemas.feed import FeedItem, FeedOut, LojaResumo
from app.schemas.loja import LojaCriar, LojaDetalhe, LojaOut, LojaPublica
from app.schemas.novidade import NovidadeCriar, NovidadeOut

__all__ = [
    "ContaOut",
    "ClienteCriar",
    "ClienteOut",
    "FeedItem",
    "FeedOut",
    "LojaCriar",
    "LojaOut",
    "LojaDetalhe",
    "LojaPublica",
    "LojaResumo",
    "LojaSeguida",
    "NovidadeCriar",
    "NovidadeOut",
    "Pagina",
    "SeguindoOut",
    "TokenOut",
]
