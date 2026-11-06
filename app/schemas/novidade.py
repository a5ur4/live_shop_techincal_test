from datetime import datetime
from decimal import Decimal

from pydantic import Field

from app.schemas.base import Entrada, Preco, Saida, Texto


class NovidadeCriar(Entrada):
    texto: Texto = Field(examples=["Chegou a coleção de verão!"])
    preco: Preco | None = Field(default=None, examples=["199.90"])


class NovidadeOut(Saida):
    id: int
    loja_id: int
    texto: str
    # Serializado como string ("199.90") para não perder precisão em JSON.
    preco: Decimal | None
    criado_em: datetime
