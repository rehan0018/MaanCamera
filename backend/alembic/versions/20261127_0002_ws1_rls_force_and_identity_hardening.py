"""WS1 security foundations: FORCE RLS, non-owner app DB role, identity tokens, lockout & DPDP consents.

Revision ID: 20261127_0002
Revises: 20261126_0001
Create Date: 2026-11-27 08:40:00+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.core.config import settings

revision: str = "20261127_0002"
down_revision: str | None = "20261126_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    # 1. Identity hardening & DPDP consent columns on users
    op.add_column(
        "users",
        sa.Column("failed_login_attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )
    op.add_column("users", sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("totp_secret", sa.String(length=64), nullable=True))
    op.add_column(
        "users",
        sa.Column("totp_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column("users", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("terms_accepted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("terms_version", sa.String(length=32), nullable=True))
    op.add_column("users", sa.Column("privacy_accepted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("privacy_version", sa.String(length=32), nullable=True))

    # 2. Single-use verification, OTP, and password reset tokens
    op.create_table(
        "identity_tokens",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("token_type", sa.String(length=30), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("target", sa.String(length=255), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "token_type IN ('email_verify', 'phone_otp', 'password_reset')",
            name=op.f("ck_identity_tokens_type"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_identity_tokens_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_identity_tokens")),
    )
    op.create_index(op.f("ix_identity_tokens_token_hash"), "identity_tokens", ["token_hash"], unique=False)
    op.create_index(op.f("ix_identity_tokens_user_id"), "identity_tokens", ["user_id"], unique=False)

    # 3. DPDP Consent Records
    op.create_table(
        "consent_records",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("consent_type", sa.String(length=50), nullable=False),
        sa.Column("policy_version", sa.String(length=32), nullable=False),
        sa.Column("granted", sa.Boolean(), nullable=False),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "consent_type IN ('terms_of_service', 'privacy_policy', 'marketing')",
            name=op.f("ck_consent_records_type"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_consent_records_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_consent_records")),
    )
    op.create_index(op.f("ix_consent_records_user_id"), "consent_records", ["user_id"], unique=False)

    if is_postgres:
        # 4. Non-owner runtime PostgreSQL role (does NOT bypass FORCE ROW LEVEL SECURITY)
        app_role = settings.APP_DB_USER.replace("'", "''")
        app_pass = settings.APP_DB_PASSWORD.replace("'", "''")
        op.execute(
            f"""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{app_role}') THEN
                    EXECUTE format(
                        'CREATE ROLE %I LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS NOREPLICATION',
                        '{app_role}',
                        '{app_pass}'
                    );
                ELSE
                    EXECUTE format(
                        'ALTER ROLE %I WITH LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS NOREPLICATION',
                        '{app_role}',
                        '{app_pass}'
                    );
                END IF;
            END $$;
            """
        )
        op.execute(f'GRANT USAGE ON SCHEMA public TO "{app_role}"')
        op.execute(f'GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO "{app_role}"')
        op.execute(f'GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO "{app_role}"')
        op.execute(f'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "{app_role}"')
        op.execute(f'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO "{app_role}"')
        op.execute(f'REVOKE INSERT, UPDATE, DELETE ON TABLE alembic_version FROM "{app_role}"')

        # 5. Fail-closed FORCE ROW LEVEL SECURITY (zero IS NULL bypass; enforces non-owner isolation)
        op.execute("DROP POLICY IF EXISTS bookings_participant_isolation ON bookings")
        op.execute("DROP POLICY IF EXISTS enquiries_participant_isolation ON enquiries")
        op.execute("DROP POLICY IF EXISTS payments_participant_isolation ON payments")

        op.execute("ALTER TABLE bookings ENABLE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE bookings FORCE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE enquiries ENABLE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE enquiries FORCE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE payments ENABLE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE payments FORCE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE quotations ENABLE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE quotations FORCE ROW LEVEL SECURITY")

        op.execute(
            """
            CREATE POLICY bookings_participant_isolation ON bookings
            USING (
                current_setting('app.current_user_role', true) IN ('admin', 'system')
                OR customer_id::text = NULLIF(current_setting('app.current_user_id', true), '')
                OR professional_id IN (
                    SELECT pp.id FROM professional_profiles pp
                    WHERE pp.owner_user_id::text = NULLIF(current_setting('app.current_user_id', true), '')
                )
            )
            WITH CHECK (
                current_setting('app.current_user_role', true) IN ('admin', 'system')
                OR customer_id::text = NULLIF(current_setting('app.current_user_id', true), '')
                OR professional_id IN (
                    SELECT pp.id FROM professional_profiles pp
                    WHERE pp.owner_user_id::text = NULLIF(current_setting('app.current_user_id', true), '')
                )
            )
            """
        )

        op.execute(
            """
            CREATE POLICY enquiries_participant_isolation ON enquiries
            USING (
                current_setting('app.current_user_role', true) IN ('admin', 'system')
                OR customer_id::text = NULLIF(current_setting('app.current_user_id', true), '')
                OR EXISTS (
                    SELECT 1 FROM enquiry_recipients er
                    JOIN professional_profiles pp ON pp.id = er.professional_id
                    WHERE er.enquiry_id = enquiries.id
                      AND pp.owner_user_id::text = NULLIF(current_setting('app.current_user_id', true), '')
                )
            )
            WITH CHECK (
                current_setting('app.current_user_role', true) IN ('admin', 'system')
                OR customer_id::text = NULLIF(current_setting('app.current_user_id', true), '')
            )
            """
        )

        op.execute(
            """
            CREATE POLICY payments_participant_isolation ON payments
            USING (
                current_setting('app.current_user_role', true) IN ('admin', 'system')
                OR EXISTS (
                    SELECT 1 FROM bookings b
                    LEFT JOIN professional_profiles pp ON pp.id = b.professional_id
                    WHERE b.id = payments.booking_id
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
                    WHERE b.id = payments.booking_id
                      AND b.customer_id::text = NULLIF(current_setting('app.current_user_id', true), '')
                )
            )
            """
        )

        op.execute(
            """
            CREATE POLICY quotations_participant_isolation ON quotations
            USING (
                current_setting('app.current_user_role', true) IN ('admin', 'system')
                OR professional_id IN (
                    SELECT pp.id FROM professional_profiles pp
                    WHERE pp.owner_user_id::text = NULLIF(current_setting('app.current_user_id', true), '')
                )
                OR enquiry_id IN (
                    SELECT e.id FROM enquiries e
                    WHERE e.customer_id::text = NULLIF(current_setting('app.current_user_id', true), '')
                )
            )
            WITH CHECK (
                current_setting('app.current_user_role', true) IN ('admin', 'system')
                OR professional_id IN (
                    SELECT pp.id FROM professional_profiles pp
                    WHERE pp.owner_user_id::text = NULLIF(current_setting('app.current_user_id', true), '')
                )
                OR enquiry_id IN (
                    SELECT e.id FROM enquiries e
                    WHERE e.customer_id::text = NULLIF(current_setting('app.current_user_id', true), '')
                )
            )
            """
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP POLICY IF EXISTS quotations_participant_isolation ON quotations")
        op.execute("ALTER TABLE quotations NO FORCE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE quotations DISABLE ROW LEVEL SECURITY")

        op.execute("DROP POLICY IF EXISTS payments_participant_isolation ON payments")
        op.execute("DROP POLICY IF EXISTS enquiries_participant_isolation ON enquiries")
        op.execute("DROP POLICY IF EXISTS bookings_participant_isolation ON bookings")
        op.execute("ALTER TABLE payments NO FORCE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE enquiries NO FORCE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE bookings NO FORCE ROW LEVEL SECURITY")

        op.execute(
            """
            CREATE POLICY bookings_participant_isolation ON bookings
            USING (
                NULLIF(current_setting('app.current_user_id', true), '') IS NULL
                OR current_setting('app.current_user_role', true) IN ('admin', 'system')
                OR customer_id::text = current_setting('app.current_user_id', true)
                OR professional_id IN (
                    SELECT id FROM professional_profiles
                    WHERE owner_user_id::text = current_setting('app.current_user_id', true)
                )
            )
            """
        )
        op.execute(
            """
            CREATE POLICY enquiries_participant_isolation ON enquiries
            USING (
                NULLIF(current_setting('app.current_user_id', true), '') IS NULL
                OR current_setting('app.current_user_role', true) IN ('admin', 'system')
                OR customer_id::text = current_setting('app.current_user_id', true)
                OR id IN (
                    SELECT er.enquiry_id FROM enquiry_recipients er
                    JOIN professional_profiles pp ON pp.id = er.professional_id
                    WHERE pp.owner_user_id::text = current_setting('app.current_user_id', true)
                )
            )
            """
        )
        op.execute(
            """
            CREATE POLICY payments_participant_isolation ON payments
            USING (
                NULLIF(current_setting('app.current_user_id', true), '') IS NULL
                OR current_setting('app.current_user_role', true) IN ('admin', 'system')
                OR booking_id IN (
                    SELECT b.id FROM bookings b
                    WHERE b.customer_id::text = current_setting('app.current_user_id', true)
                       OR b.professional_id IN (
                           SELECT pp.id FROM professional_profiles pp
                           WHERE pp.owner_user_id::text = current_setting('app.current_user_id', true)
                       )
                )
            )
            """
        )

    op.drop_index(op.f("ix_consent_records_user_id"), table_name="consent_records")
    op.drop_table("consent_records")
    op.drop_index(op.f("ix_identity_tokens_user_id"), table_name="identity_tokens")
    op.drop_index(op.f("ix_identity_tokens_token_hash"), table_name="identity_tokens")
    op.drop_table("identity_tokens")

    op.drop_column("users", "privacy_version")
    op.drop_column("users", "privacy_accepted_at")
    op.drop_column("users", "terms_version")
    op.drop_column("users", "terms_accepted_at")
    op.drop_column("users", "deleted_at")
    op.drop_column("users", "totp_enabled")
    op.drop_column("users", "totp_secret")
    op.drop_column("users", "locked_until")
    op.drop_column("users", "failed_login_attempts")
