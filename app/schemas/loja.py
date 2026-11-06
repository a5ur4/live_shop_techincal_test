from datetime import datetime

from pydantic import Field

from app.schemas.base import Entrada, Nome, Saida


class LojaCriar(Entrada):
    nome: Nome = Field(examples=["Loja da Ana"])


class LojaOut(Saida):
    id: int
    nome: str
    criado_em: datetime
