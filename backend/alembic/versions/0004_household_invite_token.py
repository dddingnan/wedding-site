"""household invite token: long secret for the invitation link / QR code

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-20 00:00:00

Existing households get a fresh random token; their short invite_code is unchanged.
"""

import secrets
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Same as app.services.invite_codes.TOKEN_BYTES (copied so this file never changes
# if the app code does).
TOKEN_BYTES = 16


def upgrade() -> None:
    with op.batch_alter_table("households") as batch:
        batch.add_column(sa.Column("invite_token", sa.String(length=64), nullable=True))

    conn = op.get_bind()
    households = sa.table("households", sa.column("id"), sa.column("invite_token"))
    for (household_id,) in conn.execute(sa.select(households.c.id)):
        conn.execute(
            households.update()
            .where(households.c.id == household_id)
            .values(invite_token=secrets.token_urlsafe(TOKEN_BYTES))
        )

    with op.batch_alter_table("households") as batch:
        batch.alter_column("invite_token", existing_type=sa.String(length=64), nullable=False)
        batch.create_index(op.f("ix_households_invite_token"), ["invite_token"], unique=True)


def downgrade() -> None:
    with op.batch_alter_table("households") as batch:
        batch.drop_index(op.f("ix_households_invite_token"))
        batch.drop_column("invite_token")
