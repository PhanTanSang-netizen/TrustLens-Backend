import unittest

from app.core.enums.metadata_status import MetadataStatus, normalize_metadata_status


class MetadataStatusTests(unittest.TestCase):
    def test_legacy_academic_statuses_map_to_normalized_values(self) -> None:
        self.assertEqual(normalize_metadata_status("ACADEMIC_VERIFIED"), MetadataStatus.VERIFIED)
        self.assertEqual(normalize_metadata_status("ACADEMIC_PARTIAL_MATCH"), MetadataStatus.PARTIAL_MATCH)
        self.assertEqual(normalize_metadata_status("ACADEMIC_AMBIGUOUS"), MetadataStatus.AMBIGUOUS)
        self.assertEqual(normalize_metadata_status("ACADEMIC_NOT_FOUND"), MetadataStatus.NOT_FOUND)

    def test_provider_unavailable_is_not_not_found(self) -> None:
        self.assertEqual(normalize_metadata_status("unknown"), MetadataStatus.PROVIDER_UNAVAILABLE)
        self.assertNotEqual(normalize_metadata_status("unknown"), MetadataStatus.NOT_FOUND)

    def test_url_ok_maps_to_url_only(self) -> None:
        self.assertEqual(normalize_metadata_status("URL_OK"), MetadataStatus.URL_ONLY)

    def test_doi_conflict_maps_to_identifier_metadata_conflict(self) -> None:
        self.assertEqual(normalize_metadata_status("DOI_CONFLICT"), MetadataStatus.IDENTIFIER_METADATA_CONFLICT)
        self.assertEqual(
            normalize_metadata_status("IDENTIFIER_METADATA_CONFLICT"),
            MetadataStatus.IDENTIFIER_METADATA_CONFLICT,
        )


if __name__ == "__main__":
    unittest.main()
