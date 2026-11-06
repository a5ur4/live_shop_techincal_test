from datetime import datetime

from sqlalchemy import BigInteger, Identity, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import NOME_MAX, Base, criado_em_coluna


class Loja(Base):
    __tablename__ = "lojas"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    nome: Mapped[str] = mapped_column(String(NOME_MAX), nullable=False)
    criado_em: Mapped[datetime] = criado_em_coluna()
