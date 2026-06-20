import asyncio
import os
import time
from typing import Any

import httpx

from app.ai.embeddings.base import EmbeddingResult


class GeminiEmbeddingProvider:
    provider = "gemini"

    def __init__(
        self,
        api_key: str | None = None,
        model_id: str | None = None,
        dimension: int | None = None,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_id = model_id or os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-2")
        self.dimension = int(dimension or os.getenv("GEMINI_EMBEDDING_DIMENSION", "768"))
        self.timeout_seconds = float(timeout_seconds or os.getenv("GEMINI_TIMEOUT_SECONDS", "15"))
        self.max_retries = int(max_retries or os.getenv("GEMINI_MAX_RETRIES", "2"))

    async def embed_query(self, text: str) -> EmbeddingResult:
        return await self._embed_many([text])

    async def embed_documents(self, texts: list[str]) -> EmbeddingResult:
        return await self._embed_many(texts)

    async def _embed_many(self, texts: list[str]) -> EmbeddingResult:
        started = time.perf_counter()
        if not self.api_key:
            return self._error_result(started, "UNAVAILABLE", "MISSING_API_KEY")

        vectors: list[list[float]] = []
        for text in texts:
            result = await self._embed_one(text)
            if result.status != "SUCCESS":
                return result
            vectors.extend(result.vectors)

        return EmbeddingResult(
            vectors=vectors,
            provider=self.provider,
            model_id=self.model_id,
            dimension=self.dimension,
            latency_ms=int((time.perf_counter() - started) * 1000),
            status="SUCCESS",
        )

    async def _embed_one(self, text: str) -> EmbeddingResult:
        started = time.perf_counter()
        endpoint = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model_id}:embedContent"
        )
        payload: dict[str, Any] = {
            "content": {"parts": [{"text": text}]},
            "output_dimensionality": self.dimension,
        }

        attempts = self.max_retries + 1
        last_error = "UNKNOWN_ERROR"
        for attempt in range(attempts):
            try:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    response = await client.post(
                        endpoint,
                        params={"key": self.api_key},
                        json=payload,
                        headers={"Accept": "application/json"},
                    )

                if response.status_code in {400, 401, 403}:
                    return self._error_result(started, "FAILED", f"HTTP_{response.status_code}")
                if response.status_code == 429:
                    last_error = "RATE_LIMITED"
                    if attempt < attempts - 1:
                        await asyncio.sleep(0.25 * (attempt + 1))
                        continue
                    return self._error_result(started, "RATE_LIMITED", last_error)
                if response.status_code >= 500:
                    last_error = f"HTTP_{response.status_code}"
                    if attempt < attempts - 1:
                        await asyncio.sleep(0.25 * (attempt + 1))
                        continue
                    return self._error_result(started, "UNAVAILABLE", last_error)

                response.raise_for_status()
                data = response.json()
                values = data.get("embedding", {}).get("values")
                if not isinstance(values, list):
                    return self._error_result(started, "FAILED", "INVALID_RESPONSE")

                vector = [float(value) for value in values]
                return EmbeddingResult(
                    vectors=[vector],
                    provider=self.provider,
                    model_id=self.model_id,
                    dimension=len(vector),
                    latency_ms=int((time.perf_counter() - started) * 1000),
                    status="SUCCESS",
                )
            except (httpx.TimeoutException, httpx.RequestError) as exc:
                last_error = exc.__class__.__name__
                if attempt < attempts - 1:
                    await asyncio.sleep(0.25 * (attempt + 1))
                    continue
                return self._error_result(started, "UNAVAILABLE", last_error)
            except (ValueError, TypeError):
                return self._error_result(started, "FAILED", "INVALID_RESPONSE")

        return self._error_result(started, "UNAVAILABLE", last_error)

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
