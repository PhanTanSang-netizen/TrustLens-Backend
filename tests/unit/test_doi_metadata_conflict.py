import unittest

from app.core.enums.metadata_status import MetadataStatus
from app.processing.metadata.metadata_matcher import MetadataCandidate, normalize_doi, select_best_metadata_match


class DoiMetadataConflictTests(unittest.TestCase):
    def test_exact_doi_with_wrong_title_is_metadata_conflict(self) -> None:
        result = select_best_metadata_match(
            citation_title="Deep learning for malware detection",
            citation_authors="Nguyen Van A",
            citation_year=2024,
            citation_doi="https://doi.org/10.1234/example",
            candidates=[
                MetadataCandidate(
                    provider="Crossref",
                    source_url="https://doi.org/10.1234/example",
                    doi="10.1234/example",
                    title="Marine biology and coral reef conservation",
                    authors="Tran Thi B",
                    year=2017,
                    venue="Ocean Journal",
                    publisher="Example Publisher",
                    source_type="journal-article",
                    citation_count=1,
                    raw_response={},
                )
            ],
        )

        self.assertIsNotNone(result)
        self.assertEqual(result.match_status, MetadataStatus.IDENTIFIER_METADATA_CONFLICT)
        self.assertTrue(result.evidence["doi_exact_match"])
        self.assertEqual(result.evidence["bibliographic_consistency"], "CONFLICT")

    def test_exact_doi_with_missing_title_is_partial_match(self) -> None:
        result = select_best_metadata_match(
            citation_title=None,
            citation_authors="Nguyen Van A",
            citation_year=2024,
            citation_doi="doi:10.1234/example",
            candidates=[
                MetadataCandidate(
                    provider="Crossref",
                    source_url="https://doi.org/10.1234/example",
                    doi="10.1234/example",
                    title="Deep learning for malware detection",
                    authors="Nguyen Van A",
                    year=2024,
                    venue="Security Journal",
                    publisher="Example Publisher",
                    source_type="journal-article",
                    citation_count=1,
                    raw_response={},
                )
            ],
        )

        self.assertIsNotNone(result)
        self.assertEqual(result.match_status, MetadataStatus.PARTIAL_MATCH)
        self.assertEqual(normalize_doi("https://doi.org/10.1234/example"), normalize_doi("doi:10.1234/example"))


if __name__ == "__main__":
    unittest.main()
