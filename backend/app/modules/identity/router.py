"""Authentication and User HTTP endpoints with CSRF and Rate Limiting."""

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import UnauthorizedException
from app.core.rate_limit import limiter
from app.core.responses import success_response
from app.core.security import generate_csrf_token
from app.modules.identity.models import User
from app.modules.identity.schemas import (
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.modules.identity.service import IdentityService

router = APIRouter(prefix="", tags=["Authentication & Users"])


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    """Dependency for extracting and validating session cookie or Bearer token."""
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[len("Bearer "):]

    if not token:
        raise UnauthorizedException("Authentication session required.")

    user = await IdentityService.get_user_by_session_token(db, token)
    if not user:
        raise UnauthorizedException("Session is invalid or has expired.")

    request.state.user_id = str(user.id)
    if db.bind and db.bind.dialect.name == "postgresql":
        await db.execute(
            text(
                "SELECT set_config('app.current_user_id', :uid, true), "
                "set_config('app.current_user_role', :role, true)"
            ),
            {"uid": str(user.id), "role": user.role},
        )
    return user


@router.get("/auth/csrf")
async def get_csrf_token(response: Response):
    """Issue a signed CSRF double-submit cookie for browser sessions."""
    csrf_token = generate_csrf_token()
    res = success_response(data={"csrf_token": csrf_token})
    res.set_cookie(
        key=settings.CSRF_COOKIE_NAME,
        value=csrf_token,
        httponly=False,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/",
    )
    return res


@router.post("/auth/register", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(
    request: Request,
    response: Response,
    req: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    user = await IdentityService.register(db, req)
    return success_response(
        data=UserResponse.model_validate(user).model_dump(mode="json"),
        status_code=status.HTTP_201_CREATED,
    )


@router.post("/auth/login")
@limiter.limit("5/minute")
async def login(
    request: Request,
    response: Response,
    req: UserLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    user_agent = request.headers.get("User-Agent")
    user, token = await IdentityService.authenticate(db, req, user_agent=user_agent)
    await db.commit()

    csrf_token = generate_csrf_token()
    res = success_response(
        data={
            "user": UserResponse.model_validate(user).model_dump(mode="json"),
            "session_token": token,
            "csrf_token": csrf_token,
        }
    )

    res.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/",
    )
    res.set_cookie(
        key=settings.CSRF_COOKIE_NAME,
        value=csrf_token,
        httponly=False,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/",
    )
    return res


@router.post("/auth/logout")
async def logout(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if token:
        await IdentityService.revoke_session(db, token)
        await db.commit()
    res = success_response(data={"message": "Logged out successfully."})
    res.delete_cookie(settings.SESSION_COOKIE_NAME, path="/")
    res.delete_cookie(settings.CSRF_COOKIE_NAME, path="/")
    return res


@router.get("/users/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return success_response(
        data=UserResponse.model_validate(current_user).model_dump(mode="json")
    )
