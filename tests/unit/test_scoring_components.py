import unittest
from types import SimpleNamespace

from app.core.enums.metadata_status import MetadataStatus
from app.models.citation import Citation
from app.services.scoring_service import (
    DEFAULT_THRESHOLDS,
    _score_relevance,
    _score_verification,
)


class ScoringComponentTests(unittest.TestCase):
    def test_verification_scores_use_normalized_v11_scale(self) -> None:
        cases = {
            MetadataStatus.VERIFIED: 25,
            MetadataStatus.PARTIAL_MATCH: 18,
            MetadataStatus.AMBIGUOUS: 10,
            MetadataStatus.URL_ONLY: 7,
            MetadataStatus.NOT_FOUND: 3,
            MetadataStatus.PROVIDER_UNAVAILABLE: 8,
            MetadataStatus.INVALID_IDENTIFIER: 0,
        }

        for status_value, expected_score in cases.items():
            metadata = SimpleNamespace(
                verification_status=status_value.value,
                confidence_score=0.8,
                provider="test",
                raw_response={"evidence": {}, "candidate_count": 0},
            )
            self.assertEqual(_score_verification(metadata).score, expected_score)

    def test_relevance_does_not_need_reference_section_text(self) -> None:
        citation = Citation(
            raw_text="Example reference",
            title="machine learning model evaluation",
            detected_style="APA7",
        )
        metadata = SimpleNamespace(
            matched_title="machine learning model evaluation",
            raw_response={"abstract": "Evaluation metrics for machine learning models."},
        )
        component = _score_relevance(
            citation=citation,
            metadata=metadata,
            report_text="This report studies machine learning model evaluation metrics.",
            thresholds=DEFAULT_THRESHOLDS,
        )

        self.assertGreater(component.score, 3)
        self.assertEqual(component.evidence["model"], "lexical-tfidf-fallback")


if __name__ == "__main__":
    unittest.main()
