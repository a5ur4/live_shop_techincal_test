from datetime import datetime

from pydantic import Field

from app.schemas.base import Email, Entrada, Nome, Saida, Senha


class LojaCriar(Entrada):
    nome: Nome = Field(examples=["Loja da Ana"])
    email: Email = Field(description="Login do lojista.", examples=["ana@lojadaana.com"])
    senha: Senha = Field(examples=["senha-forte-123"])


class LojaOut(Saida):
    id: int
    nome: str
    email: str
    criado_em: datetime


class LojaPublica(Saida):
    """Dados públicos da loja (sem e-mail de login)."""

    id: int
    nome: str
    criado_em: datetime


class LojaDetalhe(LojaPublica):
    total_seguidores: int
