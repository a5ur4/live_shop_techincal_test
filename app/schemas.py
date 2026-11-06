"""Contratos de entrada e saída da API (Pydantic)."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field, StringConstraints

from app.models import NOME_MAX, TEXTO_MAX

# Espaços nas pontas são removidos antes de validar o tamanho: "   " conta como vazio.
Nome = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=NOME_MAX)]
Texto = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=TEXTO_MAX)]
Email = Annotated[EmailStr, AfterValidator(str.lower)]
# Normaliza para 2 casas ("10" -> "10.00") para a resposta sair igual ao que o banco guarda.
Preco = Annotated[
    Decimal,
    Field(gt=0, max_digits=12, decimal_places=2),
    AfterValidator(lambda v: v.quantize(Decimal("0.01"))),
]


class _Entrada(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _Saida(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Lojas -------------------------------------------------------------------


class LojaCriar(_Entrada):
    nome: Nome = Field(examples=["Loja da Ana"])


class LojaOut(_Saida):
    id: int
    nome: str
    criado_em: datetime


# --- Clientes ----------------------------------------------------------------


class ClienteCriar(_Entrada):
    nome: Nome = Field(examples=["João Silva"])
    email: Email = Field(examples=["joao@example.com"])


class ClienteOut(_Saida):
    id: int
    nome: str
    email: str
    criado_em: datetime
