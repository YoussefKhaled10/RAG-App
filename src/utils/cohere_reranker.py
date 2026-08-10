import asyncio
import os
from typing import Any

import requests

from stores.llm.LLMExceptions import (
    LLMAuthenticationError,
    LLMConnectionError,
    LLMEmptyResponseError,
    LLMModelNotFoundError,
    LLMPermissionError,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from helpers.config import get_settings


class CohereReranker:
    PROVIDER_NAME = "COHERE_RERANK"

    def __init__(
        self,
        api_key: str | None = None,
        model_id: str | None = None,
        api_url: str | None = None,
        timeout: int = 45,
        max_documents: int = 100,
    ) -> None:
        self.api_key = (
            api_key
            or os.getenv("RERANK_API_KEY")
            or os.getenv("COHERE_API_KEY")
            or ""
        ).strip()
        self.model_id = (
            model_id
            or os.getenv("RERANK_MODEL_ID")
            or "rerank-v3.5"
        ).strip()
        self.api_url = (
            api_url
            or os.getenv("RERANK_API_URL")
            or "https://api.cohere.com/v2/rerank"
        ).rstrip("/")
        self.timeout = max(int(timeout), 1)
        self.max_documents = min(max(int(max_documents), 1), 1000)

    @classmethod
    def from_environment(cls) -> "CohereReranker":
        settings = get_settings()

        return cls(
            api_key=settings.RERANK_API_KEY,
            model_id=settings.RERANK_MODEL_ID,
            api_url=settings.RERANK_API_URL,
            timeout=settings.RERANK_TIMEOUT_SECONDS,
            max_documents=settings.RERANK_MAX_DOCUMENTS,
        )

    @staticmethod
    def enabled() -> bool:
        settings = get_settings()
        return bool(settings.RERANK_ENABLED)

    def _raise_for_response(self, response: requests.Response) -> None:
        operation = "reranking"
        common = {"provider": self.PROVIDER_NAME, "operation": operation}
        if response.status_code == 200:
            return
        if response.status_code == 401:
            raise LLMAuthenticationError(
                "Cohere Rerank authentication failed. Check RERANK_API_KEY.",
                **common,
            )
        if response.status_code == 403:
            raise LLMPermissionError(
                "Cohere denied access to the configured rerank model.",
                **common,
            )
        if response.status_code == 404:
            raise LLMModelNotFoundError(
                "The configured Cohere rerank model was not found.",
                **common,
            )
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            try:
                retry_seconds = int(float(retry_after)) if retry_after else None
            except ValueError:
                retry_seconds = None
            raise LLMRateLimitError(
                "Cohere Rerank quota or rate limit has been exceeded.",
                retry_after_seconds=retry_seconds,
                **common,
            )
        raise LLMProviderError(
            "Cohere Rerank returned an upstream service error.",
            provider=self.PROVIDER_NAME,
            operation=operation,
            code="rerank_provider_error",
            status_code=502,
        )

    def _request(self, query: str, documents: list[str], top_n: int) -> dict:
        if not self.api_key:
            raise LLMAuthenticationError(
                "RERANK_API_KEY or COHERE_API_KEY was not configured.",
                provider=self.PROVIDER_NAME,
                operation="reranking",
            )
        try:
            response = requests.post(
                self.api_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "X-Client-Name": "nexadocs-rag",
                },
                json={
                    "model": self.model_id,
                    "query": query,
                    "documents": documents,
                    "top_n": top_n,
                    "max_tokens_per_doc": 4096,
                },
                timeout=self.timeout,
            )
        except requests.Timeout as exc:
            raise LLMTimeoutError(
                "Cohere Rerank request timed out.",
                provider=self.PROVIDER_NAME,
                operation="reranking",
            ) from exc
        except requests.ConnectionError as exc:
            raise LLMConnectionError(
                "Could not connect to Cohere Rerank.",
                provider=self.PROVIDER_NAME,
                operation="reranking",
            ) from exc
        except requests.RequestException as exc:
            raise LLMProviderError(
                "Cohere Rerank request failed.",
                provider=self.PROVIDER_NAME,
                operation="reranking",
                code="rerank_request_failed",
                status_code=502,
            ) from exc

        self._raise_for_response(response)
        try:
            return response.json()
        except ValueError as exc:
            raise LLMEmptyResponseError(
                "Cohere Rerank returned invalid JSON.",
                provider=self.PROVIDER_NAME,
                operation="reranking",
            ) from exc

    async def rerank(
        self,
        query: str,
        results: list[dict[str, Any]],
        top_n: int,
    ) -> list[dict[str, Any]]:
        clean_query = str(query or "").strip()
        if not clean_query:
            raise ValueError("rerank query cannot be empty")
        if not results:
            return []

        candidates = [
            dict(item)
            for item in results[: self.max_documents]
            if str(item.get("text") or "").strip()
        ]
        if not candidates:
            return []

        safe_top_n = min(max(int(top_n), 1), len(candidates))
        documents = [str(item["text"]).strip() for item in candidates]
        payload = await asyncio.to_thread(
            self._request,
            clean_query,
            documents,
            safe_top_n,
        )

        api_results = payload.get("results") or []
        if not api_results:
            raise LLMEmptyResponseError(
                "Cohere Rerank returned no ranked results.",
                provider=self.PROVIDER_NAME,
                operation="reranking",
            )

        ranked: list[dict[str, Any]] = []
        seen_indexes: set[int] = set()
        for rank, api_item in enumerate(api_results, start=1):
            try:
                source_index = int(api_item["index"])
                score = float(api_item["relevance_score"])
            except (KeyError, TypeError, ValueError) as exc:
                raise LLMEmptyResponseError(
                    "Cohere Rerank returned an invalid result item.",
                    provider=self.PROVIDER_NAME,
                    operation="reranking",
                ) from exc
            if source_index < 0 or source_index >= len(candidates):
                continue
            if source_index in seen_indexes:
                continue
            seen_indexes.add(source_index)
            item = dict(candidates[source_index])
            item["rerank_score"] = score
            item["rerank_rank"] = rank
            item["reranked_by"] = "cohere"
            ranked.append(item)

        if not ranked:
            raise LLMEmptyResponseError(
                "Cohere Rerank returned no usable ranked results.",
                provider=self.PROVIDER_NAME,
                operation="reranking",
            )
        return ranked
