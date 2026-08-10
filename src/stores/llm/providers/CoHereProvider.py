import logging
import re
import time

import cohere

from ..LLMEnums import CoHereEnums, DocumentTypeEnum
from ..LLMExceptions import (
    LLMAuthenticationError,
    LLMConnectionError,
    LLMEmptyResponseError,
    LLMModelNotFoundError,
    LLMPermissionError,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from ..LLMInterface import LLMInterface


class CoHereProvider(LLMInterface):
    PROVIDER_NAME = "COHERE"

    def __init__(
        self,
        api_key: str,
        default_input_max_characters: int = 1000,
        default_generation_max_output_tokens: int = 1000,
        default_generation_temperature: float = 0.1,
        max_retries: int = 2,
        retry_base_seconds: int = 2,
    ):
        self.api_key = api_key
        self.default_input_max_characters = default_input_max_characters
        self.default_generation_max_output_tokens = (
            default_generation_max_output_tokens
        )
        self.default_generation_temperature = default_generation_temperature
        self.max_retries = max(int(max_retries), 0)
        self.retry_base_seconds = max(int(retry_base_seconds), 1)
        self.generation_model_id = None
        self.embedding_model_id = None
        self.embedding_size = None
        self.client = cohere.Client(api_key=self.api_key)
        self.enums = CoHereEnums
        self.logger = logging.getLogger(__name__)

    def set_generation_model(self, model_id: str):
        self.generation_model_id = model_id

    def set_embedding_model(self, model_id: str, embedding_size: int):
        self.embedding_model_id = model_id
        self.embedding_size = embedding_size

    def process_text(self, text: str):
        if not text:
            return ""
        return str(text)[:self.default_input_max_characters].strip()

    @staticmethod
    def _enum_value(value):
        return value.value if hasattr(value, "value") else value

    def _get_input_type(self, document_type: str | None = None):
        query_value = self._enum_value(DocumentTypeEnum.QUERY)
        document_value = self._enum_value(DocumentTypeEnum.DOCUMENT)
        if document_type == query_value:
            return self._enum_value(CoHereEnums.QUERY)
        if document_type == document_value:
            return self._enum_value(CoHereEnums.DOCUMENT)
        return self._enum_value(CoHereEnums.DOCUMENT)

    @staticmethod
    def _status_code(exc: Exception) -> int | None:
        for name in ("status_code", "http_status", "status"):
            value = getattr(exc, name, None)
            if isinstance(value, int):
                return value
        response = getattr(exc, "response", None)
        value = getattr(response, "status_code", None)
        return value if isinstance(value, int) else None

    @staticmethod
    def _retry_after(exc: Exception) -> int | None:
        response = getattr(exc, "response", None)
        headers = getattr(response, "headers", {}) or {}
        value = headers.get("Retry-After") if hasattr(headers, "get") else None
        if value:
            try:
                return max(int(float(value)), 0)
            except ValueError:
                pass
        match = re.search(
            r"retry(?:ing)?(?:\s+after|\s+in)?\s+([0-9.]+)",
            str(exc),
            re.IGNORECASE,
        )
        if match:
            return max(int(float(match.group(1))) + 1, 1)
        return None

    def _translate_exception(self, exc: Exception, operation: str):
        status_code = self._status_code(exc)
        common = {"provider": self.PROVIDER_NAME, "operation": operation}
        if status_code == 401:
            return LLMAuthenticationError(
                "Cohere API authentication failed. Check the configured API key.",
                **common,
            )
        if status_code == 403:
            return LLMPermissionError(
                "Cohere denied access to the requested model or operation.",
                **common,
            )
        if status_code == 404:
            return LLMModelNotFoundError(
                "The configured Cohere model was not found.",
                **common,
            )
        if status_code == 429 or "too many" in str(exc).lower() or "rate limit" in str(exc).lower():
            return LLMRateLimitError(
                "Cohere quota or rate limit has been exceeded. Try again later or use another provider.",
                retry_after_seconds=self._retry_after(exc),
                **common,
            )
        if isinstance(exc, TimeoutError) or "timeout" in str(exc).lower():
            return LLMTimeoutError(
                "Cohere request timed out.",
                **common,
            )
        if "connection" in str(exc).lower():
            return LLMConnectionError(
                "Could not connect to Cohere.",
                **common,
            )
        return LLMProviderError(
            "Cohere returned an upstream service error.",
            provider=self.PROVIDER_NAME,
            operation=operation,
            status_code=502,
        )

    @staticmethod
    def _extract_chat_text(response) -> str:
        text = getattr(response, "text", None)
        if text:
            return str(text).strip()
        message = getattr(response, "message", None)
        content = getattr(message, "content", None)
        if content:
            parts = []
            for item in content:
                value = getattr(item, "text", None)
                if value:
                    parts.append(str(value))
                elif isinstance(item, dict) and item.get("text"):
                    parts.append(str(item["text"]))
            return "".join(parts).strip()
        return ""

    @staticmethod
    def _extract_float_embeddings(response) -> list[list[float]]:
        embeddings = getattr(response, "embeddings", None)
        if embeddings is None:
            return []
        float_embeddings = getattr(embeddings, "float", None)
        if float_embeddings is not None:
            return [list(map(float, vector)) for vector in float_embeddings]
        if isinstance(embeddings, list):
            return [list(map(float, vector)) for vector in embeddings]
        if isinstance(embeddings, dict):
            values = embeddings.get("float") or []
            return [list(map(float, vector)) for vector in values]
        return []

    def generate_text(
        self,
        prompt: str,
        chat_history: list | None = None,
        max_output_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        if not self.api_key:
            raise LLMAuthenticationError(
                "Cohere API key was not configured.",
                provider=self.PROVIDER_NAME,
                operation="generation",
            )
        if not self.generation_model_id:
            raise LLMModelNotFoundError(
                "Cohere generation model was not configured.",
                provider=self.PROVIDER_NAME,
                operation="generation",
            )
        clean_prompt = self.process_text(prompt)
        if not clean_prompt:
            raise ValueError("Generation prompt cannot be empty")
        try:
            response = self.client.chat(
                model=self.generation_model_id,
                chat_history=chat_history or [],
                message=clean_prompt,
                temperature=(
                    temperature
                    if temperature is not None
                    else self.default_generation_temperature
                ),
                max_tokens=(
                    max_output_tokens
                    if max_output_tokens is not None
                    else self.default_generation_max_output_tokens
                ),
            )
        except Exception as exc:
            self.logger.exception("Cohere generation failed")
            raise self._translate_exception(exc, "generation") from exc
        answer = self._extract_chat_text(response)
        if not answer:
            raise LLMEmptyResponseError(
                "Cohere returned an empty generation response.",
                provider=self.PROVIDER_NAME,
                operation="generation",
            )
        return answer

    def embed_text(self, text: str, document_type: str | None = None):
        embeddings = self.embed_texts(
            texts=[text],
            document_type=document_type,
            batch_size=1,
        )
        return embeddings[0]

    def embed_texts(
        self,
        texts: list,
        document_type: str | None = None,
        batch_size: int = 50,
    ) -> list[list[float]]:
        if not self.api_key:
            raise LLMAuthenticationError(
                "Cohere API key was not configured.",
                provider=self.PROVIDER_NAME,
                operation="embedding",
            )
        if not self.embedding_model_id:
            raise LLMModelNotFoundError(
                "Cohere embedding model was not configured.",
                provider=self.PROVIDER_NAME,
                operation="embedding",
            )
        if not texts:
            return []
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")
        input_type = self._get_input_type(document_type=document_type)
        all_embeddings: list[list[float]] = []
        for start in range(0, len(texts), batch_size):
            batch = [self.process_text(text) for text in texts[start:start + batch_size]]
            if any(not text for text in batch):
                raise ValueError("Cannot embed empty text inside a batch")
            last_error = None
            for attempt in range(self.max_retries + 1):
                try:
                    response = self.client.embed(
                        model=self.embedding_model_id,
                        texts=batch,
                        input_type=input_type,
                        embedding_types=["float"],
                    )
                    vectors = self._extract_float_embeddings(response)
                    if len(vectors) != len(batch):
                        raise LLMEmptyResponseError(
                            "Cohere returned an unexpected embedding count.",
                            provider=self.PROVIDER_NAME,
                            operation="embedding",
                        )
                    if self.embedding_size:
                        invalid = [len(vector) for vector in vectors if len(vector) != self.embedding_size]
                        if invalid:
                            raise LLMProviderError(
                                "Cohere embedding dimension does not match the configured size.",
                                provider=self.PROVIDER_NAME,
                                operation="embedding",
                                code="embedding_dimension_mismatch",
                                status_code=502,
                            )
                    all_embeddings.extend(vectors)
                    last_error = None
                    break
                except LLMProviderError:
                    raise
                except Exception as exc:
                    translated = self._translate_exception(exc, "embedding")
                    last_error = translated
                    if not isinstance(translated, LLMRateLimitError) or attempt >= self.max_retries:
                        self.logger.exception("Cohere embedding failed")
                        raise translated from exc
                    wait_time = translated.retry_after_seconds or (
                        self.retry_base_seconds * (2 ** attempt)
                    )
                    self.logger.warning(
                        "Cohere embedding rate limited. retry=%s wait=%ss",
                        attempt + 1,
                        wait_time,
                    )
                    time.sleep(min(wait_time, 30))
            if last_error is not None:
                raise last_error
        return all_embeddings

    def construct_prompt(self, prompt: str, role: str):
        return {
            "role": role,
            "text": self.process_text(prompt),
        }
