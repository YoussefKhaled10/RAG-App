from abc import ABC, abstractmethod
from typing import Any


class VectorDBInterface(ABC):
    @abstractmethod
    def connect(self) -> Any:
        raise NotImplementedError

    @abstractmethod
    def disconnect(self) -> Any:
        raise NotImplementedError

    @abstractmethod
    def is_collection_existed(
        self,
        collection_name: str,
    ) -> Any:
        raise NotImplementedError

    @abstractmethod
    def list_all_collections(self) -> Any:
        raise NotImplementedError

    @abstractmethod
    def get_collection_info(
        self,
        collection_name: str,
    ) -> Any:
        raise NotImplementedError

    @abstractmethod
    def delete_collection(
        self,
        collection_name: str,
    ) -> Any:
        raise NotImplementedError

    @abstractmethod
    def create_collection(
        self,
        collection_name: str,
        embedding_size: int,
        do_reset: bool = False,
    ) -> Any:
        raise NotImplementedError

    @abstractmethod
    def insert_one(
        self,
        collection_name: str,
        text: str,
        vector: list[float],
        metadata: dict | None = None,
        record_id: int | str | None = None,
    ) -> Any:
        raise NotImplementedError

    @abstractmethod
    def insert_many(
        self,
        collection_name: str,
        texts: list[str],
        vectors: list[list[float]],
        metadata: list[dict | None] | None = None,
        record_ids: list[int | str] | None = None,
        batch_size: int = 50,
    ) -> Any:
        raise NotImplementedError

    @abstractmethod
    def search_by_vector(
        self,
        collection_name: str,
        vector: list[float],
        limit: int = 5,
    ) -> Any:
        raise NotImplementedError

    @abstractmethod
    def delete_by_ids(
        self,
        collection_name: str,
        record_ids: list[int | str],
    ) -> Any:
        raise NotImplementedError
