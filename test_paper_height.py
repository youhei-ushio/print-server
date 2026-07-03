"""
extract_paper_height / build_chrome_command / extract_print_scale /
build_sumatra_print_settings のユニットテスト
仕様: docs/adr/0001-dynamic-paper-height.md, docs/adr/0002-print-scale-query.md
"""

import unittest
from printer_service import (
    extract_paper_height,
    extract_paper_width,
    build_paper_width_default,
    build_chrome_command,
    extract_print_scale,
    build_sumatra_print_settings,
    resolve_paper_name,
    _parse_mm_from_label,
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

    BASE = ['chrome', '--headless=new']

    def test_with_paper_height_includes_arg_before_url(self):
        cmd = build_chrome_command(
            self.BASE,
            temp_pdf_path='/tmp/out.pdf',
            paper_width_arg=None,
            paper_height_arg='--print-to-pdf-paper-height=9.84252',
            auth_print_url='http://example.test/label/1?print_token=abc',
        )
        self.assertEqual(cmd, [
            'chrome',
            '--headless=new',
            '--print-to-pdf=/tmp/out.pdf',
            '--disable-print-preview',
            '--print-to-pdf-paper-height=9.84252',
            'http://example.test/label/1?print_token=abc',
        ])

    def test_without_paper_height_omits_arg(self):
        cmd = build_chrome_command(
            self.BASE,
            temp_pdf_path='/tmp/out.pdf',
            paper_width_arg=None,
            paper_height_arg=None,
            auth_print_url='http://example.test/label/1',
        )
        self.assertEqual(cmd, [
            'chrome',
            '--headless=new',
            '--print-to-pdf=/tmp/out.pdf',
            '--disable-print-preview',
            'http://example.test/label/1',
        ])
        for token in cmd:
            self.assertFalse(token.startswith('--print-to-pdf-paper-height'))

    def test_with_both_width_and_height(self):
        cmd = build_chrome_command(
            self.BASE,
            temp_pdf_path='/tmp/out.pdf',
            paper_width_arg='--print-to-pdf-paper-width=7.16535',
            paper_height_arg='--print-to-pdf-paper-height=10.11811',
            auth_print_url='http://example.test/label/1',
        )
        self.assertIn('--print-to-pdf-paper-width=7.16535', cmd)
        self.assertIn('--print-to-pdf-paper-height=10.11811', cmd)
        self.assertEqual(cmd[-1], 'http://example.test/label/1')

    def test_url_is_always_last(self):
        cmd = build_chrome_command(
            self.BASE,
            temp_pdf_path='/tmp/out.pdf',
            paper_width_arg=None,
            paper_height_arg='--print-to-pdf-paper-height=1.96850',
            auth_print_url='http://example.test/x',
        )
        self.assertEqual(cmd[-1], 'http://example.test/x')

    def test_does_not_mutate_base(self):
        base = list(self.BASE)
        build_chrome_command(
            base,
            temp_pdf_path='/tmp/out.pdf',
            paper_width_arg=None,
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

    def test_whitespace_only_is_rejected(self):
        # %20 のみ → strip 後に空文字となり許容値に一致しない
        with self.assertRaises(ValueError):
            extract_print_scale("http://example.test/?print_scale=%20")

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


class ExtractPaperWidthTest(unittest.TestCase):
    """extract_paper_width の単体テスト (Issue #2589)"""

    def test_omitted_query_returns_url_unchanged(self):
        url = "http://example.test/print/label/1?print_token=abc"
        cleaned, arg, label = extract_paper_width(url)
        self.assertEqual(cleaned, url)
        self.assertIsNone(arg)
        self.assertEqual(label, 'omitted')

    def test_auto_strips_query_and_omits_arg(self):
        url = "http://example.test/print/label/1?paper_width=auto"
        cleaned, arg, label = extract_paper_width(url)
        self.assertEqual(cleaned, "http://example.test/print/label/1")
        self.assertIsNone(arg)
        self.assertEqual(label, 'auto')

    def test_numeric_182mm_b5_converts_to_inch(self):
        url = "http://example.test/?paper_width=182"
        cleaned, arg, label = extract_paper_width(url)
        self.assertEqual(arg, "--print-to-pdf-paper-width=7.16535")
        self.assertEqual(label, '182mm')

    def test_numeric_lower_bound_1mm(self):
        _, arg, label = extract_paper_width("http://example.test/?paper_width=1")
        self.assertEqual(arg, "--print-to-pdf-paper-width=0.03937")
        self.assertEqual(label, '1mm')

    def test_numeric_upper_bound_3000mm(self):
        _, arg, label = extract_paper_width("http://example.test/?paper_width=3000")
        self.assertEqual(arg, "--print-to-pdf-paper-width=118.11024")
        self.assertEqual(label, '3000mm')

    def test_zero_is_rejected(self):
        with self.assertRaises(ValueError):
            extract_paper_width("http://example.test/?paper_width=0")

    def test_over_max_is_rejected(self):
        with self.assertRaises(ValueError):
            extract_paper_width("http://example.test/?paper_width=3001")

    def test_non_numeric_is_rejected(self):
        with self.assertRaises(ValueError):
            extract_paper_width("http://example.test/?paper_width=abc")

    def test_multiple_paper_width_is_rejected(self):
        with self.assertRaises(ValueError):
            extract_paper_width("http://example.test/?paper_width=182&paper_width=auto")

    def test_preserves_other_query_params(self):
        url = "http://example.test/?print_token=abc&paper_width=182&other=z"
        cleaned, _, _ = extract_paper_width(url)
        self.assertEqual(cleaned, "http://example.test/?print_token=abc&other=z")

    def test_coexists_with_paper_height_via_chaining(self):
        url = "http://example.test/?paper_width=182&paper_height=257&print_token=abc"
        cleaned, w_arg, _ = extract_paper_width(url)
        cleaned, h_arg, _ = extract_paper_height(cleaned)
        self.assertEqual(cleaned, "http://example.test/?print_token=abc")
        self.assertIn('7.16535', w_arg)
        self.assertIn('10.11811', h_arg)


class BuildPaperWidthDefaultTest(unittest.TestCase):
    """build_paper_width_default の単体テスト (Issue #2589)"""

    def test_label_returns_80mm_default(self):
        arg = build_paper_width_default('Label')
        self.assertEqual(arg, '--print-to-pdf-paper-width=3.14961')

    def test_standard_returns_none(self):
        self.assertIsNone(build_paper_width_default('Standard'))

    def test_none_returns_none(self):
        self.assertIsNone(build_paper_width_default(None))

    def test_empty_string_returns_none(self):
        self.assertIsNone(build_paper_width_default(''))


class BuildSumatraPrintSettingsTest(unittest.TestCase):
    """SumatraPDF -print-settings 文字列組み立ての単体テスト (ADR 0002, Issue #2589)"""

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
        for scale in ('fit', 'noscale'):
            self.assertTrue(
                build_sumatra_print_settings(scale).startswith('paper=MKラベル,portrait,')
            )

    def test_label_includes_paper_form(self):
        self.assertEqual(
            build_sumatra_print_settings('fit', 'Label'),
            'paper=MKラベル,portrait,fit',
        )

    def test_standard_omits_paper_form(self):
        self.assertEqual(
            build_sumatra_print_settings('fit', 'Standard'),
            'portrait,fit',
        )

    def test_standard_noscale(self):
        self.assertEqual(
            build_sumatra_print_settings('noscale', 'Standard'),
            'portrait,noscale',
        )

    def test_none_printer_type_treated_as_standard(self):
        result = build_sumatra_print_settings('fit', None)
        self.assertEqual(result, 'portrait,fit')

    def test_standard_with_paper_name_b5(self):
        self.assertEqual(
            build_sumatra_print_settings('fit', 'Standard', 'B5 (JIS)'),
            'paper=B5 (JIS),portrait,fit',
        )

    def test_standard_with_paper_name_a4(self):
        self.assertEqual(
            build_sumatra_print_settings('noscale', 'Standard', 'A4'),
            'paper=A4,portrait,noscale',
        )

    def test_label_ignores_paper_name(self):
        self.assertEqual(
            build_sumatra_print_settings('fit', 'Label', 'B5 (JIS)'),
            'paper=MKラベル,portrait,fit',
        )

    def test_standard_without_paper_name(self):
        self.assertEqual(
            build_sumatra_print_settings('fit', 'Standard', None),
            'portrait,fit',
        )


class ResolvePaperNameTest(unittest.TestCase):
    """resolve_paper_name の単体テスト (Issue #5)"""

    def test_b5_portrait(self):
        self.assertEqual(resolve_paper_name(182, 257), 'B5 (JIS)')

    def test_b5_landscape(self):
        self.assertEqual(resolve_paper_name(257, 182), 'B5 (JIS)')

    def test_a4_portrait(self):
        self.assertEqual(resolve_paper_name(210, 297), 'A4')

    def test_a4_landscape(self):
        self.assertEqual(resolve_paper_name(297, 210), 'A4')

    def test_a5_portrait(self):
        self.assertEqual(resolve_paper_name(148, 210), 'A5')

    def test_b4_portrait(self):
        self.assertEqual(resolve_paper_name(257, 364), 'B4 (JIS)')

    def test_unknown_size_returns_none(self):
        self.assertIsNone(resolve_paper_name(100, 200))

    def test_none_width_returns_none(self):
        self.assertIsNone(resolve_paper_name(None, 257))

    def test_none_height_returns_none(self):
        self.assertIsNone(resolve_paper_name(182, None))

    def test_both_none_returns_none(self):
        self.assertIsNone(resolve_paper_name(None, None))


class ParseMmFromLabelTest(unittest.TestCase):
    """_parse_mm_from_label の単体テスト (Issue #5)"""

    def test_valid_mm_label(self):
        self.assertEqual(_parse_mm_from_label('182mm'), 182)

    def test_valid_mm_label_257(self):
        self.assertEqual(_parse_mm_from_label('257mm'), 257)

    def test_omitted_returns_none(self):
        self.assertIsNone(_parse_mm_from_label('omitted'))

    def test_auto_returns_none(self):
        self.assertIsNone(_parse_mm_from_label('auto'))

    def test_default_returns_none(self):
        self.assertIsNone(_parse_mm_from_label('default'))

    def test_omitted_standard_returns_none(self):
        self.assertIsNone(_parse_mm_from_label('omitted(Standard)'))


if __name__ == '__main__':
    unittest.main()
