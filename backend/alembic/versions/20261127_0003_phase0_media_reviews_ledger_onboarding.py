"""Phase 0 stabilization: media visibility, review moderation constraint, pro onboarding, payment ledger & RLS.

Revision ID: 20261127_0003
Revises: 20261127_0002
Create Date: 2026-11-27 09:20:00+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.core.config import settings

revision: str = "20261127_0003"
down_revision: str | None = "20261127_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    # 1. Professional profile onboarding flag + private default visibility
    op.add_column(
        "professional_profiles",
        sa.Column("onboarding_completed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )

    # 2. Media asset visibility persistence (public vs private)
    op.add_column(
        "media_assets",
        sa.Column("visibility", sa.String(length=20), server_default="public", nullable=False),
    )
    op.create_check_constraint(
        "ck_media_assets_visibility",
        "media_assets",
        "visibility IN ('public', 'private')",
    )

    # 3. Expand review moderation status states and default pending
    op.drop_constraint("ck_reviews_moderation_status", "reviews", type_="check")
    op.create_check_constraint(
        "ck_reviews_moderation_status",
        "reviews",
        "moderation_status IN ('pending', 'approved', 'rejected', 'under_review', 'flagged', 'hidden')",
    )

    # 4. Append-only financial ledger table
    op.create_table(
        "payment_ledger_entries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("booking_id", sa.UUID(), nullable=False),
        sa.Column("payment_id", sa.UUID(), nullable=True),
        sa.Column("refund_id", sa.UUID(), nullable=True),
        sa.Column("entry_type", sa.String(length=40), nullable=False),
        sa.Column("direction", sa.String(length=10), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "entry_type IN ('payment_captured', 'platform_commission', 'professional_payable', 'payout_hold', 'payout_released', 'refund_issued')",
            name=op.f("ck_ledger_entry_type"),
        ),
        sa.CheckConstraint("direction IN ('credit', 'debit')", name=op.f("ck_ledger_direction")),
        sa.CheckConstraint("amount_minor > 0", name=op.f("ck_ledger_amount_positive")),
        sa.ForeignKeyConstraint(
            ["booking_id"],
            ["bookings.id"],
            name=op.f("fk_payment_ledger_entries_booking_id_bookings"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["payment_id"],
            ["payments.id"],
            name=op.f("fk_payment_ledger_entries_payment_id_payments"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["refund_id"],
            ["refunds.id"],
            name=op.f("fk_payment_ledger_entries_refund_id_refunds"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_payment_ledger_entries")),
    )
    op.create_index(
        op.f("ix_payment_ledger_entries_booking_id"),
        "payment_ledger_entries",
        ["booking_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_payment_ledger_entries_payment_id"),
        "payment_ledger_entries",
        ["payment_id"],
        unique=False,
    )

    if is_postgres:
        app_role = settings.APP_DB_USER.replace("'", "''")
        op.execute(f'GRANT SELECT, INSERT ON TABLE payment_ledger_entries TO "{app_role}"')
        op.execute("ALTER TABLE payment_ledger_entries ENABLE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE payment_ledger_entries FORCE ROW LEVEL SECURITY")
        op.execute(
            """
            CREATE POLICY ledger_participant_isolation ON payment_ledger_entries
            USING (
                current_setting('app.current_user_role', true) IN ('admin', 'system')
                OR EXISTS (
                    SELECT 1 FROM bookings b
                    LEFT JOIN professional_profiles pp ON pp.id = b.professional_id
                    WHERE b.id = payment_ledger_entries.booking_id
                      AND (
                          b.customer_id::text = NULLIF(current_setting('app.current_user_id', true), '')
                          OR pp.owner_user_id::text = NULLIF(current_setting('app.current_user_id', true), '')
                      )
                )
            )
            WITH CHECK (
                current_setting('app.current_user_role', true) IN ('admin', 'system')
                OR EXISTS (
                    SELECT 1 FROM bookings b
                    WHERE b.id = payment_ledger_entries.booking_id
                      AND b.customer_id::text = NULLIF(current_setting('app.current_user_id', true), '')
                )
            )
            """
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP POLICY IF EXISTS ledger_participant_isolation ON payment_ledger_entries")
        op.execute("ALTER TABLE payment_ledger_entries NO FORCE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE payment_ledger_entries DISABLE ROW LEVEL SECURITY")

    op.drop_index(op.f("ix_payment_ledger_entries_payment_id"), table_name="payment_ledger_entries")
    op.drop_index(op.f("ix_payment_ledger_entries_booking_id"), table_name="payment_ledger_entries")
    op.drop_table("payment_ledger_entries")

    op.drop_constraint("ck_reviews_moderation_status", "reviews", type_="check")
    op.create_check_constraint(
        "ck_reviews_moderation_status",
        "reviews",
        "moderation_status IN ('pending', 'approved', 'flagged', 'hidden')",
    )

    op.drop_constraint("ck_media_assets_visibility", "media_assets", type_="check")
    op.drop_column("media_assets", "visibility")
    op.drop_column("professional_profiles", "onboarding_completed")
