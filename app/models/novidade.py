from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Identity, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, criado_em_coluna
from app.models.loja import Loja

TEXTO_MAX = 500


class Novidade(Base):
    __tablename__ = "novidades"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    loja_id: Mapped[int] = mapped_column(ForeignKey("lojas.id", ondelete="CASCADE"), nullable=False)
    texto: Mapped[str] = mapped_column(String(TEXTO_MAX), nullable=False)
    preco: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    criado_em: Mapped[datetime] = criado_em_coluna()

    loja: Mapped[Loja] = relationship(lazy="raise")

    __table_args__ = (
        CheckConstraint("char_length(texto) BETWEEN 1 AND 500", name="texto_tamanho"),
        CheckConstraint("preco IS NULL OR preco > 0", name="preco_positivo"),
    )


# Índice do feed: para cada loja seguida, as novidades já saem ordenadas da
# mais recente para a mais antiga (desempate por id). Ver docs/adr/0002.
Index(
    "ix_novidades_loja_feed",
    Novidade.loja_id,
    Novidade.criado_em.desc(),
    Novidade.id.desc(),
)
