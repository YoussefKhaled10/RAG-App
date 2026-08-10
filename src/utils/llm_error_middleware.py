import logging

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from stores.llm.LLMExceptions import LLMProviderError


logger = logging.getLogger(__name__)


class LLMErrorMiddleware(BaseHTTPMiddleware):
    """Convert safe provider exceptions into accurate HTTP responses."""

    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except LLMProviderError as exc:
            logger.warning(
                "LLM provider error. provider=%s operation=%s code=%s status=%s",
                exc.provider,
                exc.operation,
                exc.code,
                exc.status_code,
            )
            headers = {}
            if exc.retry_after_seconds is not None:
                headers["Retry-After"] = str(exc.retry_after_seconds)
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.to_detail()},
                headers=headers,
            )
def setup_llm_error_handling(app) -> None:
    app.add_middleware(LLMErrorMiddleware)
