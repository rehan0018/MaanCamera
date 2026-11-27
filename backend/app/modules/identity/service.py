"""Service for authentication, account lockout, TOTP 2FA, verification tokens, sessions, and DPDP compliance."""

import contextlib
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import settings
from app.core.database import register_after_commit
from app.core.exceptions import (
    BusinessRuleViolationException,
    ConflictException,
    ForbiddenException,
    LockedException,
    NotFoundException,
    UnauthorizedException,
)
from app.core.security import (
    build_totp_uri,
    calculate_session_expiry,
    generate_one_time_token,
    generate_otp_code,
    generate_session_token,
    generate_totp_secret,
    hash_one_time_token,
    hash_password,
    hash_session_token,
    verify_otp_code,
    verify_password,
    verify_totp_code,
)
from app.integrations.notifications.mailer import send_email_notification, send_sms_otp
from app.modules.bookings.models import Booking
from app.modules.enquiries.models import Enquiry
from app.modules.identity.models import ConsentRecord, IdentityToken, User, UserSession
from app.modules.identity.schemas import UserLoginRequest, UserRegisterRequest
from app.modules.quotations.models import Quotation
from app.modules.reviews.models import Review

MAX_OTP_ATTEMPTS = 5


def _ensure_utc(dt: datetime) -> datetime:
    """Normalize naive datetimes returned by SQLite test drivers to UTC-aware."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def _schedule_email(
    db: AsyncSession, recipient: str, subject: str, body: str, event_type: str
) -> None:
    async def _send() -> None:
        with contextlib.suppress(Exception):
            await send_email_notification(recipient, subject, body, event_type)

    register_after_commit(db, _send)


def _schedule_sms_otp(db: AsyncSession, phone: str, code: str, purpose: str) -> None:
    async def _send() -> None:
        with contextlib.suppress(Exception):
            await send_sms_otp(phone, code, purpose)

    register_after_commit(db, _send)


class IdentityService:
    @staticmethod
    async def register(
        db: AsyncSession,
        req: UserRegisterRequest,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> User:
        normalized_email = req.email.lower()
        stmt = select(User).where(User.email == normalized_email)
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise ConflictException("An account with this email address already exists.")

        if req.phone:
            phone_stmt = select(User).where(User.phone == req.phone.strip())
            if (await db.execute(phone_stmt)).scalar_one_or_none():
                raise ConflictException("An account with this phone number already exists.")

        now = datetime.now(UTC)
        terms_ver = req.terms_version or settings.TERMS_VERSION
        privacy_ver = req.privacy_version or settings.PRIVACY_VERSION

        user = User(
            email=normalized_email,
            phone=req.phone.strip() if req.phone else None,
            password_hash=hash_password(req.password),
            full_name=req.full_name,
            role=req.role or "customer",
            status="active",
            terms_accepted_at=now,
            terms_version=terms_ver,
            privacy_accepted_at=now,
            privacy_version=privacy_ver,
        )
        db.add(user)
        await db.flush()

        db.add(
            ConsentRecord(
                user_id=user.id,
                consent_type="terms_of_service",
                policy_version=terms_ver,
                granted=True,
                ip_address=ip_address,
                user_agent=user_agent,
                recorded_at=now,
            )
        )
        db.add(
            ConsentRecord(
                user_id=user.id,
                consent_type="privacy_policy",
                policy_version=privacy_ver,
                granted=True,
                ip_address=ip_address,
                user_agent=user_agent,
                recorded_at=now,
            )
        )
        if req.marketing_opt_in:
            db.add(
                ConsentRecord(
                    user_id=user.id,
                    consent_type="marketing",
                    policy_version=privacy_ver,
                    granted=True,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    recorded_at=now,
                )
            )

        await IdentityService._issue_email_verification(db, user)
        await db.flush()
        return user

    @staticmethod
    async def _record_failed_login(db: AsyncSession, user_id: uuid.UUID) -> None:
        """Persist failed login count and exponential lockout outside the failing request txn."""
        if not db.bind:
            return
        if db.in_transaction():
            await db.rollback()
        iso_factory = async_sessionmaker(bind=db.bind, class_=AsyncSession, expire_on_commit=False)
        async with iso_factory() as iso_db:
            user = await iso_db.get(User, user_id)
            if not user:
                return
            attempts = (user.failed_login_attempts or 0) + 1
            user.failed_login_attempts = attempts
            if attempts >= settings.AUTH_LOCKOUT_MAX_ATTEMPTS:
                exponent = attempts - settings.AUTH_LOCKOUT_MAX_ATTEMPTS
                lock_minutes = min(60, settings.AUTH_LOCKOUT_BASE_MINUTES * (2**exponent))
                user.locked_until = datetime.now(UTC) + timedelta(minutes=lock_minutes)
            await iso_db.commit()

    @staticmethod
    async def authenticate(
        db: AsyncSession,
        req: UserLoginRequest,
        user_agent: str | None = None,
        ip: str | None = None,
    ) -> tuple[User, str]:
        stmt = select(User).where(User.email == req.email.lower())
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        now = datetime.now(UTC)
        if user and user.locked_until and _ensure_utc(user.locked_until) > now:
            raise LockedException("Account temporarily locked due to repeated failed login attempts.")

        if not user or not user.password_hash or not verify_password(req.password, user.password_hash):
            if user:
                await IdentityService._record_failed_login(db, user.id)
            raise UnauthorizedException("Invalid email address or password.")

        if user.status != "active":
            raise UnauthorizedException("Your account is currently inactive or suspended.")

        if (user.totp_enabled or (user.role == "admin" and settings.REQUIRE_ADMIN_TOTP)) and (
            not user.totp_secret
            or not req.totp_code
            or not verify_totp_code(user.totp_secret, req.totp_code)
        ):
            await IdentityService._record_failed_login(db, user.id)
            raise UnauthorizedException("Valid two-factor authentication code is required.")

        # Reset lockout counters on successful authentication
        if user.failed_login_attempts or user.locked_until:
            user.failed_login_attempts = 0
            user.locked_until = None

        plain_token = generate_session_token()
        hashed_token = hash_session_token(plain_token)
        session = UserSession(
            user_id=user.id,
            session_token_hash=hashed_token,
            user_agent=user_agent,
            ip_address=ip,
            expires_at=calculate_session_expiry(),
        )
        db.add(session)
        await db.flush()

        return user, plain_token

    @staticmethod
    async def get_session_and_user(db: AsyncSession, token: str) -> tuple[UserSession, User] | None:
        hashed_token = hash_session_token(token)
        stmt = select(UserSession).where(
            UserSession.session_token_hash == hashed_token,
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > datetime.now(UTC),
        )
        res = await db.execute(stmt)
        session = res.scalar_one_or_none()
        if not session:
            return None

        session.last_used_at = datetime.now(UTC)
        user = await db.get(User, session.user_id)
        if not user or user.status != "active":
            return None
        await db.flush()
        return session, user

    @staticmethod
    async def get_user_by_session_token(db: AsyncSession, token: str) -> User | None:
        pair = await IdentityService.get_session_and_user(db, token)
        return pair[1] if pair else None

    @staticmethod
    async def refresh_session(db: AsyncSession, token: str) -> tuple[User, str]:
        pair = await IdentityService.get_session_and_user(db, token)
        if not pair:
            raise UnauthorizedException("Session is invalid or has expired.")
        session, user = pair
        new_plain = generate_session_token()
        session.session_token_hash = hash_session_token(new_plain)
        session.expires_at = calculate_session_expiry()
        session.last_used_at = datetime.now(UTC)
        await db.flush()
        return user, new_plain

    @staticmethod
    async def revoke_session(db: AsyncSession, token: str) -> bool:
        hashed_token = hash_session_token(token)
        stmt = (
            update(UserSession)
            .where(UserSession.session_token_hash == hashed_token, UserSession.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
        await db.execute(stmt)
        await db.flush()
        return True

    @staticmethod
    async def list_user_sessions(db: AsyncSession, user_id: uuid.UUID) -> list[UserSession]:
        stmt = (
            select(UserSession)
            .where(UserSession.user_id == user_id)
            .order_by(UserSession.last_used_at.desc())
        )
        return list((await db.execute(stmt)).scalars().all())

    @staticmethod
    async def revoke_user_session_by_id(
        db: AsyncSession, user_id: uuid.UUID, session_id: uuid.UUID
    ) -> bool:
        session = await db.get(UserSession, session_id)
        if not session:
            raise NotFoundException("UserSession", session_id)
        if session.user_id != user_id:
            raise ForbiddenException("You cannot revoke another user's session.")
        if not session.revoked_at:
            session.revoked_at = datetime.now(UTC)
            await db.flush()
        return True

    @staticmethod
    async def _issue_email_verification(db: AsyncSession, user: User) -> str | None:
        if not user.email:
            return None
        plain, token_hash = generate_one_time_token()
        db.add(
            IdentityToken(
                user_id=user.id,
                token_type="email_verify",
                token_hash=token_hash,
                target=user.email,
                expires_at=datetime.now(UTC) + timedelta(hours=24),
            )
        )
        verify_url = f"{settings.FRONTEND_URL.rstrip('/')}/verify-email?token={plain}"
        _schedule_email(
            db,
            user.email,
            "Verify your MaanCamera email address",
            f"Hello {user.full_name},\n\nVerify your email by opening: {verify_url}\n\nThis link expires in 24 hours.",
            "email_verification",
        )
        return plain

    @staticmethod
    async def request_email_verification(db: AsyncSession, user: User) -> bool:
        if user.email_verified_at:
            return True
        await IdentityService._issue_email_verification(db, user)
        await db.flush()
        return True

    @staticmethod
    async def confirm_email_verification(db: AsyncSession, plain_token: str) -> User:
        token_hash = hash_one_time_token(plain_token)
        stmt = select(IdentityToken).where(
            IdentityToken.token_type == "email_verify",
            IdentityToken.token_hash == token_hash,
            IdentityToken.used_at.is_(None),
        )
        token_row = (await db.execute(stmt)).scalar_one_or_none()
        now = datetime.now(UTC)
        if not token_row or _ensure_utc(token_row.expires_at) <= now:
            raise BusinessRuleViolationException("Verification token is invalid or has expired.")

        user = await db.get(User, token_row.user_id)
        if not user:
            raise NotFoundException("User", token_row.user_id)

        token_row.used_at = now
        user.email_verified_at = now
        await db.flush()
        return user

    @staticmethod
    async def request_phone_otp(db: AsyncSession, user: User, phone: str | None) -> bool:
        target_phone = (phone or user.phone or "").strip()
        if not target_phone:
            raise BusinessRuleViolationException("A phone number is required to request an OTP.")

        code, code_hash = generate_otp_code()
        db.add(
            IdentityToken(
                user_id=user.id,
                token_type="phone_otp",
                token_hash=code_hash,
                target=target_phone,
                expires_at=datetime.now(UTC) + timedelta(minutes=10),
            )
        )
        await db.flush()
        _schedule_sms_otp(db, target_phone, code, "phone_verification")
        return True

    @staticmethod
    async def confirm_phone_otp(
        db: AsyncSession, user: User, code: str, phone: str | None = None
    ) -> User:
        target_phone = (phone or user.phone or "").strip()
        stmt = (
            select(IdentityToken)
            .where(
                IdentityToken.user_id == user.id,
                IdentityToken.token_type == "phone_otp",
                IdentityToken.used_at.is_(None),
            )
            .order_by(IdentityToken.created_at.desc())
        )
        token_row = (await db.execute(stmt)).scalars().first()
        now = datetime.now(UTC)
        if not token_row or _ensure_utc(token_row.expires_at) <= now:
            raise BusinessRuleViolationException("OTP has expired or was not requested.")
        if target_phone and token_row.target != target_phone:
            raise BusinessRuleViolationException("OTP phone number mismatch.")
        if token_row.attempts >= MAX_OTP_ATTEMPTS:
            raise BusinessRuleViolationException("Maximum OTP verification attempts exceeded.")

        if not verify_otp_code(code, token_row.token_hash):
            token_row_id = token_row.id
            if db.bind:
                if db.in_transaction():
                    await db.rollback()
                iso_factory = async_sessionmaker(
                    bind=db.bind, class_=AsyncSession, expire_on_commit=False
                )
                async with iso_factory() as iso_db:
                    row = await iso_db.get(IdentityToken, token_row_id)
                    if row:
                        row.attempts = (row.attempts or 0) + 1
                        await iso_db.commit()
            raise BusinessRuleViolationException("Invalid verification OTP.")

        token_row.used_at = now
        user.phone = token_row.target
        user.phone_verified_at = now
        await db.flush()
        return user

    @staticmethod
    async def request_password_reset(db: AsyncSession, email: str) -> None:
        stmt = select(User).where(User.email == email.lower(), User.status == "active")
        user = (await db.execute(stmt)).scalar_one_or_none()
        if not user or not user.email:
            return
        plain, token_hash = generate_one_time_token()
        db.add(
            IdentityToken(
                user_id=user.id,
                token_type="password_reset",
                token_hash=token_hash,
                target=user.email,
                expires_at=datetime.now(UTC) + timedelta(minutes=30),
            )
        )
        reset_url = f"{settings.FRONTEND_URL.rstrip('/')}/reset-password?token={plain}"
        _schedule_email(
            db,
            user.email,
            "Reset your MaanCamera password",
            f"Hello {user.full_name},\n\nReset your password using: {reset_url}\n\nThis link expires in 30 minutes.",
            "password_reset",
        )
        await db.flush()

    @staticmethod
    async def confirm_password_reset(db: AsyncSession, plain_token: str, new_password: str) -> User:
        token_hash = hash_one_time_token(plain_token)
        stmt = select(IdentityToken).where(
            IdentityToken.token_type == "password_reset",
            IdentityToken.token_hash == token_hash,
            IdentityToken.used_at.is_(None),
        )
        token_row = (await db.execute(stmt)).scalar_one_or_none()
        now = datetime.now(UTC)
        if not token_row or _ensure_utc(token_row.expires_at) <= now:
            raise BusinessRuleViolationException("Password reset token is invalid or has expired.")

        user = await db.get(User, token_row.user_id)
        if not user or user.status != "active":
            raise BusinessRuleViolationException("Account is unavailable for password reset.")

        token_row.used_at = now
        user.password_hash = hash_password(new_password)
        user.failed_login_attempts = 0
        user.locked_until = None

        # Revoke all existing sessions on password reset
        await db.execute(
            update(UserSession)
            .where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        if user.email:
            _schedule_email(
                db,
                user.email,
                "Your MaanCamera password was changed",
                f"Hello {user.full_name},\n\nYour password was recently changed and active sessions were signed out.",
                "password_changed",
            )
        await db.flush()
        return user

    @staticmethod
    async def setup_totp(db: AsyncSession, user: User) -> tuple[str, str]:
        secret = generate_totp_secret()
        user.totp_secret = secret
        user.totp_enabled = False
        await db.flush()
        return secret, build_totp_uri(secret, user.email or str(user.id))

    @staticmethod
    async def enable_totp(db: AsyncSession, user: User, code: str) -> bool:
        if not user.totp_secret:
            raise BusinessRuleViolationException("TOTP setup must be initialized before enabling.")
        if not verify_totp_code(user.totp_secret, code):
            raise BusinessRuleViolationException("Invalid TOTP verification code.")
        user.totp_enabled = True
        await db.flush()
        return True

    @staticmethod
    async def disable_totp(db: AsyncSession, user: User, code: str) -> bool:
        if user.totp_enabled and user.totp_secret and not verify_totp_code(user.totp_secret, code):
            raise BusinessRuleViolationException("Invalid TOTP verification code.")
        user.totp_enabled = False
        user.totp_secret = None
        await db.flush()
        return True

    @staticmethod
    async def list_consents(db: AsyncSession, user_id: uuid.UUID) -> list[ConsentRecord]:
        stmt = (
            select(ConsentRecord)
            .where(ConsentRecord.user_id == user_id)
            .order_by(ConsentRecord.recorded_at.desc())
        )
        return list((await db.execute(stmt)).scalars().all())

    @staticmethod
    async def export_user_data(db: AsyncSession, user: User) -> dict[str, Any]:
        """DPDP personal data export (excludes credential hashes and secret material)."""
        sessions = await IdentityService.list_user_sessions(db, user.id)
        consents = await IdentityService.list_consents(db, user.id)
        enquiries = list(
            (await db.execute(select(Enquiry).where(Enquiry.customer_id == user.id))).scalars().all()
        )
        bookings = list(
            (await db.execute(select(Booking).where(Booking.customer_id == user.id))).scalars().all()
        )
        reviews = list(
            (await db.execute(select(Review).where(Review.customer_id == user.id))).scalars().all()
        )
        enquiry_ids = [e.id for e in enquiries]
        quotations: list[Quotation] = []
        if enquiry_ids:
            quotations = list(
                (
                    await db.execute(select(Quotation).where(Quotation.enquiry_id.in_(enquiry_ids)))
                )
                .scalars()
                .all()
            )

        return {
            "exported_at": datetime.now(UTC).isoformat(),
            "profile": {
                "id": str(user.id),
                "full_name": user.full_name,
                "email": user.email,
                "phone": user.phone,
                "role": user.role,
                "status": user.status,
                "email_verified_at": user.email_verified_at.isoformat() if user.email_verified_at else None,
                "phone_verified_at": user.phone_verified_at.isoformat() if user.phone_verified_at else None,
                "terms_version": user.terms_version,
                "privacy_version": user.privacy_version,
                "created_at": user.created_at.isoformat(),
            },
            "consents": [
                {
                    "consent_type": c.consent_type,
                    "policy_version": c.policy_version,
                    "granted": c.granted,
                    "recorded_at": c.recorded_at.isoformat(),
                }
                for c in consents
            ],
            "sessions": [
                {
                    "id": str(s.id),
                    "user_agent": s.user_agent,
                    "ip_address": str(s.ip_address) if s.ip_address else None,
                    "created_at": s.created_at.isoformat(),
                    "last_used_at": s.last_used_at.isoformat(),
                    "revoked_at": s.revoked_at.isoformat() if s.revoked_at else None,
                }
                for s in sessions
            ],
            "enquiries": [
                {
                    "id": str(e.id),
                    "title": e.title,
                    "city": e.city,
                    "status": e.status,
                    "created_at": e.created_at.isoformat(),
                }
                for e in enquiries
            ],
            "quotations_received": [
                {
                    "id": str(q.id),
                    "enquiry_id": str(q.enquiry_id),
                    "total_amount_minor": q.total_amount_minor,
                    "status": q.status,
                    "created_at": q.created_at.isoformat(),
                }
                for q in quotations
            ],
            "bookings": [
                {
                    "id": str(b.id),
                    "booking_status": b.booking_status,
                    "agreed_amount_minor": b.agreed_amount_minor,
                    "paid_amount_minor": b.paid_amount_minor,
                    "shoot_date": b.shoot_date.isoformat(),
                }
                for b in bookings
            ],
            "reviews": [
                {
                    "id": str(r.id),
                    "booking_id": str(r.booking_id),
                    "overall_rating": float(r.overall_rating),
                    "review_text": r.review_text,
                }
                for r in reviews
            ],
        }

    @staticmethod
    async def delete_account(
        db: AsyncSession,
        user: User,
        *,
        password: str | None = None,
    ) -> bool:
        """DPDP right-to-erasure anonymization while preserving financial/booking ledger integrity."""
        if user.password_hash and password and not verify_password(password, user.password_hash):
            raise UnauthorizedException("Current password verification failed.")

        active_bookings = (
            await db.execute(
                select(Booking.id).where(
                    Booking.customer_id == user.id,
                    Booking.booking_status.in_(["pending_payment", "confirmed", "in_progress", "disputed"]),
                )
            )
        ).scalar_one_or_none()
        if active_bookings:
            raise BusinessRuleViolationException(
                "Account cannot be deleted while active bookings or disputes are still open."
            )

        now = datetime.now(UTC)
        user.email = f"deleted-{user.id}@anonymized.invalid"
        user.phone = None
        user.full_name = "Deleted User"
        user.avatar_url = None
        user.password_hash = None
        user.totp_secret = None
        user.totp_enabled = False
        user.status = "deactivated"
        user.deleted_at = now

        await db.execute(
            update(UserSession)
            .where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        await db.flush()
        return True
