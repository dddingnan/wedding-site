"""staff users (admin/manager), wedding-day check-ins and gifts

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-20 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("username", sa.String(length=50), nullable=True),
        sa.Column("pin_hash", sa.String(length=200), nullable=True),
        sa.Column("google_email", sa.String(length=320), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("failed_logins", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("google_email"),
    )
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)

    op.create_table(
        "check_ins",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("household_id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("arrived", sa.Integer(), nullable=False),
        sa.Column("checked_in_by_id", sa.Integer(), nullable=True),
        sa.Column(
            "checked_in_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["checked_in_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("household_id", "event_id"),
    )

    op.create_table(
        "gifts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("household_id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("zodiac_gifts", sa.JSON(), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("recorded_by_id", sa.Integer(), nullable=True),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recorded_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("household_id", "event_id"),
    )


def downgrade() -> None:
    op.drop_table("gifts")
    op.drop_table("check_ins")
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_table("users")
