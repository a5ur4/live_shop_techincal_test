from datetime import datetime

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, criado_em_coluna


class Seguidor(Base):
    """Relação N:N cliente → loja. A PK composta impede seguir a mesma loja duas vezes."""

    __tablename__ = "seguidores"

    cliente_id: Mapped[int] = mapped_column(
        ForeignKey("clientes.id", ondelete="CASCADE"), primary_key=True
    )
    loja_id: Mapped[int] = mapped_column(
        ForeignKey("lojas.id", ondelete="CASCADE"), primary_key=True
    )
    criado_em: Mapped[datetime] = criado_em_coluna()

    # A PK (cliente_id, loja_id) já atende "lojas que o cliente segue".
    # Este índice atende o caminho inverso: "seguidores de uma loja".
    __table_args__ = (Index("ix_seguidores_loja_id", "loja_id"),)
