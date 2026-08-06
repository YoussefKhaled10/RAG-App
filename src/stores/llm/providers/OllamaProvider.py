from ..LLMInterface import LLMInterface
from ..LLMEnums import OllamaEnums
import requests
import time
import logging


class OllamaProvider(LLMInterface):

    def __init__(
        self,
        api_url: str,
        default_input_max_characters: int = 1000,
        default_generation_max_output_tokens: int = 1000,
        default_generation_temperature: float = 0.1,
        timeout: int = 120
    ):
        self.api_url = api_url.rstrip("/")

        self.default_input_max_characters = default_input_max_characters
        self.default_generation_max_output_tokens = default_generation_max_output_tokens
        self.default_generation_temperature = default_generation_temperature
        self.timeout = timeout

        self.generation_model_id = None
        self.embedding_model_id = None
        self.embedding_size = None

        self.enums = OllamaEnums
        self.logger = logging.getLogger(__name__)

        self.headers = {
            "Content-Type": "application/json",
            "ngrok-skip-browser-warning": "true"
        }

    def set_generation_model(self, model_id: str):
        self.generation_model_id = model_id

    def set_embedding_model(self, model_id: str, embedding_size: int):
        self.embedding_model_id = model_id
        self.embedding_size = embedding_size

    def process_text(self, text: str, max_characters: int = None):
        if not text:
            return ""

        limit = max_characters or self.default_input_max_characters
        return text[:limit].strip()

    def generate_text(
        self,
        prompt: str,
        chat_history: list = None,
        max_output_tokens: int = None,
        temperature: float = None
    ):
        if not self.api_url:
            self.logger.error("Ollama API URL was not set")
            return None

        if not self.generation_model_id:
            self.logger.error("Generation model for Ollama was not set")
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

        messages = []

        for message in chat_history:
            role = message.get("role")
            content = message.get("content")

            if content is None and "text" in message:
                content = message.get("text")

            if content is None and "parts" in message:
                parts = message.get("parts", [])
                if parts and isinstance(parts, list):
                    content = parts[0].get("text", "")

            if role not in [
                OllamaEnums.SYSTEM.value,
                OllamaEnums.USER.value,
                OllamaEnums.ASSISTANT.value
            ]:
                role = OllamaEnums.USER.value

            messages.append({
                "role": role,
                "content": self.process_text(content)
            })

        messages.append(
            self.construct_prompt(
                prompt=prompt,
                role=OllamaEnums.USER.value
            )
        )

        url = f"{self.api_url}/api/chat"

        payload = {
            "model": self.generation_model_id,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_output_tokens
            }
        }

        try:
            response = requests.post(
                url,
                json=payload,
                headers=self.headers,
                timeout=self.timeout
            )

            if response.status_code != 200:
                self.logger.error(
                    f"Error while generating text with Ollama: "
                    f"{response.status_code} - {response.text}"
                )
                return None

            data = response.json()

            if "message" in data and data["message"].get("content"):
                return data["message"]["content"]

            if "response" in data:
                return data["response"]

            self.logger.error("Ollama returned empty generation response")
            return None

        except Exception as e:
            self.logger.error(f"Exception while generating text with Ollama: {e}")
            return None

    def embed_text(self, text: str, document_type: str = None):
            embeddings = self.embed_texts(
                texts=[text],
                document_type=document_type,
                batch_size=1
            )

            if not embeddings:
                return None

            return embeddings[0]

    def embed_texts(self, texts: list, document_type: str = None, batch_size: int = 5):
        all_vectors = []

        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]

            last_error = None

            for attempt in range(1, 6):
                try:
                    response = requests.post(
                        f"{self.api_url}/api/embed",
                        json={
                            "model": self.embedding_model_id,
                            "input": batch_texts
                        },
                        timeout=240
                    )

                    response.raise_for_status()

                    data = response.json()
                    vectors = data.get("embeddings", [])

                    if not vectors:
                        raise Exception("Ollama returned empty embeddings")

                    all_vectors.extend(vectors)

                    time.sleep(1)
                    break

                except Exception as e:
                    last_error = e
                    wait_time = min(10 * attempt, 60)

                    self.logger.error(
                        f"Ollama embedding batch failed. "
                        f"attempt={attempt}, wait={wait_time}s, error={e}"
                    )

                    time.sleep(wait_time)

            else:
                self.logger.error(
                    f"Ollama embedding failed after retries. Last error: {last_error}"
                )
                return None

        return all_vectors

    def construct_prompt(self, prompt: str, role: str):
        if role not in [
            OllamaEnums.SYSTEM.value,
            OllamaEnums.USER.value,
            OllamaEnums.ASSISTANT.value
        ]:
            role = OllamaEnums.USER.value

        return {
            "role": role,
            "content": self.process_text(prompt, max_characters=10000)
        }