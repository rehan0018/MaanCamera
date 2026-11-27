"""MaanCamera Modular Monolith FastAPI Application Entrypoint."""

import logging
import time
import uuid
from contextlib import asynccontextmanager
from urllib.parse import urlparse

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.exceptions import AppException
from app.core.rate_limit import limiter
from app.core.responses import error_response
from app.core.security import PiiScrubbingFilter, verify_csrf_token
from app.modules.ai.router import router as ai_router
from app.modules.bookings.router import router as bookings_router
from app.modules.enquiries.router import router as enquiries_router
from app.modules.identity.router import router as identity_router
from app.modules.payments.router import router as payments_router
from app.modules.portfolios.router import router as portfolios_router
from app.modules.professionals.router import router as professionals_router
from app.modules.quotations.router import router as quotations_router
from app.modules.reviews.router import router as reviews_router
from app.modules.search.router import router as search_router

logging.basicConfig(level=logging.INFO)
for _handler in logging.getLogger().handlers:
    _handler.addFilter(PiiScrubbingFilter())
logger = logging.getLogger("maancamera")
logger.addFilter(PiiScrubbingFilter())


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing MaanCamera Application Services...")
    yield
    logger.info("Shutting down MaanCamera Application Services...")


app = FastAPI(
    title="MaanCamera API",
    description="India's AI-Powered Marketplace & Business SaaS for Photography & Videography Professionals",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan,
)

app.state.limiter = limiter


def _normalize_origin(raw: str) -> str:
    parsed = urlparse(raw)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}".lower()
    return raw.rstrip("/").lower()


# ------------------------------------------------------------------------------
# 1. Request ID, Audit & CSRF Middleware
# ------------------------------------------------------------------------------
@app.middleware("http")
async def security_and_request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    start_time = time.perf_counter()

    # Enforce Origin + Double-Submit CSRF checks on state-changing HTTP requests
    if request.method in ("POST", "PATCH", "PUT", "DELETE"):
        webhook_prefix = f"{settings.API_V1_PREFIX}/payments/webhooks/"
        if not request.url.path.startswith(webhook_prefix):
            origin_candidates = [*settings.CORS_ORIGINS, settings.FRONTEND_URL, settings.BACKEND_URL]
            if settings.ENVIRONMENT == "test":
                origin_candidates.append("http://testserver")
            allowed_origins = {_normalize_origin(o) for o in origin_candidates}

            origin = request.headers.get("Origin")
            referer = request.headers.get("Referer")
            if origin:
                if _normalize_origin(origin) not in allowed_origins:
                    return error_response(
                        code="CSRF_ORIGIN_MISMATCH",
                        message="Cross-origin request rejected.",
                        status_code=status.HTTP_403_FORBIDDEN,
                        request_id=request_id,
                    )
            elif referer and _normalize_origin(referer) not in allowed_origins:
                return error_response(
                    code="CSRF_REFERER_MISMATCH",
                    message="Cross-origin referer rejected.",
                    status_code=status.HTTP_403_FORBIDDEN,
                    request_id=request_id,
                )

            # Enforce double-submit CSRF token when cookie session is active (exempt Bearer-only)
            has_session_cookie = settings.SESSION_COOKIE_NAME in request.cookies
            if has_session_cookie:
                cookie_csrf = request.cookies.get(settings.CSRF_COOKIE_NAME, "")
                header_csrf = request.headers.get("X-CSRF-Token", "")
                if not verify_csrf_token(cookie_csrf, header_csrf):
                    return error_response(
                        code="CSRF_TOKEN_INVALID",
                        message="Missing or invalid CSRF token.",
                        status_code=status.HTTP_403_FORBIDDEN,
                        request_id=request_id,
                    )

    response = await call_next(request)

    process_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time-Ms"] = str(process_time_ms)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if not (
        settings.ENVIRONMENT != "production"
        and request.url.path in ("/docs", "/redoc", "/api/v1/openapi.json")
    ):
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
        )
    if settings.ENVIRONMENT == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# ------------------------------------------------------------------------------
# 2. CORS Middleware (registered last to be outermost)
# ------------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-CSRF-Token",
        "X-Request-ID",
        "Idempotency-Key",
    ],
    expose_headers=["X-Request-ID"],
)


# ------------------------------------------------------------------------------
# 3. Global Exception Handlers
# ------------------------------------------------------------------------------
@app.exception_handler(RateLimitExceeded)
async def rate_limit_exception_handler(request: Request, exc: RateLimitExceeded):
    req_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    return error_response(
        code="RATE_LIMIT_EXCEEDED",
        message=f"Rate limit exceeded: {exc.detail}",
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        request_id=req_id,
    )


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    req_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    return error_response(
        code=exc.code,
        message=exc.message,
        details=exc.details,
        status_code=exc.status_code,
        request_id=req_id,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    req_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    safe_errors = jsonable_encoder(exc.errors(), custom_encoder={BaseException: str})
    return error_response(
        code="VALIDATION_ERROR",
        message="Request parameters failed validation.",
        details={"errors": safe_errors},
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        request_id=req_id,
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    req_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    logger.exception(f"Unhandled server error [Request ID: {req_id}]: {exc}")
    return error_response(
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected system error occurred. Please contact support.",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        request_id=req_id,
    )


# ------------------------------------------------------------------------------
# 4. System Health & Readiness Endpoints
# ------------------------------------------------------------------------------
@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "healthy", "service": "maancamera-backend", "timestamp": time.time()}


@app.get("/ready", tags=["System"])
async def readiness_check():
    db_status = "connected"
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception as e:
        logger.warning(f"Database readiness probe failed: {e}")
        db_status = "disconnected"

    status_str = "ready" if db_status == "connected" else "degraded"
    return {
        "status": status_str,
        "database": db_status,
        "storage": "connected",
        "timestamp": time.time(),
    }


# ------------------------------------------------------------------------------
# 5. Mount Modular API Routers under /api/v1
# ------------------------------------------------------------------------------
app.include_router(identity_router, prefix="/api/v1")
app.include_router(professionals_router, prefix="/api/v1")
app.include_router(portfolios_router, prefix="/api/v1")
app.include_router(search_router, prefix="/api/v1")
app.include_router(enquiries_router, prefix="/api/v1")
app.include_router(quotations_router, prefix="/api/v1")
app.include_router(bookings_router, prefix="/api/v1")
app.include_router(payments_router, prefix="/api/v1")
app.include_router(reviews_router, prefix="/api/v1")
app.include_router(ai_router, prefix="/api/v1")
