"""
extract_paper_height / build_chrome_command / extract_print_scale /
build_sumatra_print_settings のユニットテスト
仕様: docs/adr/0001-dynamic-paper-height.md, docs/adr/0002-print-scale-query.md
"""

import unittest
from printer_service import (
    extract_paper_height,
    build_chrome_command,
    extract_print_scale,
    build_sumatra_print_settings,
)


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


class BuildChromeCommandTest(unittest.TestCase):
    """Chrome 引数組み立てロジックの単体テスト (subprocess を呼ばず純粋関数として検証)"""

    BASE = ['chrome', '--headless=new', '--print-to-pdf-paper-width=3.14961']

    def test_with_paper_height_includes_arg_before_url(self):
        cmd = build_chrome_command(
            self.BASE,
            temp_pdf_path='/tmp/out.pdf',
            paper_height_arg='--print-to-pdf-paper-height=9.84252',
            auth_print_url='http://example.test/label/1?print_token=abc',
        )
        self.assertEqual(cmd, [
            'chrome',
            '--headless=new',
            '--print-to-pdf-paper-width=3.14961',
            '--print-to-pdf=/tmp/out.pdf',
            '--disable-print-preview',
            '--print-to-pdf-paper-height=9.84252',
            'http://example.test/label/1?print_token=abc',
        ])

    def test_without_paper_height_omits_arg(self):
        cmd = build_chrome_command(
            self.BASE,
            temp_pdf_path='/tmp/out.pdf',
            paper_height_arg=None,
            auth_print_url='http://example.test/label/1',
        )
        self.assertEqual(cmd, [
            'chrome',
            '--headless=new',
            '--print-to-pdf-paper-width=3.14961',
            '--print-to-pdf=/tmp/out.pdf',
            '--disable-print-preview',
            'http://example.test/label/1',
        ])
        # paper_height 引数が一切混入していないこと
        for token in cmd:
            self.assertFalse(token.startswith('--print-to-pdf-paper-height'))

    def test_url_is_always_last(self):
        cmd = build_chrome_command(
            self.BASE,
            temp_pdf_path='/tmp/out.pdf',
            paper_height_arg='--print-to-pdf-paper-height=1.96850',
            auth_print_url='http://example.test/x',
        )
        self.assertEqual(cmd[-1], 'http://example.test/x')

    def test_does_not_mutate_base(self):
        base = list(self.BASE)
        build_chrome_command(
            base,
            temp_pdf_path='/tmp/out.pdf',
            paper_height_arg='--print-to-pdf-paper-height=9.84252',
            auth_print_url='http://example.test/',
        )
        self.assertEqual(base, self.BASE)


class ExtractPrintScaleTest(unittest.TestCase):
    """print_scale クエリ抽出ロジックの単体テスト (ADR 0002)"""

    def test_omitted_defaults_to_fit(self):
        url = "http://example.test/print/label/1?print_token=abc"
        cleaned, scale = extract_print_scale(url)
        self.assertEqual(cleaned, url)
        self.assertEqual(scale, 'fit')

    def test_omitted_with_no_query_defaults_to_fit(self):
        url = "http://example.test/print/label/1"
        cleaned, scale = extract_print_scale(url)
        self.assertEqual(cleaned, url)
        self.assertEqual(scale, 'fit')

    def test_noscale_strips_query(self):
        url = "http://example.test/print/label/1?print_scale=noscale"
        cleaned, scale = extract_print_scale(url)
        self.assertEqual(cleaned, "http://example.test/print/label/1")
        self.assertEqual(scale, 'noscale')

    def test_fit_strips_query(self):
        url = "http://example.test/print/label/1?print_scale=fit"
        cleaned, scale = extract_print_scale(url)
        self.assertEqual(cleaned, "http://example.test/print/label/1")
        self.assertEqual(scale, 'fit')

    def test_preserves_other_query_params(self):
        url = "http://example.test/print/label/1?print_token=abc&print_scale=noscale&other=z"
        cleaned, scale = extract_print_scale(url)
        self.assertEqual(cleaned, "http://example.test/print/label/1?print_token=abc&other=z")
        self.assertEqual(scale, 'noscale')

    def test_coexists_with_paper_height_via_chaining(self):
        # 実運用の経路: extract_paper_height で paper_height を除去した URL を
        # extract_print_scale に渡す。両クエリが共存しても双方除去できること。
        url = "http://example.test/label/1?paper_height=auto&print_scale=noscale&print_token=abc"
        cleaned, _, _ = extract_paper_height(url)
        cleaned, scale = extract_print_scale(cleaned)
        self.assertEqual(cleaned, "http://example.test/label/1?print_token=abc")
        self.assertEqual(scale, 'noscale')

    def test_unknown_value_is_rejected(self):
        with self.assertRaises(ValueError):
            extract_print_scale("http://example.test/?print_scale=shrink")

    def test_empty_value_is_rejected(self):
        with self.assertRaises(ValueError):
            extract_print_scale("http://example.test/?print_scale=")

    def test_uppercase_is_rejected(self):
        # 完全一致判定。'Noscale' 等は許容しない (誤送信を握りつぶさない)
        with self.assertRaises(ValueError):
            extract_print_scale("http://example.test/?print_scale=Noscale")

    def test_multiple_print_scale_is_rejected(self):
        with self.assertRaises(ValueError):
            extract_print_scale("http://example.test/?print_scale=fit&print_scale=noscale")

    def test_fragment_is_preserved(self):
        url = "http://example.test/label/1?print_scale=noscale#section"
        cleaned, scale = extract_print_scale(url)
        self.assertEqual(cleaned, "http://example.test/label/1#section")
        self.assertEqual(scale, 'noscale')


class BuildSumatraPrintSettingsTest(unittest.TestCase):
    """SumatraPDF -print-settings 文字列組み立ての単体テスト (ADR 0002)"""

    def test_noscale(self):
        self.assertEqual(
            build_sumatra_print_settings('noscale'),
            'paper=MKラベル,portrait,noscale',
        )

    def test_fit(self):
        self.assertEqual(
            build_sumatra_print_settings('fit'),
            'paper=MKラベル,portrait,fit',
        )

    def test_fixed_prefix_is_unchanged(self):
        # 用紙フォーム名・向きの固定部が回帰しないことを保証
        for scale in ('fit', 'noscale'):
            self.assertTrue(
                build_sumatra_print_settings(scale).startswith('paper=MKラベル,portrait,')
            )


if __name__ == '__main__':
    unittest.main()
