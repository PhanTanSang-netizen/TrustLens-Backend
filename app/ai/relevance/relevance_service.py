import asyncio
from dataclasses import dataclass
from math import sqrt
from typing import Any

from app.ai.embeddings.base import EmbeddingProvider
from app.ai.embeddings.factory import create_embedding_provider
from app.ai.relevance.calibrator import (
    build_threshold_profile,
    c4_score_from_probability,
    calibrate_probability,
)
from app.ai.relevance.chunker import (
    ReportChunk,
    build_reference_representation,
    build_report_core_context,
    chunk_report_text,
)
from app.ai.relevance.lexical_scorer import lexical_similarity
from app.core.config import settings


@dataclass
class ReferenceInput:
    title: str | None
    abstract: str | None = None
    keywords: list[str] | str | None = None
    venue: str | None = None
    raw_citation: str | None = None


@dataclass
class RelevanceResult:
    score: int
    max_score: int
    reason: str
    confidence: float
    evidence: dict[str, Any]


class RelevanceService:
    def __init__(
        self,
        primary_provider: EmbeddingProvider | None = None,
        fallback_provider: EmbeddingProvider | None = None,
        prompt_version: str | None = None,
    ) -> None:
        self.primary_provider = primary_provider or create_embedding_provider(settings.RELEVANCE_PROVIDER)
        fallback_name = settings.RELEVANCE_FALLBACK_PROVIDER
        self.fallback_provider = fallback_provider or create_embedding_provider(fallback_name)
        self.prompt_version = prompt_version or settings.RELEVANCE_PROMPT_VERSION

    async def score_reference(
        self,
        report_text: str | None,
        reference: ReferenceInput,
        report_context: dict[str, Any] | None = None,
    ) -> RelevanceResult:
        core_text, core_method = build_report_core_context(report_text, report_context)
        body_text = ""
        if isinstance(report_context, dict):
            body_text = str(report_context.get("body_text") or "")
        body_text = body_text or report_text or ""
        chunks = chunk_report_text(body_text)
        reference_text, reference_evidence = build_reference_representation(
            title=reference.title or reference.raw_citation,
            abstract=reference.abstract,
            keywords=reference.keywords,
            venue=reference.venue,
        )

        if not core_text or not chunks:
            return RelevanceResult(
                score=0,
                max_score=20,
                reason="Insufficient report context for C4 relevance scoring.",
                confidence=0.0,
                evidence={
                    "status": "INSUFFICIENT_REPORT_CONTEXT",
                    "core_context_method": core_method,
                    **reference_evidence,
                },
            )

        if not reference_text:
            return self._lexical_only_result(
                core_text=core_text,
                chunks=chunks,
                reference_text=reference.raw_citation or "",
                core_method=core_method,
                reference_evidence=reference_evidence,
                provider_error="REFERENCE_TEXT_MISSING",
            )

        primary_result = await self._score_with_provider(
            self.primary_provider,
            core_text,
            chunks,
            reference_text,
            core_method,
            reference_evidence,
            fallback_used=False,
        )
        if primary_result is not None:
            return primary_result

        fallback_result = await self._score_with_provider(
            self.fallback_provider,
            core_text,
            chunks,
            reference_text,
            core_method,
            reference_evidence,
            fallback_used=True,
        )
        if fallback_result is not None:
            return fallback_result

        return self._lexical_only_result(
            core_text=core_text,
            chunks=chunks,
            reference_text=reference_text,
            core_method=core_method,
            reference_evidence=reference_evidence,
            provider_error="EMBEDDING_PROVIDER_UNAVAILABLE",
        )

    async def _score_with_provider(
        self,
        provider: EmbeddingProvider,
        core_text: str,
        chunks: list[ReportChunk],
        reference_text: str,
        core_method: str,
        reference_evidence: dict[str, bool],
        fallback_used: bool,
    ) -> RelevanceResult | None:
        query_text = self._build_query_prompt(core_text)
        document_texts = [self._build_reference_prompt(reference_text), *[chunk.text for chunk in chunks]]

        query_result = await provider.embed_query(query_text)
        documents_result = await provider.embed_documents(document_texts)
        if query_result.status != "SUCCESS" or documents_result.status != "SUCCESS":
            return None
        if not query_result.vectors or len(documents_result.vectors) < 2:
            return None

        reference_vector = documents_result.vectors[0]
        chunk_vectors = documents_result.vectors[1:]
        global_similarity = _cosine(query_result.vectors[0], reference_vector)
        chunk_similarities = [
            (chunk, _cosine(vector, reference_vector))
            for chunk, vector in zip(chunks, chunk_vectors, strict=False)
        ]
        top_chunks = sorted(chunk_similarities, key=lambda item: item[1], reverse=True)[: min(3, len(chunk_similarities))]
        local_top_k_mean = sum(score for _, score in top_chunks) / len(top_chunks) if top_chunks else 0.0
        lexical = lexical_similarity(" ".join([core_text, *(chunk.text for chunk, _ in top_chunks)]), reference_text)
        raw_relevance = global_similarity * 0.35 + local_top_k_mean * 0.50 + lexical * 0.15

        profile = build_threshold_profile(
            provider=query_result.provider,
            model_id=query_result.model_id,
            dimension=query_result.dimension,
            prompt_version=self.prompt_version,
        )
        probability = calibrate_probability(raw_relevance, profile)
        score = c4_score_from_probability(probability)
        confidence = self._confidence(reference_evidence, provider_quality=0.85 if fallback_used else 1.0)
        return RelevanceResult(
            score=score,
            max_score=20,
            reason="Relevance uses hybrid semantic global/local similarity plus lexical evidence.",
            confidence=confidence,
            evidence={
                "status": "SUCCESS",
                "provider": query_result.provider,
                "model_id": query_result.model_id,
                "embedding_dimension": query_result.dimension,
                "prompt_version": self.prompt_version,
                "threshold_profile": profile.name,
                "calibrator_version": profile.calibrator_version,
                "raw_relevance": round(raw_relevance, 4),
                "calibrated_probability": probability,
                "global_similarity": round(global_similarity, 4),
                "local_top_k_mean": round(local_top_k_mean, 4),
                "lexical_similarity": lexical,
                "top_chunks": [
                    {
                        "chunk_id": chunk.chunk_id,
                        "heading": chunk.heading,
                        "similarity": round(similarity, 4),
                        "start_char": chunk.start_char,
                        "end_char": chunk.end_char,
                    }
                    for chunk, similarity in top_chunks
                ],
                "core_context_method": core_method,
                "fallback_used": fallback_used,
                **reference_evidence,
            },
        )

    def _lexical_only_result(
        self,
        core_text: str,
        chunks: list[ReportChunk],
        reference_text: str,
        core_method: str,
        reference_evidence: dict[str, bool],
        provider_error: str,
    ) -> RelevanceResult:
        top_chunks = sorted(
            [(chunk, lexical_similarity(chunk.text, reference_text)) for chunk in chunks],
            key=lambda item: item[1],
            reverse=True,
        )[: min(3, len(chunks))]
        local_top_k_mean = sum(score for _, score in top_chunks) / len(top_chunks) if top_chunks else 0.0
        global_similarity = lexical_similarity(core_text, reference_text)
        lexical = lexical_similarity(" ".join([core_text, *(chunk.text for chunk, _ in top_chunks)]), reference_text)
        raw_relevance = global_similarity * 0.35 + local_top_k_mean * 0.50 + lexical * 0.15
        profile = build_threshold_profile("lexical", "tfidf-char-ngram", 0, self.prompt_version)
        probability = calibrate_probability(raw_relevance, profile)
        score = c4_score_from_probability(probability)
        return RelevanceResult(
            score=score,
            max_score=20,
            reason="Embedding provider unavailable; relevance uses low-confidence lexical fallback.",
            confidence=self._confidence(reference_evidence, provider_quality=0.40),
            evidence={
                "status": "FALLBACK",
                "provider": "lexical",
                "model_id": "tfidf-char-ngram",
                "embedding_dimension": 0,
                "prompt_version": self.prompt_version,
                "threshold_profile": profile.name,
                "calibrator_version": profile.calibrator_version,
                "raw_relevance": round(raw_relevance, 4),
                "calibrated_probability": probability,
                "global_similarity": round(global_similarity, 4),
                "local_top_k_mean": round(local_top_k_mean, 4),
                "lexical_similarity": lexical,
                "top_chunks": [
                    {
                        "chunk_id": chunk.chunk_id,
                        "heading": chunk.heading,
                        "similarity": round(similarity, 4),
                        "start_char": chunk.start_char,
                        "end_char": chunk.end_char,
                    }
                    for chunk, similarity in top_chunks
                ],
                "core_context_method": core_method,
                "fallback_used": True,
                "provider_error": provider_error,
                **reference_evidence,
            },
        )

    def _confidence(self, reference_evidence: dict[str, bool], provider_quality: float) -> float:
        if reference_evidence.get("reference_has_title") and reference_evidence.get("reference_has_abstract") and reference_evidence.get("reference_has_keywords"):
            evidence_quality = 0.95
        elif reference_evidence.get("reference_has_title") and reference_evidence.get("reference_has_abstract"):
            evidence_quality = 0.85
        elif reference_evidence.get("reference_has_title") and reference_evidence.get("reference_has_venue"):
            evidence_quality = 0.60
        elif reference_evidence.get("reference_has_title"):
            evidence_quality = 0.45
        else:
            evidence_quality = 0.25
        extraction_quality = 0.95
        return round(evidence_quality * extraction_quality * provider_quality, 3)

    def _build_query_prompt(self, core_text: str) -> str:
        return (
            "Task: Retrieve scholarly references that are relevant to and can support the "
            "following information-technology report.\n\n"
            f"Core report context:\n{core_text}"
        )

    def _build_reference_prompt(self, reference_text: str) -> str:
        return (
            "Task: Represent the following scholarly reference as a candidate document for "
            "retrieval by an information-technology report.\n\n"
            f"{reference_text}"
        )


def score_reference_sync(
    report_text: str | None,
    reference: ReferenceInput,
    report_context: dict[str, Any] | None = None,
) -> RelevanceResult:
    service = RelevanceService()
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(service.score_reference(report_text, reference, report_context))
    raise RuntimeError("score_reference_sync cannot run inside an active event loop") from None


def _cosine(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right, strict=False))
    left_norm = sqrt(sum(value * value for value in left))
    right_norm = sqrt(sum(value * value for value in right))
    if not left_norm or not right_norm:
        return 0.0
    return max(0.0, min(1.0, dot / (left_norm * right_norm)))
