import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from validate_wiki import validate_wiki

FIXTURES = Path(__file__).parent / "fixtures"


class TestValidateWiki(unittest.TestCase):
    def test_valid_pages_have_no_errors(self):
        results = validate_wiki(FIXTURES / "valid")
        self.assertEqual(results, {}, f"expected no errors, got: {results}")

    def test_missing_field_detected(self):
        results = validate_wiki(FIXTURES / "invalid" / "missing-field")
        self.assertTrue(any(
            "missing required frontmatter field: updated_at" in e
            for errs in results.values() for e in errs
        ))

    def test_empty_content_detected(self):
        results = validate_wiki(FIXTURES / "invalid" / "empty-content")
        self.assertTrue(any(
            "content is empty" in e
            for errs in results.values() for e in errs
        ))

    def test_dangling_link_detected(self):
        results = validate_wiki(FIXTURES / "invalid" / "dangling-link")
        self.assertTrue(any(
            "dangling link" in e
            for errs in results.values() for e in errs
        ))

    def test_bad_timestamps_detected(self):
        results = validate_wiki(FIXTURES / "invalid" / "bad-timestamps")
        self.assertTrue(any(
            "is before created_at" in e
            for errs in results.values() for e in errs
        ))

    def test_slug_mismatch_detected(self):
        results = validate_wiki(FIXTURES / "invalid" / "slug-mismatch")
        self.assertTrue(any(
            "does not match filename" in e
            for errs in results.values() for e in errs
        ))

    def test_valid_tag_is_accepted(self):
        results = validate_wiki(FIXTURES / "valid")
        self.assertNotIn("python-language.md", results)

    def test_invalid_tag_detected(self):
        results = validate_wiki(FIXTURES / "invalid" / "bad-tag")
        self.assertTrue(any(
            "invalid tag" in e
            for errs in results.values() for e in errs
        ))

    def test_nonexistent_directory_is_ok(self):
        results = validate_wiki(FIXTURES / "does-not-exist")
        self.assertEqual(results, {})


if __name__ == "__main__":
    unittest.main()
