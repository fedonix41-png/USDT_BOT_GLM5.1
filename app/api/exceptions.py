"""API exceptions and error handling."""




class APIException(Exception):  # noqa: N818
    def __init__(self, message: str, status_code: int = 400, error_code: str = "error"):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(self.message)

    def to_dict(self) -> dict:
        return {"error": self.error_code, "message": self.message}


class UnauthorizedError(APIException):
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, status_code=401, error_code="unauthorized")


class ForbiddenError(APIException):
    def __init__(self, message: str = "Forbidden"):
        super().__init__(message, status_code=403, error_code="forbidden")


class NotFoundError(APIException):
    def __init__(self, message: str = "Not found"):
        super().__init__(message, status_code=404, error_code="not_found")


class ValidationError(APIException):
    def __init__(self, message: str = "Validation error"):
        super().__init__(message, status_code=422, error_code="validation_error")


class RateLimitError(APIException):
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, status_code=429, error_code="rate_limit")


class LoginBlockedError(APIException):
    def __init__(self, retry_after: int):
        super().__init__(
            f"Too many failed attempts. Try again in {retry_after} seconds.",
            status_code=429,
            error_code="login_blocked",
        )
        self.retry_after = retry_after


from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import logging

def setup_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(APIException)
    async def api_exception_handler(request: Request, exc: APIException) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=exc.to_dict())

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger = logging.getLogger("app.api.exceptions")
        logger.exception(f"Unhandled error: {exc}")
        return JSONResponse(
            status_code=500,
            content={"error": "internal_error", "message": "Internal server error"},
        )
