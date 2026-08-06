from sqlalchemy.orm import sessionmaker

from controllers.BaseController import BaseController

from .VectorDBEnums import VectorDBEnums
from .providers import PGVectorProvider, QdrantDBProvider


class VectorDBProviderFactory:
    def __init__(
        self,
        config: object,
        db_client: sessionmaker | None = None,
    ):
        self.config = config
        self.base_controller = BaseController()
        self.db_client = db_client

    def create(self, provider: str):
        normalized_provider = str(provider).strip().upper()

        if normalized_provider == VectorDBEnums.QDRANT.value:
            qdrant_path = self.base_controller.get_database_path(
                db_name=self.config.VECTOR_DB_PATH
            )
            return QdrantDBProvider(
                db_path=qdrant_path,
                distance_method=(
                    self.config.VECTOR_DB_DISTANCE_METHOD
                ),
                default_vector_size=(
                    self.config.EMBEDDING_MODEL_SIZE
                ),
            )

        if normalized_provider == VectorDBEnums.PGVECTOR.value:
            if self.db_client is None:
                raise ValueError(
                    "db_client is required for PGVECTOR"
                )

            return PGVectorProvider(
                db_client=self.db_client,
                distance_method=(
                    self.config.VECTOR_DB_DISTANCE_METHOD
                ),
                default_vector_size=(
                    self.config.EMBEDDING_MODEL_SIZE
                ),
                index_threshold=(
                    self.config.VECTOR_DB_PGVEC_INDEX_THRESHOLD
                ),
            )

        raise ValueError(
            f"unsupported vector database provider: {provider}"
        )
