from datetime import datetime

from pydantic import Field

from app.schemas.base import Email, Entrada, Nome, Saida, Senha
from app.schemas.loja import LojaPublica


class ClienteCriar(Entrada):
    nome: Nome = Field(examples=["João Silva"])
    email: Email = Field(examples=["joao@example.com"])
    senha: Senha = Field(examples=["senha-forte-123"])


class ClienteOut(Saida):
    id: int
    nome: str
    email: str
    criado_em: datetime


class SeguindoOut(Saida):
    cliente_id: int
    loja_id: int
    criado_em: datetime


class LojaSeguida(Saida):
    loja: LojaPublica
    seguindo_desde: datetime
