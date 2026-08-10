import logging
import re

import requests

from ..LLMEnums import GeminiEnums
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


class GeminiProvider(LLMInterface):
    PROVIDER_NAME = "GEMINI"

    def __init__(
        self,
        api_key: str,
        api_url: str = "https://generativelanguage.googleapis.com/v1beta",
        default_input_max_characters: int = 1000,
        default_generation_max_output_tokens: int = 1000,
        default_generation_temperature: float = 0.1,
        timeout: int = 60,
    ):
        self.api_key = api_key
        self.api_url = (
            api_url.rstrip("/")
            if api_url
            else "https://generativelanguage.googleapis.com/v1beta"
        )
        self.default_input_max_characters = default_input_max_characters
        self.default_generation_max_output_tokens = (
            default_generation_max_output_tokens
        )
        self.default_generation_temperature = default_generation_temperature
        self.timeout = timeout
        self.generation_model_id = None
        self.embedding_model_id = None
        self.embedding_size = None
        self.enums = GeminiEnums
        self.logger = logging.getLogger(__name__)

    def set_generation_model(self, model_id: str):
        self.generation_model_id = model_id

    def set_embedding_model(self, model_id: str, embedding_size: int):
        self.embedding_model_id = model_id
        self.embedding_size = embedding_size

    def process_text(self, text: str, max_characters: int | None = None):
        if not text:
            return ""
        limit = max_characters or self.default_input_max_characters
        return str(text)[:limit].strip()

    @staticmethod
    def _retry_after(response: requests.Response, payload: dict | None) -> int | None:
        header = response.headers.get("Retry-After")
        if header:
            try:
                return max(int(float(header)), 0)
            except ValueError:
                pass
        message = str(((payload or {}).get("error") or {}).get("message", ""))
        match = re.search(r"retry\s+in\s+([0-9.]+)s", message, re.IGNORECASE)
        if match:
            return max(int(float(match.group(1))) + 1, 1)
        details = ((payload or {}).get("error") or {}).get("details", [])
        for item in details:
            delay = item.get("retryDelay") if isinstance(item, dict) else None
            if isinstance(delay, str) and delay.endswith("s"):
                try:
                    return max(int(float(delay[:-1])) + 1, 1)
                except ValueError:
                    continue
        return None

    def _raise_for_response(
        self,
        response: requests.Response,
        *,
        operation: str,
    ) -> None:
        if response.status_code == 200:
            return
        try:
            payload = response.json()
        except ValueError:
            payload = {}
        api_message = str(
            (payload.get("error") or {}).get("message")
            or response.text
            or "Gemini request failed"
        )
        safe_message = api_message[:1000]
        self.logger.error(
            "Gemini %s failed. status=%s message=%s",
            operation,
            response.status_code,
            safe_message,
        )
        common = {"provider": self.PROVIDER_NAME, "operation": operation}
        if response.status_code == 401:
            raise LLMAuthenticationError(
                "Gemini API authentication failed. Check the configured API key.",
                **common,
            )
        if response.status_code == 403:
            raise LLMPermissionError(
                "Gemini denied access to the requested model or operation.",
                **common,
            )
        if response.status_code == 404:
            raise LLMModelNotFoundError(
                "The configured Gemini model was not found.",
                **common,
            )
        if response.status_code == 429:
            raise LLMRateLimitError(
                "Gemini quota or rate limit has been exceeded. Try again later or use another generation provider.",
                retry_after_seconds=self._retry_after(response, payload),
                **common,
            )
        raise LLMProviderError(
            "Gemini returned an upstream service error.",
            provider=self.PROVIDER_NAME,
            operation=operation,
            status_code=502,
        )

    def _post(self, url: str, *, operation: str, payload: dict):
        try:
            response = requests.post(
                url,
                params={"key": self.api_key},
                json=payload,
                timeout=self.timeout,
            )
        except requests.Timeout as exc:
            raise LLMTimeoutError(
                "Gemini request timed out.",
                provider=self.PROVIDER_NAME,
                operation=operation,
            ) from exc
        except requests.ConnectionError as exc:
            raise LLMConnectionError(
                "Could not connect to Gemini.",
                provider=self.PROVIDER_NAME,
                operation=operation,
            ) from exc
        except requests.RequestException as exc:
            raise LLMProviderError(
                "Gemini request failed before a valid response was received.",
                provider=self.PROVIDER_NAME,
                operation=operation,
                status_code=502,
            ) from exc
        self._raise_for_response(response, operation=operation)
        try:
            return response.json()
        except ValueError as exc:
            raise LLMEmptyResponseError(
                "Gemini returned an invalid JSON response.",
                provider=self.PROVIDER_NAME,
                operation=operation,
            ) from exc

    def generate_text(
        self,
        prompt: str,
        chat_history: list | None = None,
        max_output_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        if not self.api_key:
            raise LLMAuthenticationError(
                "Gemini API key was not configured.",
                provider=self.PROVIDER_NAME,
                operation="generation",
            )
        if not self.generation_model_id:
            raise LLMModelNotFoundError(
                "Gemini generation model was not configured.",
                provider=self.PROVIDER_NAME,
                operation="generation",
            )
        contents = []
        system_instruction = None
        for message in chat_history or []:
            role = message.get("role")
            parts = message.get("parts", [])
            if role == GeminiEnums.SYSTEM.value:
                if parts:
                    system_instruction = {"parts": parts}
                continue
            if role == GeminiEnums.ASSISTANT.value:
                role = GeminiEnums.MODEL.value
            if role not in {GeminiEnums.USER.value, GeminiEnums.MODEL.value}:
                role = GeminiEnums.USER.value
            contents.append({"role": role, "parts": parts})
        contents.append(
            self.construct_prompt(prompt=prompt, role=GeminiEnums.USER.value)
        )
        payload = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": (
                    max_output_tokens
                    if max_output_tokens is not None
                    else self.default_generation_max_output_tokens
                ),
                "temperature": (
                    temperature
                    if temperature is not None
                    else self.default_generation_temperature
                ),
            },
        }
        if system_instruction:
            payload["systemInstruction"] = system_instruction
        data = self._post(
            f"{self.api_url}/{self.generation_model_id}:generateContent",
            operation="generation",
            payload=payload,
        )
        candidates = data.get("candidates") or []
        if not candidates:
            raise LLMEmptyResponseError(
                "Gemini returned no generation candidates.",
                provider=self.PROVIDER_NAME,
                operation="generation",
            )
        parts = (candidates[0].get("content") or {}).get("parts") or []
        answer = "".join(str(part.get("text", "")) for part in parts).strip()
        if not answer:
            raise LLMEmptyResponseError(
                "Gemini returned an empty generation response.",
                provider=self.PROVIDER_NAME,
                operation="generation",
            )
        return answer

    def embed_text(self, text: str, document_type: str | None = None):
        if not self.api_key:
            raise LLMAuthenticationError(
                "Gemini API key was not configured.",
                provider=self.PROVIDER_NAME,
                operation="embedding",
            )
        if not self.embedding_model_id:
            raise LLMModelNotFoundError(
                "Gemini embedding model was not configured.",
                provider=self.PROVIDER_NAME,
                operation="embedding",
            )
        clean_text = self.process_text(text)
        if not clean_text:
            raise ValueError("Cannot embed empty text")
        payload = {
            "model": self.embedding_model_id,
            "content": {"parts": [{"text": clean_text}]},
        }
        task_type = self._get_embedding_task_type(document_type)
        if task_type:
            payload["taskType"] = task_type
        data = self._post(
            f"{self.api_url}/{self.embedding_model_id}:embedContent",
            operation="embedding",
            payload=payload,
        )
        values = (data.get("embedding") or {}).get("values") or []
        if not values:
            raise LLMEmptyResponseError(
                "Gemini returned an empty embedding.",
                provider=self.PROVIDER_NAME,
                operation="embedding",
            )
        if self.embedding_size and len(values) != self.embedding_size:
            raise LLMProviderError(
                "Gemini embedding dimension does not match the configured size.",
                provider=self.PROVIDER_NAME,
                operation="embedding",
                code="embedding_dimension_mismatch",
                status_code=502,
            )
        return values

    def construct_prompt(self, prompt: str, role: str):
        if role == GeminiEnums.ASSISTANT.value:
            role = GeminiEnums.MODEL.value
        return {
            "role": role,
            "parts": [{"text": self.process_text(prompt, 10000)}],
        }

    @staticmethod
    def _get_embedding_task_type(document_type: str | None = None):
        if not document_type:
            return None
        value = str(document_type).lower()
        if value in {"query", "question", "user_query"}:
            return "RETRIEVAL_QUERY"
        if value in {"document", "doc", "chunk", "text"}:
            return "RETRIEVAL_DOCUMENT"
        return None
