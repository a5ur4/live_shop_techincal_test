"""Tabelas do banco (SQLAlchemy). Um módulo por entidade.

Todo modelo novo precisa ser importado aqui: o Alembic (migrations/env.py) enxerga
apenas o que estiver registrado em `Base.metadata` ao importar `app.models`.
"""

from app.models.base import EMAIL_MAX, NOME_MAX, Base
from app.models.cliente import Cliente
from app.models.loja import Loja
from app.models.novidade import TEXTO_MAX, Novidade
from app.models.refresh_token import RefreshToken
from app.models.seguidor import Seguidor

__all__ = [
    "EMAIL_MAX",
    "NOME_MAX",
    "TEXTO_MAX",
    "Base",
    "Cliente",
    "Loja",
    "Novidade",
    "RefreshToken",
    "Seguidor",
]
