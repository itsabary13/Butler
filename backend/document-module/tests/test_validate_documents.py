import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from validate_documents import validate_documents

FIXTURES = Path(__file__).parent / "fixtures"


class TestValidateDocuments(unittest.TestCase):
    def test_valid_document_has_no_errors(self):
        results = validate_documents(FIXTURES / "valid")
        self.assertEqual(results, {}, f"expected no errors, got: {results}")

    def test_missing_field_detected(self):
        results = validate_documents(FIXTURES / "invalid" / "missing-field")
        self.assertTrue(any(
            "missing required frontmatter field: file_extension" in e
            for errs in results.values() for e in errs
        ))

    def test_missing_paired_file_detected(self):
        results = validate_documents(FIXTURES / "invalid" / "missing-file")
        self.assertTrue(any(
            "paired file missing" in e
            for errs in results.values() for e in errs
        ))

    def test_slug_mismatch_detected(self):
        results = validate_documents(FIXTURES / "invalid" / "slug-mismatch")
        self.assertTrue(any(
            "does not match filename" in e
            for errs in results.values() for e in errs
        ))

    def test_nonexistent_directory_is_ok(self):
        results = validate_documents(FIXTURES / "does-not-exist")
        self.assertEqual(results, {})


if __name__ == "__main__":
    unittest.main()
