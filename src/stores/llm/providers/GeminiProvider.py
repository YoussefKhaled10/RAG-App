from ..LLMInterface import LLMInterface
from ..LLMEnums import GeminiEnums

import requests
import logging

class GeminiProvider(LLMInterface):

    def __init__(
        self,
        api_key: str,
        api_url: str = "https://generativelanguage.googleapis.com/v1beta",
        default_input_max_characters: int = 1000,
        default_generation_max_output_tokens: int = 1000,
        default_generation_temperature: float = 0.1
    ):
        self.api_key = api_key
        self.api_url = api_url.rstrip("/") if api_url else "https://generativelanguage.googleapis.com/v1beta"

        self.default_input_max_characters = default_input_max_characters
        self.default_generation_max_output_tokens = default_generation_max_output_tokens
        self.default_generation_temperature = default_generation_temperature

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

    def process_text(self, text: str):
        if not text:
            return ""

        return text[:self.default_input_max_characters].strip()

    def generate_text(
        self,
        prompt: str,
        chat_history: list = None,
        max_output_tokens: int = None,
        temperature: float = None
    ):

        if not self.api_key:
            self.logger.error("Gemini API key was not set")
            return None

        if not self.generation_model_id:
            self.logger.error("Generation model for Gemini was not set")
            return None

        if chat_history is None:
            chat_history = []

        max_output_tokens = (
            max_output_tokens
            if max_output_tokens is not None
            else self.default_generation_max_output_tokens
        )

        temperature = (
            temperature
            if temperature is not None
            else self.default_generation_temperature
        )

        contents = []
        system_instruction = None

        for message in chat_history:
            role = message.get("role")

            if role == GeminiEnums.SYSTEM.value:
                parts = message.get("parts", [])
                if parts and "text" in parts[0]:
                    system_instruction = {
                        "parts": [
                            {
                                "text": parts[0]["text"]
                            }
                        ]
                    }
                continue

            if role == GeminiEnums.ASSISTANT.value:
                role = GeminiEnums.MODEL.value

            if role not in [GeminiEnums.USER.value, GeminiEnums.MODEL.value]:
                role = GeminiEnums.USER.value

            contents.append({
                "role": role,
                "parts": message.get("parts", [])
            })

        contents.append(
            self.construct_prompt(
                prompt=prompt,
                role=GeminiEnums.USER.value
            )
        )

        url = f"{self.api_url}/{self.generation_model_id}:generateContent"

        payload = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": max_output_tokens,
                "temperature": temperature
            }
        }

        if system_instruction:
            payload["systemInstruction"] = system_instruction

        try:
            response = requests.post(
                url,
                params={"key": self.api_key},
                json=payload,
                timeout=60
            )

            if response.status_code != 200:
                self.logger.error(
                    f"Error while generating text with Gemini: "
                    f"{response.status_code} - {response.text}"
                )
                return None

            data = response.json()

            candidates = data.get("candidates", [])

            if not candidates:
                self.logger.error("Gemini returned no candidates")
                return None

            content = candidates[0].get("content", {})
            parts = content.get("parts", [])

            if not parts:
                self.logger.error("Gemini returned no content parts")
                return None

            return parts[0].get("text")

        except Exception as e:
            self.logger.error(f"Exception while generating text with Gemini: {str(e)}")
            return None

    def embed_text(self, text: str, document_type: str = None):

        if not self.api_key:
            self.logger.error("Gemini API key was not set")
            return None

        if not self.embedding_model_id:
            self.logger.error("Embedding model for Gemini was not set")
            return None

        text = self.process_text(text)

        if not text:
            self.logger.error("Cannot embed empty text")
            return None

        url = f"{self.api_url}/{self.embedding_model_id}:embedContent"

        task_type = self._get_embedding_task_type(document_type=document_type)

        payload = {
            "model": self.embedding_model_id,
            "content": {
                "parts": [
                    {
                        "text": text
                    }
                ]
            }
        }

        if task_type:
            payload["taskType"] = task_type

        try:
            response = requests.post(
                url,
                params={"key": self.api_key},
                json=payload,
                timeout=60
            )

            if response.status_code != 200:
                self.logger.error(
                    f"Error while embedding text with Gemini: "
                    f"{response.status_code} - {response.text}"
                )
                return None

            data = response.json()

            embedding = data.get("embedding", {})
            values = embedding.get("values", [])

            if not values:
                self.logger.error("Gemini returned empty embedding")
                return None

            return values

        except Exception as e:
            self.logger.error(f"Exception while embedding text with Gemini: {str(e)}")
            return None

    def construct_prompt(self, prompt: str, role: str):
        if role == GeminiEnums.ASSISTANT.value:
            role = GeminiEnums.MODEL.value

        return {
            "role": role,
            "parts": [
                {
                    "text": self.process_text(prompt)
                }
            ]
        }

    def _get_embedding_task_type(self, document_type: str = None):
        if not document_type:
            return None

        document_type = document_type.lower()

        if document_type in ["query", "question", "user_query"]:
            return "RETRIEVAL_QUERY"

        if document_type in ["document", "doc", "chunk", "text"]:
            return "RETRIEVAL_DOCUMENT"

        return None