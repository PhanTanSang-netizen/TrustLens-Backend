import unittest

from app.core.enums.publication_status import PublicationStatus
from app.services.publication_status_service import evaluate_publication_status


class PublicationStatusTests(unittest.TestCase):
    def test_crossref_retraction_update_promotes_retracted(self) -> None:
        result = evaluate_publication_status(
            "Crossref",
            {
                "update-to": [
                    {
                        "type": "retraction",
                        "DOI": "10.1234/notice",
                        "source": "retraction-watch",
                    }
                ]
            },
        )

        self.assertEqual(result.publication_status, PublicationStatus.RETRACTED)
        self.assertTrue(result.is_retracted)
        self.assertEqual(result.retraction_sources[0]["notice_doi"], "10.1234/notice")

    def test_openalex_retraction_promotes_retracted(self) -> None:
        result = evaluate_publication_status("OpenAlex", {"is_retracted": True})

        self.assertEqual(result.publication_status, PublicationStatus.RETRACTED)
        self.assertTrue(result.is_retracted)

    def test_provider_error_is_unknown_not_active(self) -> None:
        result = evaluate_publication_status("Crossref", None, provider_error="TIMEOUT")

        self.assertEqual(result.publication_status, PublicationStatus.UNKNOWN)
        self.assertIn("PUBLICATION_STATUS_PROVIDER_UNAVAILABLE", result.warnings)


if __name__ == "__main__":
    unittest.main()
