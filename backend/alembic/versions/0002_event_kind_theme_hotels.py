"""event kind, theme and hotel guide; rename 'second' event to 'taiwan'

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-19 00:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("events") as batch:
        batch.add_column(
            sa.Column("kind", sa.String(length=16), server_default="upcoming", nullable=False)
        )
        batch.add_column(sa.Column("theme", sa.String(length=16), nullable=True))

    op.create_table(
        "event_hotels",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("address", sa.String(length=500), nullable=True),
        sa.Column("map_url", sa.String(length=500), nullable=True),
        sa.Column("booking_url", sa.String(length=500), nullable=True),
        sa.Column("booking_code", sa.String(length=100), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_event_hotels_event_id"), "event_hotels", ["event_id"])

    # The placeholder "second" event is now known to be the Taiwan ceremony. Rename in place
    # so existing invitations/RSVPs keep pointing at it (seed_events upserts by slug).
    op.execute("UPDATE events SET slug = 'taiwan' WHERE slug = 'second'")


def downgrade() -> None:
    op.execute("UPDATE events SET slug = 'second' WHERE slug = 'taiwan'")
    op.drop_index(op.f("ix_event_hotels_event_id"), table_name="event_hotels")
    op.drop_table("event_hotels")
    with op.batch_alter_table("events") as batch:
        batch.drop_column("theme")
        batch.drop_column("kind")
