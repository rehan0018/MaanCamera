"""Standard API response builders matching MaanCamera API specification v1.0."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from fastapi.responses import JSONResponse


def success_response(
    data: Any = None,
    meta: Optional[Dict[str, Any]] = None,
    status_code: int = 200,
) -> JSONResponse:
    """Format and return a standardized success response envelope."""
    payload_meta = {
        "request_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
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
    details: Optional[Dict[str, Any]] = None,
    status_code: int = 400,
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
                "request_id": str(uuid.uuid4()),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        },
    )
