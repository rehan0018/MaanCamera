"""Custom exception hierarchy for domain errors and API handlers."""

from typing import Any, Dict, Optional
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.responses import error_response


class MaanCameraException(Exception):
    """Base exception for all domain logic errors in MaanCamera."""

    def __init__(
        self,
        code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 400,
    ):
        self.code = code
        self.message = message
        self.details = details or {}
        self.status_code = status_code
        super().__init__(message)


class NotFoundException(MaanCameraException):
    def __init__(self, resource: str, identifier: Any):
        super().__init__(
            code="RESOURCE_NOT_FOUND",
            message=f"{resource} with identifier '{identifier}' was not found.",
            status_code=404,
        )


class UnauthorizedException(MaanCameraException):
    def __init__(self, message: str = "Authentication credentials were not provided or are invalid."):
        super().__init__(
            code="UNAUTHORIZED",
            message=message,
            status_code=401,
        )


class ForbiddenException(MaanCameraException):
    def __init__(self, message: str = "You do not have permission to perform this action."):
        super().__init__(
            code="FORBIDDEN",
            message=message,
            status_code=403,
        )


class ConflictException(MaanCameraException):
    def __init__(self, message: str):
        super().__init__(
            code="RESOURCE_CONFLICT",
            message=message,
            status_code=409,
        )


async def maancamera_exception_handler(request: Request, exc: MaanCameraException):
    return error_response(
        code=exc.code,
        message=exc.message,
        details=exc.details,
        status_code=exc.status_code,
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return error_response(
        code="VALIDATION_ERROR",
        message="The request payload failed schema validation.",
        details={"errors": exc.errors()},
        status_code=422,
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return error_response(
        code=f"HTTP_{exc.status_code}",
        message=str(exc.detail),
        status_code=exc.status_code,
    )


async def general_exception_handler(request: Request, exc: Exception):
    return error_response(
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected server error occurred. Please try again later.",
        status_code=500,
    )
