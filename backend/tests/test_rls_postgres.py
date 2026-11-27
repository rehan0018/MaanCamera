"""PostgreSQL FORCE ROW LEVEL SECURITY, non-owner role, and after_begin persistence tests."""

import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import select, text

from app.core.database import _apply_rls_context_on_begin, apply_rls_context
from app.core.security import hash_password
from app.modules.bookings.models import Booking
from app.modules.enquiries.models import Enquiry, EnquiryRecipient
from app.modules.identity.models import User
from app.modules.payments.models import Payment
from app.modules.professionals.models import Category, ProfessionalProfile
from app.modules.quotations.models import Quotation


class _FakeDialect:
    def __init__(self, name: str):
        self.name = name


class _FakeConnection:
    def __init__(self, dialect_name: str):
        self.dialect = _FakeDialect(dialect_name)
        self.calls: list[tuple[str, dict[str, str]]] = []

    def execute(self, statement, params=None):
        self.calls.append((str(statement), dict(params or {})))


class _FakeSession:
    def __init__(self, uid: str = "", role: str = ""):
        self.info = {"rls_user_id": uid, "rls_user_role": role}


@pytest.mark.asyncio
async def test_after_begin_hook_reapplies_rls_gucs_on_every_transaction(session_factory):
    # 1. Verify hook emits transaction-local set_config calls for Postgres dialect connections
    conn = _FakeConnection("postgresql")
    sess = _FakeSession(uid="user-123", role="customer")
    _apply_rls_context_on_begin(sess, None, conn)  # type: ignore[arg-type]
    assert len(conn.calls) == 1
    assert conn.calls[0][1] == {"uid": "user-123", "role": "customer"}

    # Verify unset session defaults to empty GUCs (fail-closed)
    conn_unset = _FakeConnection("postgresql")
    _apply_rls_context_on_begin(_FakeSession(), None, conn_unset)  # type: ignore[arg-type]
    assert conn_unset.calls[0][1] == {"uid": "", "role": ""}

    # 2. Live PostgreSQL verification when TEST_DATABASE_URL points to Postgres
    async with session_factory() as check_sess:
        is_postgres = bool(check_sess.bind and check_sess.bind.dialect.name == "postgresql")
    if not is_postgres:
        return

    cust_a_id = uuid.uuid4()
    cust_b_id = uuid.uuid4()
    pro_user_id = uuid.uuid4()
    pro_id = uuid.uuid4()
    cat_id = uuid.uuid4()
    enq_a_id = uuid.uuid4()
    enq_b_id = uuid.uuid4()
    quot_a_id = uuid.uuid4()
    quot_b_id = uuid.uuid4()
    bk_a_id = uuid.uuid4()
    bk_b_id = uuid.uuid4()

    async with session_factory() as admin_s:
        role_row = (
            await admin_s.execute(
                text(
                    "SELECT current_user, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user"
                )
            )
        ).one()
        assert role_row[1] is False, "Runtime test DB role must not be a superuser"
        assert role_row[2] is False, "Runtime test DB role must not have BYPASSRLS"

        await apply_rls_context(admin_s, role="system")
        pw = hash_password("RlsTestPass@2026!")
        admin_s.add_all(
            [
                User(id=cust_a_id, email=f"rls-a-{cust_a_id.hex[:6]}@example.com", password_hash=pw, full_name="Cust A", role="customer"),
                User(id=cust_b_id, email=f"rls-b-{cust_b_id.hex[:6]}@example.com", password_hash=pw, full_name="Cust B", role="customer"),
                User(id=pro_user_id, email=f"rls-p-{pro_user_id.hex[:6]}@example.com", password_hash=pw, full_name="Pro One", role="professional"),
                Category(id=cat_id, name=f"Cat {cat_id.hex[:6]}", slug=f"cat-{cat_id.hex[:8]}"),
            ]
        )
        await admin_s.flush()
        admin_s.add(
            ProfessionalProfile(
                id=pro_id,
                owner_user_id=pro_user_id,
                display_name="RLS Pro",
                slug=f"rls-pro-{pro_id.hex[:8]}",
                base_city="Pune",
                state="Maharashtra",
            )
        )
        await admin_s.flush()
        admin_s.add_all(
            [
                Enquiry(id=enq_a_id, customer_id=cust_a_id, category_id=cat_id, title="Enq A", description="Shoot A", location="Pune", city="Pune"),
                Enquiry(id=enq_b_id, customer_id=cust_b_id, category_id=cat_id, title="Enq B", description="Shoot B", location="Pune", city="Pune"),
            ]
        )
        await admin_s.flush()
        admin_s.add_all(
            [
                EnquiryRecipient(enquiry_id=enq_a_id, professional_id=pro_id, recipient_status="sent"),
                EnquiryRecipient(enquiry_id=enq_b_id, professional_id=pro_id, recipient_status="sent"),
                Quotation(id=quot_a_id, enquiry_id=enq_a_id, professional_id=pro_id, total_amount_minor=100000, advance_amount_minor=25000, scope_of_work="Scope A", valid_until=datetime.now(UTC) + timedelta(days=5)),
                Quotation(id=quot_b_id, enquiry_id=enq_b_id, professional_id=pro_id, total_amount_minor=200000, advance_amount_minor=50000, scope_of_work="Scope B", valid_until=datetime.now(UTC) + timedelta(days=5)),
            ]
        )
        await admin_s.flush()
        admin_s.add_all(
            [
                Booking(id=bk_a_id, enquiry_id=enq_a_id, quotation_id=quot_a_id, customer_id=cust_a_id, professional_id=pro_id, shoot_date=date.today(), location="Pune", agreed_amount_minor=100000, booking_status="pending_payment"),
                Booking(id=bk_b_id, enquiry_id=enq_b_id, quotation_id=quot_b_id, customer_id=cust_b_id, professional_id=pro_id, shoot_date=date.today(), location="Pune", agreed_amount_minor=200000, booking_status="pending_payment"),
            ]
        )
        await admin_s.flush()
        admin_s.add_all(
            [
                Payment(booking_id=bk_a_id, provider="mock", provider_order_id=f"ord_a_{bk_a_id.hex[:8]}", amount_minor=25000),
                Payment(booking_id=bk_b_id, provider="mock", provider_order_id=f"ord_b_{bk_b_id.hex[:8]}", amount_minor=50000),
            ]
        )
        await admin_s.commit()

    # Unauthenticated / unset context MUST return 0 rows on all RLS-protected tables
    async with session_factory() as anon_s:
        assert list((await anon_s.execute(select(Booking))).scalars().all()) == []
        assert list((await anon_s.execute(select(Enquiry))).scalars().all()) == []
        assert list((await anon_s.execute(select(Payment))).scalars().all()) == []
        assert list((await anon_s.execute(select(Quotation))).scalars().all()) == []

    # Customer A context sees ONLY Customer A rows before AND after a mid-request commit()
    async with session_factory() as cust_a_s:
        await apply_rls_context(cust_a_s, user_id=str(cust_a_id), role="customer")

        bks_before = list((await cust_a_s.execute(select(Booking))).scalars().all())
        assert [b.id for b in bks_before] == [bk_a_id]

        # Mid-request commit starts a fresh Postgres transaction; after_begin must preserve Customer A GUC
        await cust_a_s.commit()

        bks_after = list((await cust_a_s.execute(select(Booking))).scalars().all())
        enqs_after = list((await cust_a_s.execute(select(Enquiry))).scalars().all())
        pays_after = list((await cust_a_s.execute(select(Payment))).scalars().all())
        quots_after = list((await cust_a_s.execute(select(Quotation))).scalars().all())

        assert [b.id for b in bks_after] == [bk_a_id]
        assert [e.id for e in enqs_after] == [enq_a_id]
        assert [p.booking_id for p in pays_after] == [bk_a_id]
        assert [q.id for q in quots_after] == [quot_a_id]
