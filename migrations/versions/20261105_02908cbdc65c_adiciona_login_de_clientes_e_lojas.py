"""adiciona login de clientes e lojas

Linhas já existentes recebem senha bloqueada ("!", que não é hash válido, logo nenhum
login funciona) e, no caso de lojas, um e-mail provisório único. Redefina com o seed
(`python -m app.seed --reset`) ou atualize manualmente.

Revision ID: 02908cbdc65c
Revises: 7342f345a6ae
Create Date: 2026-11-05 23:34:07.161769

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "02908cbdc65c"
down_revision: str | Sequence[str] | None = "7342f345a6ae"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("clientes", sa.Column("senha_hash", sa.String(length=255), nullable=True))
    op.add_column("lojas", sa.Column("email", sa.String(length=254), nullable=True))
    op.add_column("lojas", sa.Column("senha_hash", sa.String(length=255), nullable=True))

    op.execute("UPDATE clientes SET senha_hash = '!' WHERE senha_hash IS NULL")
    op.execute(
        "UPDATE lojas SET email = 'loja-' || id || '@sem-email.invalid', senha_hash = '!' "
        "WHERE email IS NULL"
    )

    op.alter_column("clientes", "senha_hash", nullable=False)
    op.alter_column("lojas", "email", nullable=False)
    op.alter_column("lojas", "senha_hash", nullable=False)
    op.create_unique_constraint(op.f("uq_lojas_email"), "lojas", ["email"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(op.f("uq_lojas_email"), "lojas", type_="unique")
    op.drop_column("lojas", "senha_hash")
    op.drop_column("lojas", "email")
    op.drop_column("clientes", "senha_hash")
