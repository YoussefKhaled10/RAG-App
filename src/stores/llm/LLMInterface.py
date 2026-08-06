from abc import ABC, abstractmethod
class LLMInterface(ABC):
    @abstractmethod
    def set_generation_model(
        self,
        model_id: str,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def set_embedding_model(
        self,
        model_id: str,
        embedding_size: int,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def generate_text(
        self,
        prompt: str,
        chat_history: list | None = None,
        max_output_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str | None:
        raise NotImplementedError

    @abstractmethod
    def embed_text(
        self,
        text: str,
        document_type: str | None = None,
    ) -> list[float] | None:
        raise NotImplementedError

    def embed_texts(
        self,
        texts: list[str],
        document_type: str | None = None,
        batch_size: int = 5,
    ) -> list[list[float]] | None:
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")

        vectors: list[list[float]] = []
        for text in texts:
            vector = self.embed_text(
                text=text,
                document_type=document_type,
            )
            if vector is None:
                return None
            vectors.append(vector)

        return vectors

    @abstractmethod
    def construct_prompt(
        self,
        prompt: str,
        role: str,
    ) -> dict:
        raise NotImplementedError
