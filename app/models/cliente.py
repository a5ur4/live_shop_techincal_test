from datetime import datetime

from sqlalchemy import BigInteger, Identity, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import NOME_MAX, Base, criado_em_coluna

EMAIL_MAX = 254


class Cliente(Base):
    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    nome: Mapped[str] = mapped_column(String(NOME_MAX), nullable=False)
    # Sempre gravado em minúsculas (normalizado no schema), então o índice
    # único comum já garante unicidade sem diferenciar maiúsculas.
    email: Mapped[str] = mapped_column(String(EMAIL_MAX), nullable=False, unique=True)
    criado_em: Mapped[datetime] = criado_em_coluna()
