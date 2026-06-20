from app.ai.embeddings.base import EmbeddingProvider
from app.ai.embeddings.gemini_provider import GeminiEmbeddingProvider
from app.ai.embeddings.huggingface_provider import HuggingFaceEmbeddingProvider
from app.ai.embeddings.local_provider import LocalSentenceTransformerProvider
from app.core.config import settings


def create_embedding_provider(name: str | None = None) -> EmbeddingProvider:
    provider_name = (name or settings.RELEVANCE_PROVIDER).strip().lower()
    if provider_name == "gemini":
        return GeminiEmbeddingProvider(
            api_key=settings.GEMINI_API_KEY,
            model_id=settings.GEMINI_EMBEDDING_MODEL,
            dimension=settings.GEMINI_EMBEDDING_DIMENSION,
            timeout_seconds=settings.GEMINI_TIMEOUT_SECONDS,
            max_retries=settings.GEMINI_MAX_RETRIES,
        )
    if provider_name in {"local", "local_sentence_transformer", "sentence_transformer"}:
        return LocalSentenceTransformerProvider(
            model_id=settings.LOCAL_EMBEDDING_MODEL,
            device=settings.LOCAL_EMBEDDING_DEVICE,
        )
    if provider_name in {"hf", "huggingface"}:
        return HuggingFaceEmbeddingProvider(token=settings.HF_TOKEN, model_id=settings.HF_EMBEDDING_MODEL)
    return LocalSentenceTransformerProvider(model_id=provider_name)
