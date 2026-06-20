import unittest
from types import SimpleNamespace

from app.models.citation import Citation
from app.services.scoring_service import (
    ComponentScore,
    _apply_component_weights,
    _evaluate_penalties,
    _warnings_for_reference,
)


class WeightInvarianceTests(unittest.TestCase):
    def test_low_relevance_penalty_survives_zero_weight(self) -> None:
        components = {
            "c1": ComponentScore(10, 10, "ok", {}, 1.0),
            "c2": ComponentScore(25, 25, "ok", {}, 1.0),
            "c3": ComponentScore(20, 20, "ok", {}, 1.0),
            "c4": ComponentScore(3, 20, "low", {"status": "SUCCESS"}, 0.9),
            "c5": ComponentScore(10, 10, "ok", {}, 1.0),
            "c6": ComponentScore(10, 10, "ok", {}, 1.0),
            "c7": ComponentScore(5, 5, "ok", {}, 1.0),
        }
        weights = {
            "c1_completeness": 10,
            "c2_verification": 25,
            "c3_credibility": 20,
            "c4_relevance": 0,
            "c5_recency": 20,
            "c6_style": 20,
            "c7_duplicate_concentration": 5,
        }
        weighted = _apply_component_weights(components, weights)
        penalties = _evaluate_penalties(Citation(raw_text="ref"), None, weighted, None)

        self.assertEqual(weighted["c4"].score, 0)
        self.assertIn("LOW_RELEVANCE", {item["code"] for item in penalties})

    def test_style_warning_uses_raw_ratio_not_weighted_score(self) -> None:
        components = {
            "c1": ComponentScore(10, 10, "ok", {"missing_fields": []}, 1.0),
            "c2": ComponentScore(25, 25, "ok", {}, 1.0),
            "c3": ComponentScore(20, 20, "ok", {}, 1.0),
            "c4": ComponentScore(20, 20, "ok", {"status": "SUCCESS"}, 0.9),
            "c5": ComponentScore(10, 10, "ok", {"age": 0}, 1.0),
            "c6": ComponentScore(6, 10, "Citation style differs.", {}, 0.9),
            "c7": ComponentScore(5, 5, "ok", {}, 1.0),
        }
        weights = {
            "c1_completeness": 10,
            "c2_verification": 25,
            "c3_credibility": 20,
            "c4_relevance": 20,
            "c5_recency": 10,
            "c6_style": 0,
            "c7_duplicate_concentration": 15,
        }
        weighted = _apply_component_weights(components, weights)
        metadata = SimpleNamespace(verification_status="VERIFIED", raw_response={}, confidence_score=1.0, provider="test")
        warnings = _warnings_for_reference(Citation(raw_text="ref"), metadata, weighted, [])

        self.assertEqual(weighted["c6"].score, 0)
        self.assertIn("STYLE_REVIEW", {item["code"] for item in warnings})


if __name__ == "__main__":
    unittest.main()
