"""Authentication and User HTTP endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import UnauthorizedException
from app.core.responses import success_response
from app.modules.identity.models import User
from app.modules.identity.schemas import (
    UserRegisterRequest,
    UserLoginRequest,
    UserResponse,
)
from app.modules.identity.service import IdentityService

router = APIRouter(prefix="", tags=["Authentication & Users"])


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    """Dependency for extracting and validating session cookie."""
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not token:
        # Check Bearer auth fallback
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[len("Bearer "):]

    if not token:
        raise UnauthorizedException("Authentication session required.")

    user = await IdentityService.get_user_by_session_token(db, token)
    if not user:
        raise UnauthorizedException("Session is invalid or has expired.")
    return user


@router.post("/auth/register", status_code=status.HTTP_201_CREATED)
async def register(req: UserRegisterRequest, db: AsyncSession = Depends(get_db)):
    user = await IdentityService.register(db, req)
    return success_response(
        data=UserResponse.model_validate(user).model_dump(mode="json"),
        status_code=status.HTTP_201_CREATED,
    )


@router.post("/auth/login")
async def login(req: UserLoginRequest, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    user_agent = request.headers.get("User-Agent")
    user, token = await IdentityService.authenticate(db, req, user_agent=user_agent)

    # Set secure HTTP-only cookie
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
    )

    return success_response(
        data={
            "user": UserResponse.model_validate(user).model_dump(mode="json"),
            "session_token": token,
        }
    )


@router.post("/auth/logout")
async def logout(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if token:
        await IdentityService.revoke_session(db, token)
        response.delete_cookie(settings.SESSION_COOKIE_NAME)
    return success_response(data={"message": "Logged out successfully."})


@router.get("/users/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return success_response(
        data=UserResponse.model_validate(current_user).model_dump(mode="json")
    )
