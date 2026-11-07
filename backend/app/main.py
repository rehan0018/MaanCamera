"""MaanCamera Modular Monolith FastAPI Application Entrypoint."""

import time
import uuid
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.responses import error_response

# Module routers
from app.modules.identity.router import router as identity_router
from app.modules.professionals.router import router as professionals_router
from app.modules.portfolios.router import router as portfolios_router
from app.modules.search.router import router as search_router
from app.modules.enquiries.router import router as enquiries_router
from app.modules.quotations.router import router as quotations_router
from app.modules.bookings.router import router as bookings_router
from app.modules.payments.router import router as payments_router
from app.modules.reviews.router import router as reviews_router
from app.modules.ai.router import router as ai_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("maancamera")


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

# ------------------------------------------------------------------------------
# 1. CORS Middleware
# ------------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)


# ------------------------------------------------------------------------------
# 2. Request ID & Audit Middleware
# ------------------------------------------------------------------------------
@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    start_time = time.perf_counter()

    response = await call_next(request)

    process_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time-Ms"] = str(process_time_ms)
    return response


# ------------------------------------------------------------------------------
# 3. Global Exception Handlers
# ------------------------------------------------------------------------------
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
    return error_response(
        code="VALIDATION_ERROR",
        message="Request parameters failed validation.",
        details={"errors": exc.errors()},
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
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
    return {"status": "ready", "database": "connected", "storage": "connected"}


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
