import os
import time
from typing import Any

import httpx

from app.ai.embeddings.base import EmbeddingResult


class HuggingFaceEmbeddingProvider:
    provider = "huggingface"

    def __init__(self, token: str | None = None, model_id: str | None = None) -> None:
        self.token = token or os.getenv("HF_TOKEN")
        self.model_id = model_id or os.getenv("HF_EMBEDDING_MODEL", "intfloat/multilingual-e5-small")
        self.dimension = 0

    async def embed_query(self, text: str) -> EmbeddingResult:
        return await self._embed_many([text])

    async def embed_documents(self, texts: list[str]) -> EmbeddingResult:
        return await self._embed_many(texts)

    async def _embed_many(self, texts: list[str]) -> EmbeddingResult:
        started = time.perf_counter()
        if not self.token:
            return self._error_result(started, "UNAVAILABLE", "MISSING_TOKEN")

        endpoint = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{self.model_id}"
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(
                    endpoint,
                    headers={"Authorization": f"Bearer {self.token}"},
                    json={"inputs": texts},
                )
            if response.status_code == 429:
                return self._error_result(started, "RATE_LIMITED", "HTTP_429")
            if response.status_code >= 400:
                return self._error_result(started, "UNAVAILABLE", f"HTTP_{response.status_code}")

            data = response.json()
            vectors = self._normalize_response(data)
            dimension = len(vectors[0]) if vectors else 0
            self.dimension = dimension
            return EmbeddingResult(
                vectors=vectors,
                provider=self.provider,
                model_id=self.model_id,
                dimension=dimension,
                latency_ms=int((time.perf_counter() - started) * 1000),
                status="SUCCESS",
            )
        except (httpx.RequestError, ValueError, TypeError):
            return self._error_result(started, "UNAVAILABLE", "REQUEST_FAILED")

    def _normalize_response(self, data: Any) -> list[list[float]]:
        if not isinstance(data, list):
            return []
        if data and isinstance(data[0], (int, float)):
            return [[float(value) for value in data]]
        vectors: list[list[float]] = []
        for item in data:
            if item and isinstance(item, list) and isinstance(item[0], list):
                pooled = [
                    sum(float(token[index]) for token in item) / len(item)
                    for index in range(len(item[0]))
                ]
                vectors.append(pooled)
            elif isinstance(item, list):
                vectors.append([float(value) for value in item])
        return vectors

    def _error_result(self, started: float, status: str, error_code: str) -> EmbeddingResult:
        return EmbeddingResult(
            vectors=[],
            provider=self.provider,
            model_id=self.model_id,
            dimension=self.dimension,
            latency_ms=int((time.perf_counter() - started) * 1000),
            status=status,
            error_code=error_code,
        )
