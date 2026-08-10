from __future__ import annotations
class LLMProviderError(RuntimeError):
    """Base error raised by generation and embedding providers."""
    def __init__(
        self,
        message: str,
        *,
        provider: str,
        code: str = "llm_provider_error",
        status_code: int = 502,
        retry_after_seconds: int | None = None,
        operation: str | None = None,
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.code = code
        self.status_code = status_code
        self.retry_after_seconds = retry_after_seconds
        self.operation = operation

    def to_detail(self) -> dict:
        detail = {
            "code": self.code,
            "provider": self.provider,
            "message": str(self),
        }
        if self.operation:
            detail["operation"] = self.operation
        if self.retry_after_seconds is not None:
            detail["retry_after_seconds"] = self.retry_after_seconds
        return detail


class LLMAuthenticationError(LLMProviderError):
    def __init__(self, message: str, *, provider: str, operation: str | None = None):
        super().__init__(
            message,
            provider=provider,
            code="llm_authentication_failed",
            status_code=401,
            operation=operation,
        )


class LLMPermissionError(LLMProviderError):
    def __init__(self, message: str, *, provider: str, operation: str | None = None):
        super().__init__(
            message,
            provider=provider,
            code="llm_permission_denied",
            status_code=403,
            operation=operation,
        )


class LLMModelNotFoundError(LLMProviderError):
    def __init__(self, message: str, *, provider: str, operation: str | None = None):
        super().__init__(
            message,
            provider=provider,
            code="llm_model_not_found",
            status_code=404,
            operation=operation,
        )


class LLMRateLimitError(LLMProviderError):
    def __init__(
        self,
        message: str,
        *,
        provider: str,
        retry_after_seconds: int | None = None,
        operation: str | None = None,
    ) -> None:
        super().__init__(
            message,
            provider=provider,
            code="llm_quota_or_rate_limit_exceeded",
            status_code=429,
            retry_after_seconds=retry_after_seconds,
            operation=operation,
        )


class LLMTimeoutError(LLMProviderError):
    def __init__(self, message: str, *, provider: str, operation: str | None = None):
        super().__init__(
            message,
            provider=provider,
            code="llm_request_timeout",
            status_code=504,
            operation=operation,
        )


class LLMConnectionError(LLMProviderError):
    def __init__(self, message: str, *, provider: str, operation: str | None = None):
        super().__init__(
            message,
            provider=provider,
            code="llm_connection_failed",
            status_code=503,
            operation=operation,
        )


class LLMEmptyResponseError(LLMProviderError):
    def __init__(self, message: str, *, provider: str, operation: str | None = None):
        super().__init__(
            message,
            provider=provider,
            code="llm_empty_response",
            status_code=502,
            operation=operation,
        )
