"""Service for user authentication, registration, and session lifecycle."""

from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, UnauthorizedException
from app.core.security import (
    calculate_session_expiry,
    generate_session_token,
    hash_password,
    hash_session_token,
    verify_password,
)
from app.modules.identity.models import User, UserSession
from app.modules.identity.schemas import UserLoginRequest, UserRegisterRequest


class IdentityService:
    @staticmethod
    async def register(db: AsyncSession, req: UserRegisterRequest) -> User:
        # Check existing email
        stmt = select(User).where(User.email == req.email.lower())
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise ConflictException("An account with this email address already exists.")

        user = User(
            email=req.email.lower(),
            phone=req.phone,
            password_hash=hash_password(req.password),
            full_name=req.full_name,
            role=req.role or "customer",
            status="active",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def authenticate(db: AsyncSession, req: UserLoginRequest, user_agent: str | None = None, ip: str | None = None) -> tuple[User, str]:
        stmt = select(User).where(User.email == req.email.lower())
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user or not user.password_hash or not verify_password(req.password, user.password_hash):
            raise UnauthorizedException("Invalid email address or password.")

        if user.status != "active":
            raise UnauthorizedException("Your account is currently inactive or suspended.")

        # Create session
        plain_token = generate_session_token()
        hashed_token = hash_session_token(plain_token)
        session = UserSession(
            user_id=user.id,
            session_token_hash=hashed_token,
            user_agent=user_agent,
            expires_at=calculate_session_expiry(),
        )
        db.add(session)
        await db.flush()

        return user, plain_token

    @staticmethod
    async def get_user_by_session_token(db: AsyncSession, token: str) -> User | None:
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

        # Update last used
        session.last_used_at = datetime.now(UTC)
        await db.flush()

        user_stmt = select(User).where(User.id == session.user_id)
        user_res = await db.execute(user_stmt)
        return user_res.scalar_one_or_none()

    @staticmethod
    async def revoke_session(db: AsyncSession, token: str) -> bool:
        hashed_token = hash_session_token(token)
        stmt = update(UserSession).where(UserSession.session_token_hash == hashed_token).values(revoked_at=datetime.now(UTC))
        await db.execute(stmt)
        return True
