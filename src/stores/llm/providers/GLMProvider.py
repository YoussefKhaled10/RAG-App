import logging
import time

import requests

from ..LLMEnums import GLMEnums
from ..LLMInterface import LLMInterface


class GLMProvider(LLMInterface):
    def __init__(
        self,
        api_key: str,
        api_url: str = "https://api.z.ai/api/paas/v4",
        default_input_max_characters: int = 10000,
        default_generation_max_output_tokens: int = 1000,
        default_generation_temperature: float = 0.1,
        timeout: int = 120,
    ):
        self.api_key = api_key
        self.api_url = api_url.rstrip("/")
        self.default_input_max_characters = (
            default_input_max_characters
        )
        self.default_generation_max_output_tokens = (
            default_generation_max_output_tokens
        )
        self.default_generation_temperature = (
            default_generation_temperature
        )
        self.timeout = timeout

        self.generation_model_id: str | None = None
        self.embedding_model_id: str | None = None
        self.embedding_size: int | None = None
        self.enums = GLMEnums
        self.logger = logging.getLogger(__name__)

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept-Language": "en-US,en",
        }

    def set_generation_model(
        self,
        model_id: str,
    ) -> None:
        self.generation_model_id = model_id

    def set_embedding_model(
        self,
        model_id: str,
        embedding_size: int,
    ) -> None:
        self.embedding_model_id = model_id
        self.embedding_size = embedding_size

    def process_text(
        self,
        text: str | None,
        max_characters: int | None = None,
    ) -> str:
        if not text:
            return ""

        limit = (
            max_characters
            or self.default_input_max_characters
        )
        return str(text)[:limit].strip()

    def generate_text(
        self,
        prompt: str,
        chat_history: list | None = None,
        max_output_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str | None:
        if not self.api_key:
            self.logger.error("GLM API key was not set")
            return None

        if not self.generation_model_id:
            self.logger.error(
                "Generation model for GLM was not set"
            )
            return None

        messages: list[dict] = []
        for message in chat_history or []:
            role = message.get("role", GLMEnums.USER.value)
            content = message.get("content")

            if content is None and "text" in message:
                content = message.get("text")

            if role not in {
                GLMEnums.SYSTEM.value,
                GLMEnums.USER.value,
                GLMEnums.ASSISTANT.value,
            }:
                role = GLMEnums.USER.value

            clean_content = self.process_text(content)
            if clean_content:
                messages.append(
                    {
                        "role": role,
                        "content": clean_content,
                    }
                )

        messages.append(
            self.construct_prompt(
                prompt=prompt,
                role=GLMEnums.USER.value,
            )
        )

        payload = {
            "model": self.generation_model_id,
            "messages": messages,
            "stream": False,
            "max_tokens": (
                max_output_tokens
                if max_output_tokens is not None
                else self.default_generation_max_output_tokens
            ),
            "temperature": (
                temperature
                if temperature is not None
                else self.default_generation_temperature
            ),
        }

        try:
            response = requests.post(
                f"{self.api_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

            choices = data.get("choices", [])
            if not choices:
                raise RuntimeError(
                    "GLM returned no generation choices"
                )

            content = (
                choices[0]
                .get("message", {})
                .get("content")
            )
            return content.strip() if content else None

        except Exception as exc:
            self.logger.error(
                "GLM generation failed: %s",
                exc,
            )
            return None

    def embed_text(
        self,
        text: str,
        document_type: str | None = None,
    ) -> list[float] | None:
        vectors = self.embed_texts(
            texts=[text],
            document_type=document_type,
            batch_size=1,
        )
        return vectors[0] if vectors else None

    def embed_texts(
        self,
        texts: list[str],
        document_type: str | None = None,
        batch_size: int = 5,
    ) -> list[list[float]] | None:
        if not self.api_key:
            self.logger.error("GLM API key was not set")
            return None

        if not self.embedding_model_id:
            self.logger.error(
                "Embedding model for GLM was not set"
            )
            return None

        if batch_size <= 0:
            raise ValueError("batch_size must be positive")

        clean_texts = [
            self.process_text(text)
            for text in texts
            if self.process_text(text)
        ]
        if not clean_texts:
            return []

        all_vectors: list[list[float]] = []

        for start in range(0, len(clean_texts), batch_size):
            batch = clean_texts[start:start + batch_size]
            last_error: Exception | None = None

            for attempt in range(1, 4):
                try:
                    response = requests.post(
                        f"{self.api_url}/embeddings",
                        headers=self.headers,
                        json={
                            "model": self.embedding_model_id,
                            "input": batch,
                        },
                        timeout=self.timeout,
                    )
                    response.raise_for_status()
                    data = response.json().get("data", [])

                    ordered_items = sorted(
                        data,
                        key=lambda item: item.get("index", 0),
                    )
                    vectors = [
                        item.get("embedding", [])
                        for item in ordered_items
                    ]

                    if len(vectors) != len(batch):
                        raise RuntimeError(
                            "GLM embeddings count does not "
                            "match input count"
                        )

                    if any(not vector for vector in vectors):
                        raise RuntimeError(
                            "GLM returned an empty embedding"
                        )

                    if self.embedding_size is not None:
                        invalid_sizes = [
                            len(vector)
                            for vector in vectors
                            if len(vector) != self.embedding_size
                        ]
                        if invalid_sizes:
                            raise RuntimeError(
                                "GLM embedding dimension does "
                                "not match configured size"
                            )

                    all_vectors.extend(vectors)
                    break

                except Exception as exc:
                    last_error = exc
                    if attempt == 3:
                        break
                    wait_seconds = 2 ** attempt
                    self.logger.warning(
                        "GLM embedding retry. attempt=%s "
                        "wait=%ss error=%s",
                        attempt,
                        wait_seconds,
                        exc,
                    )
                    time.sleep(wait_seconds)
            else:
                pass

            if last_error is not None and len(
                all_vectors
            ) < min(start + len(batch), len(clean_texts)):
                self.logger.error(
                    "GLM embedding failed: %s",
                    last_error,
                )
                return None

        return all_vectors

    def construct_prompt(
        self,
        prompt: str,
        role: str,
    ) -> dict:
        if role not in {
            GLMEnums.SYSTEM.value,
            GLMEnums.USER.value,
            GLMEnums.ASSISTANT.value,
        }:
            role = GLMEnums.USER.value

        return {
            "role": role,
            "content": self.process_text(
                prompt,
                max_characters=10000,
            ),
        }
