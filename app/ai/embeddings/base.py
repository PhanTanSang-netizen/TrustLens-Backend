from dataclasses import dataclass
from typing import Protocol


@dataclass
class EmbeddingResult:
    vectors: list[list[float]]
    provider: str
    model_id: str
    dimension: int
    latency_ms: int
    status: str
    error_code: str | None = None


class EmbeddingProvider(Protocol):
    provider: str
    model_id: str
    dimension: int

    async def embed_query(self, text: str) -> EmbeddingResult:
        ...

    async def embed_documents(self, texts: list[str]) -> EmbeddingResult:
        ...
