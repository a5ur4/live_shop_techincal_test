"""adiciona editado_em em novidades

Revision ID: edeee003a6bb
Revises: 34f1fbd7f3f4
Create Date: 2026-11-06 07:30:40.065029

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "edeee003a6bb"
down_revision: str | Sequence[str] | None = "34f1fbd7f3f4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Nulo = nunca editada. Coluna nula sem default: ADD COLUMN não reescreve a tabela.
    op.add_column("novidades", sa.Column("editado_em", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("novidades", "editado_em")
