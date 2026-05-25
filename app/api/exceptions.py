"""API exceptions and error handling."""

from aiohttp import web


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


async def api_error_middleware(app: web.Application, handler):
    async def middleware_handler(request: web.Request) -> web.Response:
        try:
            return await handler(request)
        except APIException as e:
            return web.json_response(e.to_dict(), status=e.status_code)
        except Exception as e:
            app["logger"].exception(f"Unhandled error: {e}")
            return web.json_response(
                {"error": "internal_error", "message": "Internal server error"},
                status=500,
            )

    return middleware_handler
