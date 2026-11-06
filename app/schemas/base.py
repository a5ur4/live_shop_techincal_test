"""Tipos e bases compartilhados pelos contratos da API."""

from decimal import Decimal
from typing import Annotated

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    model_validator,
)
from pydantic_core import PydanticCustomError

from app.models import NOME_MAX, TEXTO_MAX

# Espaços nas pontas são removidos antes de validar o tamanho: "   " conta como vazio.
Nome = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=NOME_MAX)]
Texto = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=TEXTO_MAX)]
Email = Annotated[EmailStr, AfterValidator(str.lower)]
# Sem regra de composição; só tamanho. 128 limita o custo do hash (evita DoS com senha enorme).
Senha = Annotated[str, StringConstraints(min_length=8, max_length=128)]
# Normaliza para 2 casas ("10" -> "10.00") para a resposta sair igual ao que o banco guarda.
Preco = Annotated[
    Decimal,
    Field(gt=0, max_digits=12, decimal_places=2),
    AfterValidator(lambda v: v.quantize(Decimal("0.01"))),
]


class Entrada(BaseModel):
    """Corpo de requisição: campos desconhecidos geram 422 (ver ADR 0004)."""

    model_config = ConfigDict(extra="forbid")


class Edicao(Entrada):
    """Corpo de PATCH: só os campos enviados mudam, e é preciso enviar ao menos um.

    Campos obrigatórios no cadastro são declarados aqui como `Tipo = None` (sem `| None`):
    omitir mantém o valor; enviar `null` falha na validação do tipo (422 no campo).
    Use `model_dump(exclude_unset=True)` para aplicar só o que veio.
    """

    @model_validator(mode="after")
    def _ao_menos_um_campo(self):
        if not self.model_fields_set:
            raise PydanticCustomError("edicao_vazia", "Informe ao menos um campo para alterar.")
        return self


class Saida(BaseModel):
    """Resposta: pode ser montada direto de um objeto ORM."""

    model_config = ConfigDict(from_attributes=True)


class Pagina[T](BaseModel):
    """Lista paginada por cursor (ver docs/adr/0006)."""

    itens: list[T]
    proximo_cursor: str | None = Field(
        description="Envie em `cursor` para buscar a próxima página; `null` quando não há mais."
    )
