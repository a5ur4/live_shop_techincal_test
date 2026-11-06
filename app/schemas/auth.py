from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.base import Edicao, Email, Entrada, Nome, Senha


class TokenOut(BaseModel):
    """Resposta do token endpoint. Nomes em inglês por exigência da RFC 6749 (OAuth2)."""

    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int = Field(description="Validade do access token, em segundos.")
    refresh_token: str = Field(description="Use em POST /auth/refresh quando o access expirar.")
    refresh_expires_in: int = Field(description="Validade do refresh token, em segundos.")


class RefreshIn(Entrada):
    refresh_token: str = Field(min_length=1, max_length=200)


class TrocaSenhaIn(Entrada):
    senha_atual: str = Field(min_length=1, max_length=128)
    nova_senha: Senha


class ContaEditar(Edicao):
    """Edição do perfil (cliente ou lojista). Senha tem rota própria: PUT /me/senha."""

    nome: Nome = Field(default=None, examples=["Ana Maria"])
    email: Email = Field(default=None, description="Também muda o login.")


class ExcluirContaIn(Entrada):
    senha: str = Field(
        min_length=1, max_length=128, description="Senha atual, para confirmar a exclusão."
    )


class ContaOut(BaseModel):
    """Perfil de quem está logado (GET /me)."""

    tipo: Literal["cliente", "loja"]
    id: int
    nome: str
    email: str
    criado_em: datetime
