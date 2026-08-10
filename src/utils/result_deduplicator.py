import hashlib
import re
from typing import Any


class ResultDeduplicator:
    """Remove exact and near-duplicate retrieved text while preserving order."""

    def __init__(
        self,
        similarity_threshold: float = 0.92,
        shingle_size: int = 5,
    ) -> None:
        if not 0.0 <= similarity_threshold <= 1.0:
            raise ValueError("similarity_threshold must be between 0 and 1")
        if shingle_size < 2:
            raise ValueError("shingle_size must be at least 2")
        self.similarity_threshold = float(similarity_threshold)
        self.shingle_size = int(shingle_size)

    @staticmethod
    def _normalize(text: str) -> str:
        value = str(text or "").lower()
        value = re.sub(r"[\u064b-\u065f\u0670]", "", value)
        value = value.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
        value = value.replace("ى", "ي").replace("ؤ", "و").replace("ئ", "ي")
        value = re.sub(r"[^\w\u0600-\u06ff]+", " ", value)
        return re.sub(r"\s+", " ", value).strip()

    @staticmethod
    def _hash(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def _shingles(self, value: str) -> set[str]:
        words = value.split()
        if not words:
            return set()
        if len(words) < self.shingle_size:
            return {" ".join(words)}
        return {
            " ".join(words[index:index + self.shingle_size])
            for index in range(len(words) - self.shingle_size + 1)
        }

    @staticmethod
    def _jaccard(left: set[str], right: set[str]) -> float:
        if not left or not right:
            return 0.0
        union = left | right
        if not union:
            return 0.0
        return len(left & right) / len(union)

    def deduplicate(
        self,
        results: list[dict[str, Any]],
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        if not results:
            return []

        output: list[dict[str, Any]] = []
        exact_hashes: set[str] = set()
        accepted_shingles: list[set[str]] = []

        for raw_item in results:
            item = dict(raw_item)
            normalized = self._normalize(item.get("text", ""))
            if not normalized:
                continue

            text_hash = self._hash(normalized)
            if text_hash in exact_hashes:
                continue

            shingles = self._shingles(normalized)
            is_near_duplicate = any(
                self._jaccard(shingles, previous) >= self.similarity_threshold
                for previous in accepted_shingles
            )
            if is_near_duplicate:
                continue

            exact_hashes.add(text_hash)
            accepted_shingles.append(shingles)
            item["content_hash"] = text_hash
            output.append(item)

            if limit is not None and len(output) >= max(int(limit), 1):
                break

        return output