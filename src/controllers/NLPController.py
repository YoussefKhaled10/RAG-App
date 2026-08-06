import inspect
import json
import logging
import re
from typing import Any

from models.db_schemes import DataChunk, Project
from stores.llm.LLMEnums import DocumentTypeEnum

from .BaseController import BaseController


class NLPController(BaseController):
    def __init__(
        self,
        vectordb_client,
        generation_client,
        embedding_client,
        template_parser,
    ):
        super().__init__()
        self.vectordb_client = vectordb_client
        self.generation_client = generation_client
        self.embedding_client = embedding_client
        self.template_parser = template_parser
        self.logger = logging.getLogger(__name__)

    @staticmethod
    async def _maybe_await(value):
        if inspect.isawaitable(value):
            return await value
        return value

    @staticmethod
    def create_collection_name(
        project_id: int,
        tenant_id=None,
        project_uuid=None,
    ) -> str:
        if tenant_id is not None:
            tenant_part = re.sub(
                r"[^a-z0-9]",
                "",
                str(tenant_id).lower(),
            )
            return f"collection_{tenant_part}_{int(project_id)}"

        if project_uuid is not None:
            project_part = re.sub(
                r"[^a-z0-9]",
                "",
                str(project_uuid).lower(),
            )
            return f"collection_{project_part}"

        return f"collection_{int(project_id)}"

    def _project_collection_name(
        self,
        project: Project,
    ) -> str:
        return self.create_collection_name(
            project_id=project.project_id,
            tenant_id=getattr(project, "tenant_id", None),
            project_uuid=getattr(project, "project_uuid", None),
        )

    async def reset_vector_db_collection(
        self,
        project: Project,
    ) -> bool:
        return bool(
            await self._maybe_await(
                self.vectordb_client.delete_collection(
                    collection_name=(
                        self._project_collection_name(project)
                    )
                )
            )
        )

    async def get_vector_db_collection_info(
        self,
        project: Project,
    ) -> dict | None:
        collection_info = await self._maybe_await(
            self.vectordb_client.get_collection_info(
                collection_name=(
                    self._project_collection_name(project)
                )
            )
        )
        if collection_info is None:
            return None

        return json.loads(
            json.dumps(
                collection_info,
                default=lambda value: getattr(
                    value,
                    "__dict__",
                    str(value),
                ),
            )
        )

    async def delete_vectors_by_ids(
        self,
        project: Project,
        record_ids: list[int],
    ) -> bool:
        if not record_ids:
            return True

        delete_method = getattr(
            self.vectordb_client,
            "delete_by_ids",
            None,
        )
        if not callable(delete_method):
            self.logger.error(
                "Vector DB provider does not support delete_by_ids"
            )
            return False

        result = await self._maybe_await(
            delete_method(
                collection_name=(
                    self._project_collection_name(project)
                ),
                record_ids=record_ids,
            )
        )
        return bool(result)

    def _expected_embedding_size(self) -> int:
        expected_size = getattr(
            self.embedding_client,
            "embedding_size",
            None,
        )
        if not isinstance(expected_size, int) or expected_size <= 0:
            raise ValueError(
                "embedding client size was not configured"
            )
        return expected_size

    @staticmethod
    def _normalize_texts(texts: list[str]) -> list[str]:
        normalized_texts = [
            str(text).strip()
            for text in texts
            if text is not None and str(text).strip()
        ]
        if len(normalized_texts) != len(texts):
            raise ValueError(
                "empty chunk text cannot be embedded"
            )
        return normalized_texts

    def _validate_vectors(
        self,
        vectors: Any,
        expected_count: int,
    ) -> list[list[float]]:
        if not isinstance(vectors, list) or not vectors:
            raise RuntimeError("embedding provider returned no vectors")
        if len(vectors) != expected_count:
            raise RuntimeError(
                "embedding vectors count does not match text count"
            )

        expected_size = self._expected_embedding_size()
        normalized_vectors: list[list[float]] = []

        for index, vector in enumerate(vectors, start=1):
            if not isinstance(vector, (list, tuple)):
                raise RuntimeError(
                    f"embedding vector {index} is invalid"
                )
            if len(vector) != expected_size:
                raise RuntimeError(
                    "embedding dimension mismatch at vector "
                    f"{index}: expected={expected_size}, "
                    f"received={len(vector)}"
                )
            normalized_vectors.append(
                [float(value) for value in vector]
            )

        return normalized_vectors

    def _embed_documents(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        clean_texts = self._normalize_texts(texts)
        embed_many = getattr(
            self.embedding_client,
            "embed_texts",
            None,
        )

        if callable(embed_many):
            vectors = embed_many(
                texts=clean_texts,
                document_type=DocumentTypeEnum.DOCUMENT.value,
                batch_size=5,
            )
        else:
            vectors = [
                self.embedding_client.embed_text(
                    text=text,
                    document_type=(
                        DocumentTypeEnum.DOCUMENT.value
                    ),
                )
                for text in clean_texts
            ]

        return self._validate_vectors(
            vectors=vectors,
            expected_count=len(clean_texts),
        )

    def _embed_query(self, text: str) -> list[float]:
        clean_text = str(text).strip()
        if not clean_text:
            raise ValueError("query cannot be empty")

        vector = self.embedding_client.embed_text(
            text=clean_text,
            document_type=DocumentTypeEnum.QUERY.value,
        )
        return self._validate_vectors(
            vectors=[vector] if vector is not None else None,
            expected_count=1,
        )[0]

    @staticmethod
    def _extract_doc_text(doc) -> str:
        if hasattr(doc, "payload") and doc.payload:
            return str(doc.payload.get("text", ""))
        if isinstance(doc, dict):
            payload = doc.get("payload", {})
            return str(payload.get("text", doc.get("text", "")))
        return str(getattr(doc, "text", ""))

    async def index_into_vector_db(
        self,
        project: Project,
        chunks: list[DataChunk],
        chunks_ids: list[int],
        do_reset: bool = False,
    ) -> bool:
        if len(chunks) != len(chunks_ids):
            raise ValueError(
                "chunks and chunks_ids must have the same length"
            )

        valid_items: list[tuple[DataChunk, int]] = []
        for chunk, chunk_id in zip(chunks, chunks_ids):
            chunk_text = getattr(chunk, "chunk_text", None)
            if (
                chunk_id is None
                or chunk_text is None
                or not str(chunk_text).strip()
            ):
                raise ValueError(
                    "all chunks must contain text and chunk_id"
                )
            valid_items.append((chunk, int(chunk_id)))

        if not valid_items:
            raise ValueError("no chunks were provided for indexing")

        texts = [
            str(chunk.chunk_text).strip()
            for chunk, _ in valid_items
        ]
        metadata = []
        record_ids = []

        tenant_id = str(getattr(project, "tenant_id", ""))
        project_id = int(project.project_id)

        for chunk, chunk_id in valid_items:
            chunk_metadata = dict(
                getattr(chunk, "chunk_metadata", None) or {}
            )
            chunk_metadata.update(
                {
                    "tenant_id": tenant_id,
                    "project_id": project_id,
                    "chunk_id": chunk_id,
                    "asset_id": getattr(
                        chunk,
                        "chunk_asset_id",
                        None,
                    ),
                    "chunk_order": getattr(
                        chunk,
                        "chunk_order",
                        None,
                    ),
                }
            )
            metadata.append(chunk_metadata)
            record_ids.append(chunk_id)

        vectors = self._embed_documents(texts)
        collection_name = self._project_collection_name(project)
        embedding_size = self._expected_embedding_size()

        await self._maybe_await(
            self.vectordb_client.create_collection(
                collection_name=collection_name,
                embedding_size=embedding_size,
                do_reset=do_reset,
            )
        )

        inserted = await self._maybe_await(
            self.vectordb_client.insert_many(
                collection_name=collection_name,
                texts=texts,
                vectors=vectors,
                metadata=metadata,
                record_ids=record_ids,
            )
        )
        if not inserted:
            raise RuntimeError("vector database insertion failed")

        self.logger.info(
            "Indexed %s chunks into %s",
            len(record_ids),
            collection_name,
        )
        return True

    async def search_vector_db_collection(
        self,
        project: Project,
        text: str,
        limit: int = 10,
    ) -> list:
        if limit <= 0 or limit > 100:
            raise ValueError("limit must be between 1 and 100")

        vector = self._embed_query(text)
        results = await self._maybe_await(
            self.vectordb_client.search_by_vector(
                collection_name=(
                    self._project_collection_name(project)
                ),
                vector=vector,
                limit=limit,
            )
        )
        return list(results or [])

    async def answer_rag_question(
        self,
        project: Project,
        query: str,
        limit: int = 10,
    ):
        clean_query = str(query).strip()
        if not clean_query:
            return None, None, None

        retrieved_documents = (
            await self.search_vector_db_collection(
                project=project,
                text=clean_query,
                limit=limit,
            )
        )
        if not retrieved_documents:
            return None, None, None

        document_blocks = []
        for index, document in enumerate(
            retrieved_documents,
            start=1,
        ):
            document_text = self._extract_doc_text(document).strip()
            if not document_text:
                continue
            document_blocks.append(
                self.template_parser.get(
                    "rag",
                    "document_prompt",
                    {
                        "doc_num": index,
                        "chunk_text": document_text,
                    },
                )
            )

        if not document_blocks:
            return None, None, None

        system_prompt = self.template_parser.get(
            "rag",
            "system_prompt",
        )
        footer_prompt = self.template_parser.get(
            "rag",
            "footer_prompt",
            {"query": clean_query},
        )

        chat_history = [
            self.generation_client.construct_prompt(
                prompt=system_prompt,
                role=self.generation_client.enums.SYSTEM.value,
            )
        ]
        full_prompt = "\n\n".join(
            [*document_blocks, footer_prompt]
        )
        answer = self.generation_client.generate_text(
            prompt=full_prompt,
            chat_history=chat_history,
        )

        if not answer:
            raise RuntimeError(
                "generation provider returned no answer"
            )

        return answer, full_prompt, chat_history

    @staticmethod
    def reciprocal_rank_fusion(
        semantic_results: list,
        keyword_results: list[dict],
        limit: int = 5,
        rrf_k: int = 60,
    ) -> list[dict]:
        fused: dict[int, dict] = {}

        def ensure_item(chunk_id: int, source: dict) -> dict:
            item = fused.setdefault(
                chunk_id,
                {
                    "chunk_id": chunk_id,
                    "asset_id": source.get("asset_id"),
                    "chunk_order": source.get("chunk_order"),
                    "text": source.get("text", ""),
                    "metadata": source.get("metadata", {}),
                    "semantic_score": None,
                    "keyword_score": None,
                    "fusion_score": 0.0,
                    "semantic_rank": None,
                    "keyword_rank": None,
                    "matched_by": [],
                },
            )
            if not item["text"]:
                item["text"] = source.get("text", "")
            if not item["metadata"]:
                item["metadata"] = source.get("metadata", {})
            return item

        for rank, document in enumerate(semantic_results, start=1):
            source = (
                document.model_dump()
                if hasattr(document, "model_dump")
                else dict(document)
            )
            chunk_id = int(source["chunk_id"])
            item = ensure_item(chunk_id, source)
            item["semantic_score"] = float(source.get("score", 0.0))
            item["semantic_rank"] = rank
            item["fusion_score"] += 1.0 / (rrf_k + rank)
            item["matched_by"].append("semantic")

        for rank, source in enumerate(keyword_results, start=1):
            chunk_id = int(source["chunk_id"])
            item = ensure_item(chunk_id, source)
            item["keyword_score"] = float(source.get("score", 0.0))
            item["keyword_rank"] = rank
            item["fusion_score"] += 1.0 / (rrf_k + rank)
            item["matched_by"].append("keyword")

        return sorted(
            fused.values(),
            key=lambda item: item["fusion_score"],
            reverse=True,
        )[:limit]

    async def hybrid_search(
        self,
        project: Project,
        query: str,
        keyword_results: list[dict],
        limit: int = 5,
        semantic_limit: int = 20,
        rrf_k: int = 60,
    ) -> list[dict]:
        semantic_results = await self.search_vector_db_collection(
            project=project,
            text=query,
            limit=semantic_limit,
        )
        return self.reciprocal_rank_fusion(
            semantic_results=semantic_results,
            keyword_results=keyword_results,
            limit=limit,
            rrf_k=rrf_k,
        )

    def answer_from_hybrid_results(
        self,
        question: str,
        results: list[dict],
    ) -> str:
        if not results:
            raise ValueError("hybrid search returned no results")

        system_prompt = self.template_parser.get("rag", "system_prompt")
        document_blocks = [
            self.template_parser.get(
                "rag",
                "document_prompt",
                {
                    "doc_num": index,
                    "chunk_text": item["text"],
                },
            )
            for index, item in enumerate(results, start=1)
        ]
        footer_prompt = self.template_parser.get(
            "rag", "footer_prompt", {"query": question}
        )
        chat_history = [
            self.generation_client.construct_prompt(
                prompt=system_prompt,
                role=self.generation_client.enums.SYSTEM.value,
            )
        ]
        answer = self.generation_client.generate_text(
            prompt="\n\n".join([*document_blocks, footer_prompt]),
            chat_history=chat_history,
        )
        if not answer:
            raise RuntimeError("generation provider returned no answer")
        return answer
