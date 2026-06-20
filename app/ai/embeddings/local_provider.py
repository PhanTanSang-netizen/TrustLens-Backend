import os
import time

from app.ai.embeddings.base import EmbeddingResult


class LocalSentenceTransformerProvider:
    provider = "local_sentence_transformer"

    def __init__(self, model_id: str | None = None, device: str | None = None) -> None:
        self.model_id = model_id or os.getenv("LOCAL_EMBEDDING_MODEL", "intfloat/multilingual-e5-small")
        self.device = device or os.getenv("LOCAL_EMBEDDING_DEVICE", "cpu")
        self.dimension = 0
        self._model = None

    async def embed_query(self, text: str) -> EmbeddingResult:
        return await self._embed_many([f"query: {text}"])

    async def embed_documents(self, texts: list[str]) -> EmbeddingResult:
        return await self._embed_many([f"passage: {text}" for text in texts])

    def _load_model(self):
        if self._model is not None:
            return self._model
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            return None
        self._model = SentenceTransformer(self.model_id, device=self.device)
        return self._model

    async def _embed_many(self, texts: list[str]) -> EmbeddingResult:
        started = time.perf_counter()
        model = self._load_model()
        if model is None:
            return EmbeddingResult(
                vectors=[],
                provider=self.provider,
                model_id=self.model_id,
                dimension=self.dimension,
                latency_ms=int((time.perf_counter() - started) * 1000),
                status="UNAVAILABLE",
                error_code="DEPENDENCY_MISSING",
            )

        vectors = model.encode(texts, normalize_embeddings=True)
        result = [[float(value) for value in vector] for vector in vectors]
        dimension = len(result[0]) if result else 0
        self.dimension = dimension
        return EmbeddingResult(
            vectors=result,
            provider=self.provider,
            model_id=self.model_id,
            dimension=dimension,
            latency_ms=int((time.perf_counter() - started) * 1000),
            status="SUCCESS",
        )
