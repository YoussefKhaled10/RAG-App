from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)
class MessageResponse(BaseModel):
    """
    Generic success response.
    """
    success: bool = True

    message: str = Field(
        ...,
        min_length=1,
        max_length=255,
    )


class ErrorResponse(BaseModel):
    """
    Generic error response.

    details may contain additional validation
    or processing error information.
    """

    success: bool = False

    error: str = Field(
        ...,
        min_length=1,
        max_length=255,
    )

    details: dict[str, Any] | list[Any] | None = None


class PaginationParams(BaseModel):
    """
    Common pagination parameters.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    offset: int = Field(
        default=0,
        ge=0,
    )

    limit: int = Field(
        default=100,
        ge=1,
        le=100,
    )