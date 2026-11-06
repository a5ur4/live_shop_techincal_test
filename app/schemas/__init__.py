"""Contratos de entrada e saída da API (Pydantic). Um módulo por recurso."""

from app.schemas.auth import (
    ContaEditar,
    ContaOut,
    ExcluirContaIn,
    RefreshIn,
    TokenOut,
    TrocaSenhaIn,
)
from app.schemas.base import Pagina
from app.schemas.cliente import ClienteCriar, ClienteOut, LojaSeguida, SeguindoOut
from app.schemas.feed import FeedItem, FeedOut, LojaResumo
from app.schemas.loja import LojaCriar, LojaDetalhe, LojaOut, LojaPublica
from app.schemas.novidade import NovidadeCriar, NovidadeEditar, NovidadeOut

__all__ = [
    "ContaEditar",
    "ContaOut",
    "ExcluirContaIn",
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
    "NovidadeEditar",
    "NovidadeOut",
    "Pagina",
    "RefreshIn",
    "SeguindoOut",
    "TokenOut",
    "TrocaSenhaIn",
]
