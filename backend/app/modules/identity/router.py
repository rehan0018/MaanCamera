"""Authentication, verification, TOTP 2FA, session, and DPDP compliance HTTP endpoints."""

import uuid

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import apply_rls_context, get_db
from app.core.exceptions import UnauthorizedException
from app.core.rate_limit import get_client_ip, limiter
from app.core.responses import success_response
from app.core.security import generate_csrf_token, hash_session_token
from app.modules.identity.models import User
from app.modules.identity.schemas import (
    ConsentRecordResponse,
    DeleteAccountRequest,
    EmailVerifyConfirmRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    PhoneOtpConfirmRequest,
    PhoneOtpRequest,
    TotpCodeRequest,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
    UserSessionResponse,
)
from app.modules.identity.service import IdentityService

router = APIRouter(prefix="", tags=["Authentication & Users"])


def _extract_session_token(request: Request) -> str | None:
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[len("Bearer ") :]
    return token


def _set_auth_cookies(res: Response, session_token: str, csrf_token: str) -> None:
    max_age = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400
    res.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=session_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=max_age,
        path="/",
    )
    res.set_cookie(
        key=settings.CSRF_COOKIE_NAME,
        value=csrf_token,
        httponly=False,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=max_age,
        path="/",
    )


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    """Dependency for extracting and validating session cookie or Bearer token and binding RLS."""
    token = _extract_session_token(request)
    if not token:
        raise UnauthorizedException("Authentication session required.")

    user = await IdentityService.get_user_by_session_token(db, token)
    if not user:
        raise UnauthorizedException("Session is invalid or has expired.")

    request.state.user_id = str(user.id)
    await apply_rls_context(db, user_id=str(user.id), role=user.role)
    return user


async def get_optional_current_user(
    request: Request, db: AsyncSession = Depends(get_db)
) -> User | None:
    """Resolve authenticated user when present without failing anonymous public requests."""
    token = _extract_session_token(request)
    if not token:
        return None
    user = await IdentityService.get_user_by_session_token(db, token)
    if not user:
        return None
    request.state.user_id = str(user.id)
    await apply_rls_context(db, user_id=str(user.id), role=user.role)
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
    user = await IdentityService.register(
        db,
        req,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )
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
    client_ip = get_client_ip(request)
    user, token = await IdentityService.authenticate(
        db, req, user_agent=user_agent, ip=client_ip
    )

    csrf_token = generate_csrf_token()
    res = success_response(
        data={
            "user": UserResponse.model_validate(user).model_dump(mode="json"),
            "csrf_token": csrf_token,
        }
    )
    _set_auth_cookies(res, token, csrf_token)
    return res


