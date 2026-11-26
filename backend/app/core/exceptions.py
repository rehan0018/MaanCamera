"""Custom exception hierarchy for domain errors and API handlers."""

from typing import Any, Dict, Optional


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


# Backward-compatibility alias
AppException = MaanCameraException


class NotFoundException(MaanCameraException):
    def __init__(self, resource: str, identifier: Any = None):
        if identifier is not None:
            msg = f"{resource} with identifier '{identifier}' was not found."
        else:
            msg = resource if ("not found" in resource.lower()) else f"{resource} not found."
        super().__init__(
            code="RESOURCE_NOT_FOUND",
            message=msg,
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


class BusinessRuleViolationException(MaanCameraException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="BUSINESS_RULE_VIOLATION",
            message=message,
            details=details,
            status_code=400,
        )


class ValidationException(MaanCameraException):
    def __init__(self, message: str = "Validation failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            details=details,
            status_code=422,
        )
