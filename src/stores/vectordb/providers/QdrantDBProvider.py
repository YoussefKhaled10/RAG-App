import logging
import uuid
from typing import Any

from qdrant_client import QdrantClient, models

from ..VectorDBEnums import DistanceMethodEnums
from ..VectorDBInterface import VectorDBInterface


class QdrantDBProvider(VectorDBInterface):
    def __init__(
        self,
        db_path: str,
        distance_method: str,
        default_vector_size: int = 768,
    ):
        self.client: QdrantClient | None = None
        self.db_path = db_path
        self.default_vector_size = default_vector_size
        self.logger = logging.getLogger(__name__)

        normalized_distance = str(distance_method).lower()
        if normalized_distance == DistanceMethodEnums.DOT.value:
            self.distance_method = models.Distance.DOT
        else:
            self.distance_method = models.Distance.COSINE

    def _require_client(self) -> QdrantClient:
        if self.client is None:
            self.connect()
        assert self.client is not None
        return self.client

    def connect(self) -> bool:
        if self.client is None:
            self.client = QdrantClient(path=self.db_path)
        return True

    def disconnect(self) -> bool:
        if self.client is not None:
            close_method = getattr(self.client, "close", None)
            if callable(close_method):
                close_method()
        self.client = None
        return True

    @staticmethod
    def _normalize_record_id(
        record_id: int | str | None = None,
    ) -> int | str:
        if record_id is None:
            return str(uuid.uuid4())
        if isinstance(record_id, int):
            return record_id

        record_value = str(record_id)
        try:
            return str(uuid.UUID(record_value))
        except ValueError:
            return str(
                uuid.uuid5(
                    uuid.NAMESPACE_URL,
                    record_value,
                )
            )

    @staticmethod
    def _validate_vector(
        vector: list[float],
        expected_size: int,
    ) -> None:
        if len(vector) != expected_size:
            raise ValueError(
                "vector dimension does not match collection size"
            )

    def is_collection_existed(
        self,
        collection_name: str,
    ) -> bool:
        return self._require_client().collection_exists(
            collection_name=collection_name
        )

    def list_all_collections(self) -> list[str]:
        response = self._require_client().get_collections()
        return [item.name for item in response.collections]

    def get_collection_info(
        self,
        collection_name: str,
    ) -> Any:
        if not self.is_collection_existed(collection_name):
            return None
        return self._require_client().get_collection(
            collection_name=collection_name
        )

    def delete_collection(
        self,
        collection_name: str,
    ) -> bool:
        if not self.is_collection_existed(collection_name):
            return False
        self._require_client().delete_collection(
            collection_name=collection_name
        )
        return True

    def create_collection(
        self,
        collection_name: str,
        embedding_size: int,
        do_reset: bool = False,
    ) -> bool:
        if embedding_size <= 0:
            raise ValueError("embedding_size must be positive")

        if do_reset:
            self.delete_collection(collection_name)

        if self.is_collection_existed(collection_name):
            info = self.get_collection_info(collection_name)
            configured_size = info.config.params.vectors.size
            if configured_size != embedding_size:
                raise ValueError(
                    "existing collection vector size does not "
                    "match embedding_size"
                )
            return False

        self._require_client().create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=embedding_size,
                distance=self.distance_method,
            ),
        )
        return True

    def insert_one(
        self,
        collection_name: str,
        text: str,
        vector: list[float],
        metadata: dict | None = None,
        record_id: int | str | None = None,
    ) -> bool:
        if not self.is_collection_existed(collection_name):
            return False

        info = self.get_collection_info(collection_name)
        self._validate_vector(
            vector,
            info.config.params.vectors.size,
        )

        point = models.PointStruct(
            id=self._normalize_record_id(record_id),
            vector=vector,
            payload={
                "text": text,
                "metadata": metadata or {},
                "record_id": (
                    str(record_id)
                    if record_id is not None
                    else None
                ),
            },
        )
        self._require_client().upsert(
            collection_name=collection_name,
            points=[point],
            wait=True,
        )
        return True

    def insert_many(
        self,
        collection_name: str,
        texts: list[str],
        vectors: list[list[float]],
        metadata: list[dict | None] | None = None,
        record_ids: list[int | str] | None = None,
        batch_size: int = 50,
    ) -> bool:
        if not self.is_collection_existed(collection_name):
            return False
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")

        metadata = metadata or [{} for _ in texts]
        record_ids = record_ids or [
            str(uuid.uuid4()) for _ in texts
        ]

        if not (
            len(texts)
            == len(vectors)
            == len(metadata)
            == len(record_ids)
        ):
            raise ValueError(
                "texts, vectors, metadata, and record_ids "
                "must have the same length"
            )

        info = self.get_collection_info(collection_name)
        expected_size = info.config.params.vectors.size
        for vector in vectors:
            self._validate_vector(vector, expected_size)

        for start in range(0, len(texts), batch_size):
            end = start + batch_size
            points = [
                models.PointStruct(
                    id=self._normalize_record_id(record_ids[index]),
                    vector=vectors[index],
                    payload={
                        "text": texts[index],
                        "metadata": metadata[index] or {},
                        "record_id": str(record_ids[index]),
                    },
                )
                for index in range(start, min(end, len(texts)))
            ]
            self._require_client().upsert(
                collection_name=collection_name,
                points=points,
                wait=True,
            )
        return True

    def search_by_vector(
        self,
        collection_name: str,
        vector: list[float],
        limit: int = 5,
    ) -> list:
        if limit <= 0:
            raise ValueError("limit must be positive")
        if not self.is_collection_existed(collection_name):
            return []

        info = self.get_collection_info(collection_name)
        self._validate_vector(
            vector,
            info.config.params.vectors.size,
        )

        response = self._require_client().query_points(
            collection_name=collection_name,
            query=vector,
            limit=limit,
            with_payload=True,
        )
        return list(response.points)

    def delete_by_ids(
        self,
        collection_name: str,
        record_ids: list[int | str],
    ) -> bool:
        if not record_ids:
            return True
        if not self.is_collection_existed(collection_name):
            return False

        point_ids = [
            self._normalize_record_id(record_id)
            for record_id in record_ids
        ]
        self._require_client().delete(
            collection_name=collection_name,
            points_selector=models.PointIdsList(
                points=point_ids
            ),
            wait=True,
        )
        return True
