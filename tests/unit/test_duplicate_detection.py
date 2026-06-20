import unittest
from uuid import uuid4

from app.models.citation import Citation
from app.services.scoring_service import _find_duplicate_match


class DuplicateDetectionTests(unittest.TestCase):
    def test_fuzzy_title_author_year_detects_duplicate_reference(self) -> None:
        first = Citation(
            id=uuid4(),
            raw_text="ref 1",
            title="Deep Learning for Malware Detection in Android Applications",
            authors="Nguyen Van A, Tran Thi B",
            year=2024,
            detected_style="APA7",
        )
        second = Citation(
            id=uuid4(),
            raw_text="ref 2",
            title="Deep-learning for malware detection in Android application",
            authors="Nguyen V. A, Tran T. B",
            year=2024,
            detected_style="APA7",
        )

        match = _find_duplicate_match(second, None, [(first, None)], {})

        self.assertIsNotNone(match)
        self.assertEqual(match.duplicate_of, first.id)
        self.assertEqual(match.match_type, "fuzzy_title_author_year")
        self.assertGreaterEqual(match.confidence, 0.85)

    def test_short_ambiguous_title_is_not_fuzzy_duplicate(self) -> None:
        first = Citation(
            id=uuid4(),
            raw_text="ref 1",
            title="Machine Learning",
            authors="Nguyen Van A",
            year=2024,
            detected_style="APA7",
        )
        second = Citation(
            id=uuid4(),
            raw_text="ref 2",
            title="Machine Learning",
            authors="Tran Thi B",
            year=2024,
            detected_style="APA7",
        )

        match = _find_duplicate_match(second, None, [(first, None)], {})

        self.assertIsNone(match)


if __name__ == "__main__":
    unittest.main()
