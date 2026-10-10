from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.services.location.errors import LocationError


def _payload(code: str, message: str, status_code: int, details: object | None = None) -> dict:
    body: dict = {
        "error": {
            "code": code,
            "message": message,
        }
    }
    if details is not None:
        body["error"]["details"] = details
    return body


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(LocationError)
    async def location_exception_handler(_request: Request, exc: LocationError):
        return JSONResponse(
            status_code=exc.status_code,
            content=_payload(exc.code, exc.message, exc.status_code),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(_request: Request, exc: StarletteHTTPException):
        message = exc.detail if isinstance(exc.detail, str) else "Request failed"
        code = "http_error"
        if exc.status_code == 401:
            code = "unauthorized"
        elif exc.status_code == 403:
            code = "forbidden"
        elif exc.status_code == 404:
            code = "not_found"
        elif exc.status_code == 409:
            code = "conflict"
        elif exc.status_code == 422:
            code = "validation_error"
        return JSONResponse(
            status_code=exc.status_code,
            content=_payload(code, message, exc.status_code),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_request: Request, exc: RequestValidationError):
        readable = []
        for err in exc.errors():
            loc = " ".join(str(part) for part in err.get("loc", []) if part != "body")
            readable.append(f"{loc}: {err.get('msg')}" if loc else str(err.get("msg")))
        return JSONResponse(
            status_code=422,
            content=_payload(
                "validation_error",
                readable[0] if readable else "Invalid request",
                422,
                readable,
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(_request: Request, _exc: Exception):
        return JSONResponse(
            status_code=500,
            content=_payload("server_error", "Something went wrong. Please try again.", 500),
        )
