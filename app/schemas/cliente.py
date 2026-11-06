from datetime import datetime

from pydantic import Field

from app.schemas.base import Email, Entrada, Nome, Saida


class ClienteCriar(Entrada):
    nome: Nome = Field(examples=["João Silva"])
    email: Email = Field(examples=["joao@example.com"])


class ClienteOut(Saida):
    id: int
    nome: str
    email: str
    criado_em: datetime


class SeguindoOut(Saida):
    cliente_id: int
    loja_id: int
    criado_em: datetime
