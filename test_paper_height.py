"""
extract_paper_height のユニットテスト
仕様: docs/adr/0001-dynamic-paper-height.md
"""

import unittest
from printer_service import extract_paper_height


class ExtractPaperHeightTest(unittest.TestCase):

    def test_omitted_query_returns_url_unchanged(self):
        url = "http://example.test/print/label/1?print_token=abc"
        cleaned, arg, label = extract_paper_height(url)
        self.assertEqual(cleaned, url)
        self.assertIsNone(arg)
        self.assertEqual(label, 'omitted')

    def test_omitted_with_no_query(self):
        url = "http://example.test/print/label/1"
        cleaned, arg, label = extract_paper_height(url)
        self.assertEqual(cleaned, url)
        self.assertIsNone(arg)
        self.assertEqual(label, 'omitted')

    def test_auto_strips_query_and_omits_arg(self):
        url = "http://example.test/print/label/1?paper_height=auto"
        cleaned, arg, label = extract_paper_height(url)
        self.assertEqual(cleaned, "http://example.test/print/label/1")
        self.assertIsNone(arg)
        self.assertEqual(label, 'auto')

    def test_auto_preserves_other_query_params(self):
        url = "http://example.test/print/label/1?print_token=abc&paper_height=auto&other=z"
        cleaned, arg, label = extract_paper_height(url)
        self.assertEqual(cleaned, "http://example.test/print/label/1?print_token=abc&other=z")
        self.assertIsNone(arg)
        self.assertEqual(label, 'auto')

    def test_numeric_250mm_converts_to_inch(self):
        url = "http://example.test/print/label/1?paper_height=250"
        cleaned, arg, label = extract_paper_height(url)
        self.assertEqual(cleaned, "http://example.test/print/label/1")
        self.assertEqual(arg, "--print-to-pdf-paper-height=9.84252")
        self.assertEqual(label, '250mm')

    def test_numeric_lower_bound_1mm(self):
        url = "http://example.test/?paper_height=1"
        _, arg, label = extract_paper_height(url)
        self.assertEqual(arg, "--print-to-pdf-paper-height=0.03937")
        self.assertEqual(label, '1mm')

    def test_numeric_upper_bound_3000mm(self):
        url = "http://example.test/?paper_height=3000"
        _, arg, label = extract_paper_height(url)
        self.assertEqual(arg, "--print-to-pdf-paper-height=118.11024")
        self.assertEqual(label, '3000mm')

    def test_numeric_strips_query_preserves_others(self):
        url = "http://example.test/print/label/1?print_token=abc&paper_height=250"
        cleaned, _, _ = extract_paper_height(url)
        self.assertEqual(cleaned, "http://example.test/print/label/1?print_token=abc")

    def test_zero_is_rejected(self):
        with self.assertRaises(ValueError):
            extract_paper_height("http://example.test/?paper_height=0")

    def test_negative_is_rejected(self):
        with self.assertRaises(ValueError):
            extract_paper_height("http://example.test/?paper_height=-1")

    def test_over_max_is_rejected(self):
        with self.assertRaises(ValueError):
            extract_paper_height("http://example.test/?paper_height=3001")

    def test_non_numeric_is_rejected(self):
        with self.assertRaises(ValueError):
            extract_paper_height("http://example.test/?paper_height=abc")

    def test_decimal_is_rejected(self):
        with self.assertRaises(ValueError):
            extract_paper_height("http://example.test/?paper_height=250.5")

    def test_empty_value_is_rejected(self):
        with self.assertRaises(ValueError):
            extract_paper_height("http://example.test/?paper_height=")

    def test_multiple_paper_height_is_rejected(self):
        with self.assertRaises(ValueError):
            extract_paper_height("http://example.test/?paper_height=250&paper_height=auto")

    def test_url_with_fragment_is_preserved(self):
        url = "http://example.test/print/label/1?paper_height=auto#section"
        cleaned, _, _ = extract_paper_height(url)
        self.assertEqual(cleaned, "http://example.test/print/label/1#section")


if __name__ == '__main__':
    unittest.main()
