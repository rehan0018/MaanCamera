"""Standard API response builders matching MaanCamera API specification v1.0."""

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi.responses import JSONResponse


def success_response(
    data: Any = None,
    meta: dict[str, Any] | None = None,
    status_code: int = 200,
    request_id: str | None = None,
) -> JSONResponse:
    """Format and return a standardized success response envelope."""
    payload_meta = {
        "request_id": request_id or str(uuid.uuid4()),
        "timestamp": datetime.now(UTC).isoformat(),
    }
    if meta:
        payload_meta.update(meta)

    return JSONResponse(
        status_code=status_code,
        content={
            "success": True,
            "data": data,
            "meta": payload_meta,
        },
    )


def error_response(
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
    status_code: int = 400,
    request_id: str | None = None,
) -> JSONResponse:
    """Format and return a standardized error response envelope."""
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": {
                "code": code,
                "message": message,
                "details": details or {},
            },
            "meta": {
                "request_id": request_id or str(uuid.uuid4()),
                "timestamp": datetime.now(UTC).isoformat(),
            },
        },
    )
