import asyncio
import inspect
import logging
import os
import re
from typing import Any


class QueryRewriter:
    """Rewrite follow-up questions into standalone retrieval queries."""

    def __init__(
        self,
        generation_client: Any,
        *,
        enabled: bool = True,
        max_history_messages: int = 6,
        max_query_characters: int = 2000,
        fallback_to_original: bool = True,
    ) -> None:
        self.generation_client = generation_client
        self.enabled = bool(enabled)
        self.max_history_messages = min(
            max(int(max_history_messages), 0),
            20,
        )
        self.max_query_characters = min(
            max(int(max_query_characters), 50),
            4000,
        )
        self.fallback_to_original = bool(fallback_to_original)
        self.logger = logging.getLogger(__name__)

    @classmethod
    def from_environment(
        cls,
        generation_client: Any,
    ) -> "QueryRewriter":
        return cls(
            generation_client=generation_client,
            enabled=(
                os.getenv("QUERY_REWRITE_ENABLED", "true")
                .strip()
                .lower()
                in {"1", "true", "yes", "on"}
            ),
            max_history_messages=int(
                os.getenv("QUERY_REWRITE_MAX_HISTORY", "6")
            ),
            max_query_characters=int(
                os.getenv("QUERY_REWRITE_MAX_CHARACTERS", "2000")
            ),
            fallback_to_original=(
                os.getenv("QUERY_REWRITE_FALLBACK", "true")
                .strip()
                .lower()
                in {"1", "true", "yes", "on"}
            ),
        )

    @staticmethod
    def _clean_text(value: Any) -> str:
        text = str(value or "").replace("\x00", "")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _normalize_history(
        self,
        history: list[Any] | None,
    ) -> list[dict[str, str]]:
        if not history or self.max_history_messages == 0:
            return []

        normalized: list[dict[str, str]] = []
        for raw_message in history[-self.max_history_messages:]:
            if hasattr(raw_message, "model_dump"):
                message = raw_message.model_dump()
            elif isinstance(raw_message, dict):
                message = raw_message
            else:
                continue

            role = self._clean_text(message.get("role")).lower()
            content = self._clean_text(message.get("content"))
            if role not in {"user", "assistant"} or not content:
                continue

            normalized.append(
                {
                    "role": role,
                    "content": content[:4000],
                }
            )
        return normalized

    @staticmethod
    def _format_history(history: list[dict[str, str]]) -> str:
        if not history:
            return "No previous conversation is available."

        labels = {
            "user": "User",
            "assistant": "Assistant",
        }
        return "\n".join(
            f"{labels[message['role']]}: {message['content']}"
            for message in history
        )

    @staticmethod
    def _system_prompt() -> str:
        return (
            "You rewrite document-search questions for a retrieval system. "
            "Return exactly one standalone search query and nothing else. "
            "Use conversation history only to resolve references, pronouns, "
            "missing subjects, and follow-up wording. Preserve names, dates, "
            "article numbers, file-specific terms, and the user's language. "
            "Do not answer the question. Do not add facts. Do not use quotes, "
            "labels, Markdown, explanations, or multiple alternatives. If the "
            "question is already standalone, return it with minimal or no change."
        )

    def _user_prompt(
        self,
        question: str,
        history: list[dict[str, str]],
    ) -> str:
        return (
            "Conversation history:\n"
            f"{self._format_history(history)}\n\n"
            "Current question:\n"
            f"{question}\n\n"
            "Standalone retrieval query:"
        )

    def _construct_chat_history(self) -> list[Any]:
        construct_prompt = getattr(
            self.generation_client,
            "construct_prompt",
            None,
        )
        enums = getattr(self.generation_client, "enums", None)
        system_role = getattr(enums, "SYSTEM", None)
        system_role_value = getattr(system_role, "value", None)

        if callable(construct_prompt) and system_role_value:
            return [
                construct_prompt(
                    prompt=self._system_prompt(),
                    role=system_role_value,
                )
            ]
        return []

    async def _generate(self, prompt: str) -> Any:
        generate_text = getattr(
            self.generation_client,
            "generate_text",
            None,
        )
        if not callable(generate_text):
            raise RuntimeError(
                "generation client does not support generate_text"
            )

        result = generate_text(
            prompt=prompt,
            chat_history=self._construct_chat_history(),
        )
        if inspect.isawaitable(result):
            return await result
        return result

    def _sanitize_rewritten_query(
        self,
        value: Any,
        original_question: str,
    ) -> str:
        rewritten = self._clean_text(value)
        rewritten = re.sub(
            r"^```(?:text)?\s*|\s*```$",
            "",
            rewritten,
            flags=re.IGNORECASE,
        ).strip()
        rewritten = re.sub(
            r"^(?:standalone retrieval query|rewritten query|query)\s*:\s*",
            "",
            rewritten,
            flags=re.IGNORECASE,
        ).strip()
        rewritten = rewritten.strip("\"'` ")
        rewritten = rewritten.splitlines()[0].strip()

        if not rewritten:
            raise RuntimeError("query rewriter returned an empty query")
        if len(rewritten) > self.max_query_characters:
            rewritten = rewritten[: self.max_query_characters].rstrip()
        if len(rewritten) < 2:
            return original_question
        return rewritten

    async def rewrite(
        self,
        question: str,
        conversation_history: list[Any] | None = None,
    ) -> str:
        original_question = self._clean_text(question)
        if not original_question:
            raise ValueError("question cannot be empty")
        if not self.enabled:
            return original_question

        history = self._normalize_history(conversation_history)

        # No API call is needed when there is no previous context to resolve.
        if not history:
            return original_question

        try:
            rewritten = await self._generate(
                self._user_prompt(original_question, history)
            )
            return self._sanitize_rewritten_query(
                rewritten,
                original_question,
            )
        except Exception:
            if not self.fallback_to_original:
                raise
            self.logger.exception(
                "Query rewriting failed; using the original question"
            )
            return original_question
