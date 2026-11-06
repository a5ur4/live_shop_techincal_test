from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    MetaData,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Nomes previsíveis para constraints: facilitam migrations e o tratamento de
# IntegrityError (ver services, que identificam a violação pelo nome).
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

TEXTO_MAX = 500
NOME_MAX = 120
EMAIL_MAX = 254


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def _criado_em() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Loja(Base):
    __tablename__ = "lojas"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    nome: Mapped[str] = mapped_column(String(NOME_MAX), nullable=False)
    criado_em: Mapped[datetime] = _criado_em()


class Cliente(Base):
    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    nome: Mapped[str] = mapped_column(String(NOME_MAX), nullable=False)
    # Sempre gravado em minúsculas (normalizado no schema), então o índice
    # único comum já garante unicidade sem diferenciar maiúsculas.
    email: Mapped[str] = mapped_column(String(EMAIL_MAX), nullable=False, unique=True)
    criado_em: Mapped[datetime] = _criado_em()


class Seguidor(Base):
    """Relação N:N cliente → loja. A PK composta impede seguir a mesma loja duas vezes."""

    __tablename__ = "seguidores"

    cliente_id: Mapped[int] = mapped_column(
        ForeignKey("clientes.id", ondelete="CASCADE"), primary_key=True
    )
    loja_id: Mapped[int] = mapped_column(
        ForeignKey("lojas.id", ondelete="CASCADE"), primary_key=True
    )
    criado_em: Mapped[datetime] = _criado_em()

    # A PK (cliente_id, loja_id) já atende "lojas que o cliente segue".
    # Este índice atende o caminho inverso: "seguidores de uma loja".
    __table_args__ = (Index("ix_seguidores_loja_id", "loja_id"),)


class Novidade(Base):
    __tablename__ = "novidades"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    loja_id: Mapped[int] = mapped_column(ForeignKey("lojas.id", ondelete="CASCADE"), nullable=False)
    texto: Mapped[str] = mapped_column(String(TEXTO_MAX), nullable=False)
    preco: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    criado_em: Mapped[datetime] = _criado_em()

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
