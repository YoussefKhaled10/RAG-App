from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class HybridSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    query: str = Field(..., min_length=2, max_length=2000)
    limit: int = Field(default=5, ge=1, le=20)
    semantic_limit: int = Field(default=20, ge=1, le=100)
    keyword_limit: int = Field(default=20, ge=1, le=100)
    rrf_k: int = Field(default=60, ge=1, le=200)


class HybridSearchResult(BaseModel):
    chunk_id: int
    asset_id: int | None = None
    chunk_order: int | None = None
    text: str
    metadata: dict = Field(default_factory=dict)
    semantic_score: float | None = None
    keyword_score: float | None = None
    fusion_score: float = Field(..., ge=0)
    semantic_rank: int | None = None
    keyword_rank: int | None = None
    matched_by: list[Literal["semantic", "keyword"]]


class HybridSearchResponse(BaseModel):
    project_id: int
    query: str
    search_type: Literal["hybrid"] = "hybrid"
    results: list[HybridSearchResult]
    total: int = Field(..., ge=0)


class AskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    question: str = Field(..., min_length=2, max_length=4000)
    limit: int = Field(default=5, ge=1, le=20)
    semantic_limit: int = Field(default=20, ge=1, le=100)
    keyword_limit: int = Field(default=20, ge=1, le=100)
    rrf_k: int = Field(default=60, ge=1, le=200)


class AskResponse(BaseModel):
    project_id: int
    question: str
    answer: str
    sources: list[HybridSearchResult]
