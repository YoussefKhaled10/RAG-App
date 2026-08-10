from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class HybridSearchRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    query: str = Field(
        ...,
        min_length=2,
        max_length=2000,
    )
    limit: int = Field(default=5, ge=1, le=20)
    semantic_limit: int = Field(default=20, ge=1, le=100)
    keyword_limit: int = Field(default=20, ge=1, le=100)
    rrf_k: int = Field(default=60, ge=1, le=200)
    rerank: bool = True
    rerank_candidates: int = Field(default=30, ge=1, le=100)


class CitationInfo(BaseModel):
    file_name: str
    stored_file_name: str | None = None
    file_type: str | None = None
    page_number: int | None = Field(default=None, ge=1)
    sheet_name: str | None = None
    row_start: int | None = Field(default=None, ge=1)
    row_end: int | None = Field(default=None, ge=1)


class HybridSearchResult(BaseModel):
    chunk_id: int
    asset_id: int | None = None
    chunk_order: int | None = None
    text: str
    metadata: dict = Field(default_factory=dict)
    citation: CitationInfo | None = None

    semantic_score: float | None = None
    keyword_score: float | None = None
    fusion_score: float = Field(..., ge=0)
    semantic_rank: int | None = None
    keyword_rank: int | None = None
    matched_by: list[Literal["semantic", "keyword"]]

    rerank_score: float | None = Field(
        default=None,
        ge=0,
        le=1,
    )
    rerank_rank: int | None = Field(default=None, ge=1)
    reranked_by: Literal["cohere"] | None = None


class HybridSearchResponse(BaseModel):
    project_id: int
    query: str
    search_type: Literal["hybrid_reranked"] = "hybrid_reranked"
    results: list[HybridSearchResult]
    total: int = Field(..., ge=0)


class ConversationMessage(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    role: Literal["user", "assistant"]
    content: str = Field(
        ...,
        min_length=1,
        max_length=4000,
    )


class AskRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    question: str = Field(
        ...,
        min_length=2,
        max_length=4000,
    )
    limit: int = Field(default=5, ge=1, le=20)
    semantic_limit: int = Field(default=20, ge=1, le=100)
    keyword_limit: int = Field(default=20, ge=1, le=100)
    rrf_k: int = Field(default=60, ge=1, le=200)

    rerank: bool = True
    rerank_candidates: int = Field(default=30, ge=1, le=100)

    rewrite_query: bool = True
    conversation_history: list[ConversationMessage] = Field(
        default_factory=list,
        max_length=20,
    )


class AskResponse(BaseModel):
    project_id: int
    question: str
    search_query: str | None = None
    answer: str
    sources: list[HybridSearchResult]
