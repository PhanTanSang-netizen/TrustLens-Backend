import unittest

from app.ai.embeddings.base import EmbeddingResult
from app.ai.relevance.relevance_service import ReferenceInput, RelevanceService


class FailingProvider:
    provider = "failing"
    model_id = "failing-model"
    dimension = 2

    async def embed_query(self, text: str) -> EmbeddingResult:
        return EmbeddingResult([], self.provider, self.model_id, self.dimension, 1, "UNAVAILABLE", "TIMEOUT")

    async def embed_documents(self, texts: list[str]) -> EmbeddingResult:
        return EmbeddingResult([], self.provider, self.model_id, self.dimension, 1, "UNAVAILABLE", "TIMEOUT")


class SemanticProvider:
    provider = "test_semantic"
    model_id = "test-model"
    dimension = 2

    async def embed_query(self, text: str) -> EmbeddingResult:
        return EmbeddingResult([self._vector(text)], self.provider, self.model_id, self.dimension, 1, "SUCCESS")

    async def embed_documents(self, texts: list[str]) -> EmbeddingResult:
        return EmbeddingResult([self._vector(text) for text in texts], self.provider, self.model_id, self.dimension, 1, "SUCCESS")

    def _vector(self, text: str) -> list[float]:
        lowered = text.lower()
        if "fraud" in lowered or "gian lận" in lowered or "bat thuong" in lowered or "bất thường" in lowered:
            return [1.0, 0.0]
        return [0.0, 1.0]


class RelevanceServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_provider_timeout_uses_fallback_without_zeroing_relevance(self) -> None:
        service = RelevanceService(primary_provider=FailingProvider(), fallback_provider=SemanticProvider())
        result = await service.score_reference(
            report_text="Báo cáo xây dựng hệ thống phát hiện gian lận trong giao dịch trực tuyến.",
            report_context={"body_text": "Báo cáo xây dựng hệ thống phát hiện gian lận trong giao dịch trực tuyến."},
            reference=ReferenceInput(
                title="Fraud detection for online transaction anomaly analysis",
                abstract="Models detect suspicious payment behavior.",
            ),
        )

        self.assertGreater(result.score, 3)
        self.assertTrue(result.evidence["fallback_used"])
        self.assertNotEqual(result.evidence["provider"], "failing")

    async def test_semantic_provider_can_score_synonyms_above_lexical_only(self) -> None:
        report = "Báo cáo phát hiện gian lận và hành vi bất thường trong giao dịch điện tử."
        reference = ReferenceInput(title="Fraud detection in electronic transactions", abstract="Anomaly methods for payment risk.")
        semantic = await RelevanceService(primary_provider=SemanticProvider(), fallback_provider=FailingProvider()).score_reference(
            report_text=report,
            report_context={"body_text": report},
            reference=reference,
        )
        lexical = await RelevanceService(primary_provider=FailingProvider(), fallback_provider=FailingProvider()).score_reference(
            report_text=report,
            report_context={"body_text": report},
            reference=reference,
        )

        self.assertGreater(semantic.evidence["raw_relevance"], lexical.evidence["raw_relevance"])
        self.assertEqual(semantic.evidence["threshold_profile"], "test_semantic-test-model-2-c4-v2")

    async def test_title_only_has_lower_confidence_than_title_and_abstract(self) -> None:
        service = RelevanceService(primary_provider=FailingProvider(), fallback_provider=FailingProvider())
        report = "Báo cáo đánh giá mô hình học máy cho phân loại văn bản tiếng Việt."
        title_only = await service.score_reference(
            report_text=report,
            report_context={"body_text": report},
            reference=ReferenceInput(title="Vietnamese text classification with machine learning"),
        )
        with_abstract = await service.score_reference(
            report_text=report,
            report_context={"body_text": report},
            reference=ReferenceInput(
                title="Vietnamese text classification with machine learning",
                abstract="The paper studies supervised models for Vietnamese text classification.",
            ),
        )

        self.assertLess(title_only.confidence, with_abstract.confidence)


if __name__ == "__main__":
    unittest.main()
