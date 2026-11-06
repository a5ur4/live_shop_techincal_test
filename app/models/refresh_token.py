import uuid
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Identity, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, criado_em_coluna


class RefreshToken(Base):
    """Refresh token opaco, guardado só como hash (ver docs/adr/0007).

    Cada uso gera um novo token na mesma `familia` e revoga o anterior (rotação). Se um
    token já revogado for apresentado de novo, alguém o copiou: a família inteira é revogada.
    """

    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    # Conta de cliente ou de loja: sem FK porque aponta para tabelas diferentes.
    tipo: Mapped[str] = mapped_column(String(10), nullable=False)
    conta_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # SHA-256 em hex: o token tem 256 bits aleatórios, então não precisa de hash lento.
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    familia: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revogado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    criado_em: Mapped[datetime] = criado_em_coluna()

    __table_args__ = (
        CheckConstraint("tipo IN ('cliente', 'loja')", name="tipo_valido"),
        Index("ix_refresh_tokens_familia", "familia"),
        # Revogar todos os tokens de uma conta (troca de senha).
        Index("ix_refresh_tokens_conta", "tipo", "conta_id"),
    )
