from ..LLMInterface import LLMInterface
from ..LLMEnums import CoHereEnums, DocumentTypeEnum
import cohere
import logging
import time

try:
    from cohere.errors import TooManyRequestsError
except Exception:
    TooManyRequestsError = Exception


class CoHereProvider(LLMInterface):

    def __init__(
        self,
        api_key: str,
        default_input_max_characters: int = 1000,
        default_generation_max_output_tokens: int = 1000,
        default_generation_temperature: float = 0.1
    ):
        self.api_key = api_key

        self.default_input_max_characters = default_input_max_characters
        self.default_generation_max_output_tokens = default_generation_max_output_tokens
        self.default_generation_temperature = default_generation_temperature

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
        return text[:self.default_input_max_characters].strip()

    def _enum_value(self, value):
        return value.value if hasattr(value, "value") else value

    def _get_input_type(self, document_type: str = None):
        """
        Cohere embeddings should use:
        - search_document for indexed document chunks
        - search_query for user questions
        This method supports enum objects and raw string values.
        """
        query_value = self._enum_value(DocumentTypeEnum.QUERY)
        document_value = self._enum_value(DocumentTypeEnum.DOCUMENT)

        if document_type == query_value:
            return self._enum_value(CoHereEnums.QUERY)

        if document_type == document_value:
            return self._enum_value(CoHereEnums.DOCUMENT)

        return self._enum_value(CoHereEnums.DOCUMENT)

    def generate_text(
        self,
        prompt: str,
        chat_history: list = None,
        max_output_tokens: int = None,
        temperature: float = None
    ):
        if not self.client:
            self.logger.error("CoHere client was not set")
            return None

        if not self.generation_model_id:
            self.logger.error("Generation model for CoHere was not set")
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

        try:
            response = self.client.chat(
                model=self.generation_model_id,
                chat_history=chat_history,
                message=self.process_text(prompt),
                temperature=temperature,
                max_tokens=max_output_tokens
            )
        except Exception as e:
            self.logger.error(f"Error while generating text with CoHere: {e}")
            return None

        if not response or not response.text:
            self.logger.error("Error while generating text with CoHere")
            return None

        return response.text

    def embed_text(self, text: str, document_type: str = None):
        embeddings = self.embed_texts(
            texts=[text],
            document_type=document_type,
            batch_size=1
        )

        if not embeddings:
            return None

        return embeddings[0]

    def embed_texts(self, texts: list, document_type: str = None, batch_size: int = 50):
        """
        Batch embedding to reduce Cohere API calls.
        This helps avoid Trial-key 429 errors because many chunks are sent in fewer API requests.
        """
        if not self.client:
            self.logger.error("CoHere client was not set")
            return None

        if not self.embedding_model_id:
            self.logger.error("Embedding model for CoHere was not set")
            return None

        if not texts:
            return []

        input_type = self._get_input_type(document_type=document_type)
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            original_batch = texts[i:i + batch_size]
            batch = [self.process_text(text) for text in original_batch]

            # Keep only non-empty texts. If any text is empty, return None to avoid vector/text mismatch.
            if any(not text for text in batch):
                self.logger.error("Cannot embed empty text inside batch")
                return None

            for attempt in range(3):
                try:
                    response = self.client.embed(
                        model=self.embedding_model_id,
                        texts=batch,
                        input_type=input_type,
                        embedding_types=["float"],
                    )

                    if not response or not response.embeddings or not response.embeddings.float:
                        self.logger.error("Error while embedding batch with CoHere")
                        return None

                    all_embeddings.extend(response.embeddings.float)
                    break

                except TooManyRequestsError:
                    wait_time = 200
                    self.logger.warning(
                        f"Cohere rate limit reached. Waiting {wait_time} seconds before retrying..."
                    )
                    time.sleep(wait_time)

                except Exception as e:
                    self.logger.error(f"Error while embedding batch with CoHere: {e}")
                    return None
            else:
                return None

        return all_embeddings

    def construct_prompt(self, prompt: str, role: str):
        return {
            "role": role,
            "text": self.process_text(prompt)
        }
