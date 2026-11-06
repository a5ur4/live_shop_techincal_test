"""Tipos e bases compartilhados pelos contratos da API."""

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


class Entrada(BaseModel):
    """Corpo de requisição: campos desconhecidos geram 422 (ver ADR 0004)."""

    model_config = ConfigDict(extra="forbid")


class Saida(BaseModel):
    """Resposta: pode ser montada direto de um objeto ORM."""

    model_config = ConfigDict(from_attributes=True)
