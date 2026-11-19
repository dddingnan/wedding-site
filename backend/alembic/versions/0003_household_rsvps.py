"""household-level RSVPs: drop per-person guests; add capacity, gift zodiacs, main event

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-19 00:00:00

Invitations are answered per household (party size + meal/zodiac counts) instead of per
named guest, so the guests table and per-guest rsvps go away. Any existing guest-level
RSVP data is dropped (there was none in production when this was written).
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("events") as batch:
        batch.add_column(sa.Column("capacity", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("gift_zodiacs", sa.JSON(), server_default="[]", nullable=False))

    with op.batch_alter_table("households") as batch:
        batch.add_column(sa.Column("contact_first_name", sa.String(length=100), nullable=True))
        batch.add_column(sa.Column("contact_last_name", sa.String(length=100), nullable=True))
        batch.add_column(sa.Column("primary_event_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_households_primary_event_id_events",
            "events",
            ["primary_event_id"],
            ["id"],
            ondelete="RESTRICT",
        )

    # Existing invitations: main event = their earliest invited event.
    op.execute(
        """
        UPDATE households SET primary_event_id = (
            SELECT he.event_id FROM household_events he
            JOIN events e ON e.id = he.event_id
            WHERE he.household_id = households.id
            ORDER BY e.starts_at LIMIT 1
        )
        """
    )

    op.drop_table("rsvps")
    op.drop_table("guests")
    op.create_table(
        "rsvps",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("household_id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("attending", sa.Boolean(), nullable=False),
        sa.Column("party_size", sa.Integer(), nullable=False),
        sa.Column("meals", sa.JSON(), nullable=False),
        sa.Column("zodiacs", sa.JSON(), nullable=False),
        sa.Column("dietary", sa.String(length=500), nullable=True),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("household_id", "event_id"),
    )


def downgrade() -> None:
    # Household-level answers can't be split back into named guests; they're dropped.
    op.drop_table("rsvps")
    op.create_table(
        "guests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("household_id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("is_plus_one", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "rsvps",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("guest_id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("attending", sa.Boolean(), nullable=False),
        sa.Column("meal", sa.String(length=50), nullable=True),
        sa.Column("dietary", sa.String(length=500), nullable=True),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["guest_id"], ["guests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("guest_id", "event_id"),
    )
    with op.batch_alter_table("households") as batch:
        batch.drop_constraint("fk_households_primary_event_id_events", type_="foreignkey")
        batch.drop_column("primary_event_id")
        batch.drop_column("contact_last_name")
        batch.drop_column("contact_first_name")
    with op.batch_alter_table("events") as batch:
        batch.drop_column("gift_zodiacs")
        batch.drop_column("capacity")
