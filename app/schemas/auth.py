from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class TokenOut(BaseModel):
    """Resposta do token endpoint. Nomes em inglês por exigência da RFC 6749 (OAuth2)."""

    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class ContaOut(BaseModel):
    """Perfil de quem está logado (GET /me)."""

    tipo: Literal["cliente", "loja"]
    id: int
    nome: str
    email: str
    criado_em: datetime