@router.post("/auth/refresh")
async def refresh_session(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    token = _extract_session_token(request)
    if not token:
        raise UnauthorizedException("Authentication session required.")

    user, new_token = await IdentityService.refresh_session(db, token)
    csrf_token = generate_csrf_token()
    res = success_response(
        data={
            "user": UserResponse.model_validate(user).model_dump(mode="json"),
            "csrf_token": csrf_token,
        }
    )
    _set_auth_cookies(res, new_token, csrf_token)
    return res


@router.post("/auth/logout")
async def logout(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    token = _extract_session_token(request)
    if token:
        await IdentityService.revoke_session(db, token)
    res = success_response(data={"message": "Logged out successfully."})
    res.delete_cookie(settings.SESSION_COOKIE_NAME, path="/")
    res.delete_cookie(settings.CSRF_COOKIE_NAME, path="/")
    return res


@router.post("/auth/verify-email/request")
@limiter.limit("5/minute")
async def request_email_verification(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await IdentityService.request_email_verification(db, current_user)
    return success_response(data={"message": "Verification instructions sent if email is unverified."})


@router.post("/auth/verify-email/confirm")
async def confirm_email_verification(
    req: EmailVerifyConfirmRequest,
    db: AsyncSession = Depends(get_db),
):
    user = await IdentityService.confirm_email_verification(db, req.token)
    return success_response(data=UserResponse.model_validate(user).model_dump(mode="json"))


@router.post("/auth/verify-phone/request")
@limiter.limit("5/minute")
async def request_phone_otp(
    request: Request,
    req: PhoneOtpRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await IdentityService.request_phone_otp(db, current_user, req.phone)
    return success_response(data={"message": "OTP dispatched for phone verification."})


@router.post("/auth/verify-phone/confirm")
async def confirm_phone_otp(
    req: PhoneOtpConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user = await IdentityService.confirm_phone_otp(db, current_user, req.code, phone=req.phone)
    return success_response(data=UserResponse.model_validate(user).model_dump(mode="json"))


@router.post("/auth/password-reset/request")
@limiter.limit("5/minute")
async def request_password_reset(
    request: Request,
    req: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
):
    await IdentityService.request_password_reset(db, req.email)
    return success_response(
        data={"message": "If an active account matches that email, reset instructions were sent."}
    )


@router.post("/auth/password-reset/confirm")
async def confirm_password_reset(
    req: PasswordResetConfirmRequest,
    db: AsyncSession = Depends(get_db),
):
    await IdentityService.confirm_password_reset(db, req.token, req.new_password)
    return success_response(data={"message": "Password reset successfully. Please sign in again."})


@router.get("/auth/sessions")
async def list_sessions(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_token = _extract_session_token(request)
    current_hash = hash_session_token(current_token) if current_token else None
    sessions = await IdentityService.list_user_sessions(db, current_user.id)
    payload = []
    for s in sessions:
        row = UserSessionResponse.model_validate(
            {
                "id": s.id,
                "user_agent": s.user_agent,
                "ip_address": str(s.ip_address) if s.ip_address else None,
                "created_at": s.created_at,
                "last_used_at": s.last_used_at,
                "expires_at": s.expires_at,
                "revoked_at": s.revoked_at,
                "is_current": bool(current_hash and s.session_token_hash == current_hash),
            }
        ).model_dump(mode="json")
        payload.append(row)
    return success_response(data=payload)


@router.delete("/auth/sessions/{session_id}")
async def revoke_session_by_id(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await IdentityService.revoke_user_session_by_id(db, current_user.id, session_id)
    return success_response(data={"revoked": True, "session_id": str(session_id)})


@router.post("/auth/totp/setup")
async def setup_totp(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    secret, otpauth_uri = await IdentityService.setup_totp(db, current_user)
    return success_response(data={"secret": secret, "otpauth_uri": otpauth_uri})


@router.post("/auth/totp/enable")
async def enable_totp(
    req: TotpCodeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await IdentityService.enable_totp(db, current_user, req.code)
    return success_response(data={"totp_enabled": True})


@router.post("/auth/totp/disable")
async def disable_totp(
    req: TotpCodeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await IdentityService.disable_totp(db, current_user, req.code)
    return success_response(data={"totp_enabled": False})


@router.get("/users/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return success_response(
        data=UserResponse.model_validate(current_user).model_dump(mode="json")
    )


@router.get("/users/me/consents")
async def list_my_consents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    consents = await IdentityService.list_consents(db, current_user.id)
    return success_response(
        data=[ConsentRecordResponse.model_validate(c).model_dump(mode="json") for c in consents]
    )


@router.get("/users/me/export")
async def export_my_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await IdentityService.export_user_data(db, current_user)
    return success_response(data=data)


@router.delete("/users/me")
async def delete_my_account(
    req: DeleteAccountRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await IdentityService.delete_account(db, current_user, password=req.password)
    res = success_response(data={"deleted": True})
    res.delete_cookie(settings.SESSION_COOKIE_NAME, path="/")
    res.delete_cookie(settings.CSRF_COOKIE_NAME, path="/")
    return res
