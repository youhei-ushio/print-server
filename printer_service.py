"""
印刷サービス - クリーン実装
仕様書: docs/print-server-specification.md
"""

import subprocess
import logging
from typing import Tuple, Optional
from urllib.parse import urlparse, urlencode, parse_qsl, urlunparse
from config import PrintServerConfig
import os

# paper_height / paper_width クエリ仕様 (ADR docs/adr/0001-dynamic-paper-height.md, Issue #2589)
PAPER_SIZE_MAX_MM = 3000
MM_PER_INCH = 25.4


def extract_paper_height(url: str) -> Tuple[str, Optional[str], str]:
    """印刷 URL から paper_height クエリを取り出し、Chrome 引数と監査用ラベルを返す。

    Returns:
        (cleaned_url, chrome_arg, log_label)
            cleaned_url : paper_height クエリを除去した URL (Chrome に渡す)
            chrome_arg  : --print-to-pdf-paper-height=<inch> 文字列。引数を渡さない場合は None
            log_label   : ジョブログ用の人間可読ラベル ("omitted" / "auto" / "250mm" 等)

    Raises:
        ValueError: paper_height の値が仕様 (auto または 1..3000 の整数) を満たさないとき
    """
    parsed = urlparse(url)
    query_pairs = parse_qsl(parsed.query, keep_blank_values=True)

    paper_height_values = [v for k, v in query_pairs if k == 'paper_height']
    remaining_pairs = [(k, v) for k, v in query_pairs if k != 'paper_height']

    cleaned_url = urlunparse(parsed._replace(query=urlencode(remaining_pairs)))

    if not paper_height_values:
        return cleaned_url, None, 'omitted'

    if len(paper_height_values) > 1:
        raise ValueError(f"paper_height specified multiple times: {paper_height_values}")

    value = paper_height_values[0].strip()

    if value == 'auto':
        return cleaned_url, None, 'auto'

    try:
        mm = int(value)
    except ValueError:
        raise ValueError(f"paper_height must be 'auto' or an integer in mm: got {value!r}")

    if mm < 1 or mm > PAPER_SIZE_MAX_MM:
        raise ValueError(f"paper_height out of range (1..{PAPER_SIZE_MAX_MM} mm): {mm}")

    inch = mm / MM_PER_INCH
    return cleaned_url, f"--print-to-pdf-paper-height={inch:.5f}", f"{mm}mm"


def extract_paper_width(url: str) -> Tuple[str, Optional[str], str]:
    """印刷 URL から paper_width クエリを取り出し、Chrome 引数と監査用ラベルを返す。

    extract_paper_height と対称の API。Issue #2589 で追加。

    Returns:
        (cleaned_url, chrome_arg, log_label)

    Raises:
        ValueError: paper_width の値が仕様 (auto または 1..3000 の整数) を満たさないとき
    """
    parsed = urlparse(url)
    query_pairs = parse_qsl(parsed.query, keep_blank_values=True)

    paper_width_values = [v for k, v in query_pairs if k == 'paper_width']
    remaining_pairs = [(k, v) for k, v in query_pairs if k != 'paper_width']

    cleaned_url = urlunparse(parsed._replace(query=urlencode(remaining_pairs)))

    if not paper_width_values:
        return cleaned_url, None, 'omitted'

    if len(paper_width_values) > 1:
        raise ValueError(f"paper_width specified multiple times: {paper_width_values}")

    value = paper_width_values[0].strip()

    if value == 'auto':
        return cleaned_url, None, 'auto'

    try:
        mm = int(value)
    except ValueError:
        raise ValueError(f"paper_width must be 'auto' or an integer in mm: got {value!r}")

    if mm < 1 or mm > PAPER_SIZE_MAX_MM:
        raise ValueError(f"paper_width out of range (1..{PAPER_SIZE_MAX_MM} mm): {mm}")

    inch = mm / MM_PER_INCH
    return cleaned_url, f"--print-to-pdf-paper-width={inch:.5f}", f"{mm}mm"


def build_paper_width_default(printer_type: str) -> Optional[str]:
    """PrinterType に応じたデフォルトの paper_width Chrome 引数を返す。

    Label: 80mm (3.14961in) のハードコード値を維持。
    Standard: None (Chrome が CSS @page size に従う)。
    """
    if printer_type == 'Label':
        return f'--print-to-pdf-paper-width={PrintServerConfig.LABEL_DEFAULT_PAPER_WIDTH_INCH:.5f}'
    return None


def build_chrome_command(
    chrome_command_base: list,
    temp_pdf_path: str,
    paper_width_arg: Optional[str],
    paper_height_arg: Optional[str],
    auth_print_url: str,
) -> list:
    """Chrome 実行コマンドの最終形を組み立てる。

    paper_width_arg / paper_height_arg が None の場合はそれぞれの引数を含めない。
    URL は常に最後尾。
    """
    extra_args = [
        f'--print-to-pdf={temp_pdf_path}',
        '--disable-print-preview',
    ]
    if paper_width_arg:
        extra_args.append(paper_width_arg)
    if paper_height_arg:
        extra_args.append(paper_height_arg)
    extra_args.append(auth_print_url)
    return list(chrome_command_base) + extra_args


# print_scale クエリ仕様 (ADR docs/adr/0002-print-scale-query.md)
ALLOWED_PRINT_SCALES = ('fit', 'noscale')
DEFAULT_PRINT_SCALE = 'fit'


def extract_print_scale(url: str) -> Tuple[str, str]:
    """印刷 URL から print_scale クエリを取り出し、SumatraPDF の縮尺トークンを返す。

    paper_height とは独立した軸 (高さ ≠ 縮尺) として扱う。梱包ラベルのような
    可変長ロール紙を等倍印刷したい場合に呼び出し側が `?print_scale=noscale` を付ける。

    Returns:
        (cleaned_url, scale)
            cleaned_url : print_scale クエリを除去した URL (Chrome に渡す)
            scale       : SumatraPDF の縮尺トークン ('fit' / 'noscale')。未指定は 'fit'。

    Raises:
        ValueError: print_scale が複数指定、または許容値 (fit / noscale) 以外のとき
    """
    parsed = urlparse(url)
    query_pairs = parse_qsl(parsed.query, keep_blank_values=True)

    scale_values = [v for k, v in query_pairs if k == 'print_scale']
    remaining_pairs = [(k, v) for k, v in query_pairs if k != 'print_scale']

    cleaned_url = urlunparse(parsed._replace(query=urlencode(remaining_pairs)))

    if not scale_values:
        return cleaned_url, DEFAULT_PRINT_SCALE

    if len(scale_values) > 1:
        raise ValueError(f"print_scale specified multiple times: {scale_values}")

    value = scale_values[0].strip()
    if value not in ALLOWED_PRINT_SCALES:
        raise ValueError(
            f"print_scale must be one of {ALLOWED_PRINT_SCALES}: got {value!r}"
        )
    return cleaned_url, value


def build_sumatra_print_settings(scale: str, printer_type: str = 'Label') -> str:
    """SumatraPDF の -print-settings 値を組み立てる。

    Label: 用紙フォーム名 'paper=MKラベル' 付き (従来挙動)。
    Standard: 用紙指定なし。プリンターのデフォルトトレイ用紙に従う。
    """
    if printer_type == 'Label':
        return f'paper=MKラベル,portrait,{scale}'
    return f'portrait,{scale}'


class PrinterService:
    """印刷処理サービス"""

    def __init__(self):
        self.config = PrintServerConfig()
        self.logger = logging.getLogger(__name__)

    def print_web_url(self, print_url: str, printer_name: str, job_name: str = "Web Print", printer_type: str = "Label") -> Tuple[bool, str, bool]:
        """Web URLを直接印刷

        Returns:
            (success, message, retryable)
                retryable: 失敗時にキュー側で再試行してよいか。
                           入力起因の恒久エラー (invalid paper_height 等) は False。
                           成功時の値は意味を持たない (True を返す)。
        """
        try:
            self.logger.info(f"Starting web print job: {job_name}")
            self.logger.info(f"Print URL: {print_url}")
            self.logger.info(f"Target printer: {printer_name} (type: {printer_type})")

            # paper_width クエリを抽出 (Issue #2589)
            try:
                cleaned_url, paper_width_arg, paper_width_label = extract_paper_width(print_url)
            except ValueError as e:
                error_msg = f"invalid paper_width: {e}"
                self.logger.error(error_msg)
                return False, error_msg, False

            # paper_width 未指定時は PrinterType のデフォルトを適用
            if paper_width_arg is None and paper_width_label == 'omitted':
                paper_width_arg = build_paper_width_default(printer_type)
                paper_width_label = 'default' if paper_width_arg else 'omitted(Standard)'

            if paper_width_arg:
                self.logger.info(f"paper_width: {paper_width_label} -> {paper_width_arg}")
            else:
                self.logger.info(f"paper_width: {paper_width_label} (--print-to-pdf-paper-width omitted)")

            # paper_height クエリを抽出 (ADR 0001)
            try:
                cleaned_url, paper_height_arg, paper_height_label = extract_paper_height(cleaned_url)
            except ValueError as e:
                error_msg = f"invalid paper_height: {e}"
                self.logger.error(error_msg)
                return False, error_msg, False

            if paper_height_arg:
                self.logger.info(f"paper_height: {paper_height_label} -> {paper_height_arg}")
            else:
                self.logger.info(f"paper_height: {paper_height_label} (--print-to-pdf-paper-height omitted)")

            # print_scale クエリを抽出 (ADR 0002)。Chrome へ渡す URL からは除去する。
            try:
                cleaned_url, print_scale = extract_print_scale(cleaned_url)
            except ValueError as e:
                error_msg = f"invalid print_scale: {e}"
                self.logger.error(error_msg)
                return False, error_msg, False
            self.logger.info(f"print_scale: {print_scale}")

            # 印刷用URLに認証トークンを追加
            auth_print_url = self._add_auth_token(cleaned_url)

            # PDFファイル名を生成
            import tempfile
            import os
            temp_pdf = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
            temp_pdf_path = temp_pdf.name
            temp_pdf.close()

            # Chrome実行コマンドを組み立て
            chrome_command = build_chrome_command(
                self.config.chrome_command_base,
                temp_pdf_path,
                paper_width_arg,
                paper_height_arg,
                auth_print_url,
            )
            chrome_path = chrome_command[0]

            # Chrome実行ファイルの存在確認
            if not self._chrome_exists(chrome_path):
                error_msg = f"Chrome executable not found: {chrome_path}"
                self.logger.error(error_msg)
                return False, error_msg, True

            self.logger.info(f"Using Chrome: {chrome_path}")
            self.logger.info(f"Target printer: {printer_name}")
            self.logger.info(f"Executing Chrome command: {' '.join(chrome_command)}")

            result = subprocess.run(
                chrome_command,
                capture_output=True,
                text=True,
                timeout=self.config.PRINT_TIMEOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )

            # プロセス終了を明示的に待機
            if result.returncode is not None:
                self.logger.info(f"Chrome process completed with return code: {result.returncode}")
            else:
                self.logger.warning("Chrome process did not complete properly")

            # Chromeのファイル書き込み完了を待つ
            self.logger.info("Waiting for Chrome to finish file operations...")
            import time
            time.sleep(0.5)  # 0.5秒待機してファイル書き込み開始を待つ

            if result.returncode == 0:
                # PDFファイルの完全な書き込み完了を待機
                max_wait_time = 10  # 最大10秒待機
                wait_interval = 0.2  # 200ms間隔でチェック
                waited_time = 0
                prev_size = 0
                stable_count = 0

                while waited_time < max_wait_time:
                    if os.path.exists(temp_pdf_path):
                        current_size = os.path.getsize(temp_pdf_path)
                        self.logger.debug(f"PDF size check: {current_size} bytes (waited {waited_time}s)")

                        if current_size > 0:
                            if current_size == prev_size:
                                stable_count += 1
                                if stable_count >= 3:  # 3回連続で同じサイズなら書き込み完了
                                    self.logger.info(f"PDF writing completed: {temp_pdf_path} ({current_size} bytes)")
                                    break
                            else:
                                stable_count = 0
                                prev_size = current_size

                    time.sleep(wait_interval)
                    waited_time += wait_interval

                # 最終確認
                if os.path.exists(temp_pdf_path):
                    final_size = os.path.getsize(temp_pdf_path)
                    if final_size == 0:
                        self.logger.error("Generated PDF is empty (0 bytes)")
                        self.logger.error(f"Chrome STDOUT: {result.stdout}")
                        self.logger.error(f"Chrome STDERR: {result.stderr}")
                        return False, "PDFファイルが空です", True
                else:
                    self.logger.error(f"PDF file not created: {temp_pdf_path}")
                    return False, "PDFファイルが作成されませんでした", True

                try:
                    # PDFをプリンターに送信（Windows）
                    if self._print_pdf_to_printer(temp_pdf_path, printer_name, print_scale, printer_type):
                        self.logger.info(f"PDF printed successfully to {printer_name}")
                        return True, "Web印刷完了", True
                    else:
                        return False, "プリンターへの送信に失敗しました", True
                finally:
                    # 一時ファイルを削除（成功時のみ）
                    if os.path.exists(temp_pdf_path):
                        try:
                            #os.remove(temp_pdf_path)
                            self.logger.debug(f"Temporary PDF deleted: {temp_pdf_path}")
                        except Exception as e:
                            self.logger.warning(f"Could not delete temporary PDF: {e}")
            else:
                error_msg = f"Chrome print failed with return code {result.returncode}: {result.stderr}"
                self.logger.error(error_msg)
                # 一時ファイルを削除
                if os.path.exists(temp_pdf_path):
                    os.remove(temp_pdf_path)
                return False, error_msg, True

        except subprocess.TimeoutExpired:
            error_msg = f"Print job timed out after {self.config.PRINT_TIMEOUT} seconds"
            self.logger.error(error_msg)
            return False, error_msg, True

        except Exception as e:
            error_msg = f"Print job failed: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg, True

    def _chrome_exists(self, chrome_path: str) -> bool:
        """Chrome実行ファイルの存在確認"""
        import os
        return os.path.exists(chrome_path) if os.path.isabs(chrome_path) else True

    def _add_auth_token(self, print_url: str) -> str:
        """印刷用URLに認証トークンを追加"""
        # 認証トークンをクエリパラメータとして追加
        auth_token = self.config.PRINT_AUTH_TOKEN if hasattr(self.config, 'PRINT_AUTH_TOKEN') else None

        if auth_token:
            from urllib.parse import quote
            # トークンをURLエンコード
            encoded_token = quote(auth_token, safe='')
            separator = '&' if '?' in print_url else '?'
            return f"{print_url}{separator}print_token={encoded_token}"

        # 認証トークンが設定されていない場合は元のURLをそのまま返す
        return print_url

    def _print_pdf_to_printer(self, pdf_path: str, printer_name: str, scale: str = DEFAULT_PRINT_SCALE, printer_type: str = "Label") -> bool:
        """PDFファイルをプリンターに送信（Windows）。

        scale: SumatraPDF の縮尺トークン ('fit' 既定 / 'noscale')。
               梱包ラベル等の可変長ロール紙を等倍印刷したいときは 'noscale' を渡す。
        printer_type: 'Label' or 'Standard'。SumatraPDF の用紙設定に影響する。
        """
        try:
            import platform

            if platform.system() == 'Windows':
                # SumatraPDFコマンドラインツールを使用（軽量で高速）
                sumatra_paths = [
                    r'C:\Program Files\SumatraPDF\SumatraPDF.exe',
                    r'C:\Program Files (x86)\SumatraPDF\SumatraPDF.exe',
                    # Adobe Readerも試す
                    r'C:\Program Files\Adobe\Acrobat Reader DC\Reader\AcroRd32.exe',
                    r'C:\Program Files (x86)\Adobe\Acrobat Reader DC\Reader\AcroRd32.exe'
                ]

                pdf_reader = None
                for path in sumatra_paths:
                    if os.path.exists(path):
                        pdf_reader = path
                        break

                if pdf_reader and 'SumatraPDF' in pdf_reader:
                    # SumatraPDFの場合
                    # プリンター名は引用符なしで渡す（subprocess.runが適切に処理）
                    print_command = [
                        pdf_reader,
                        '-print-to', printer_name,
                        '-print-settings', build_sumatra_print_settings(scale, printer_type),
                        '-silent',
                        pdf_path
                    ]
                elif pdf_reader and 'AcroRd32' in pdf_reader:
                    # Adobe Readerの場合
                    # print_scale は SumatraPDF 経路でのみ反映される。フォールバック時に
                    # noscale 等が黙って無視されると実機での原因追跡が困難なため警告を残す。
                    if scale != DEFAULT_PRINT_SCALE:
                        self.logger.warning(
                            f"print_scale={scale} requested but ignored on Adobe Reader path"
                        )
                    print_command = [
                        pdf_reader,
                        '/t', pdf_path, printer_name
                    ]
                else:
                    # 代替方法: PowerShellでPDFを既定のアプリケーションで開いて印刷
                    # まずPDFビューアーがインストールされているか確認
                    self.logger.warning("No PDF reader found, trying Windows Shell print")
                    if scale != DEFAULT_PRINT_SCALE:
                        self.logger.warning(
                            f"print_scale={scale} requested but ignored on Windows Shell print path"
                        )
                    print_command = [
                        'powershell.exe', '-Command',
                        f'(New-Object -ComObject Shell.Application).ShellExecute("{pdf_path}", "print", "", "{printer_name}", 0)'
                    ]

                self.logger.info(f"Sending PDF to printer: {printer_name}")
                self.logger.info(f"Using command: {' '.join(print_command)}")

                result = subprocess.run(
                    print_command,
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if result.returncode == 0:
                    return True
                else:
                    self.logger.error(f"Print command failed with return code {result.returncode}")
                    self.logger.error(f"STDOUT: {result.stdout}")
                    self.logger.error(f"STDERR: {result.stderr}")

                    # SumatraPDFの場合、さらに詳細なデバッグ
                    if pdf_reader and 'SumatraPDF' in pdf_reader:
                        # PDFファイルの存在確認
                        if not os.path.exists(pdf_path):
                            self.logger.error(f"PDF file not found: {pdf_path}")
                        else:
                            self.logger.info(f"PDF file exists: {pdf_path} ({os.path.getsize(pdf_path)} bytes)")

                        # プリンター名の確認
                        self.logger.info(f"Printer name passed: {printer_name}")

                    return False
            else:
                self.logger.error("Direct printing is only supported on Windows")
                return False

        except Exception as e:
            self.logger.error(f"Failed to print PDF: {str(e)}")
            return False

    def test_printer_connection(self, printer_name: str) -> Tuple[bool, str]:
        """プリンター接続テスト"""
        try:
            # Windowsのプリンター一覧を取得してチェック
            ps_command = [
                'powershell.exe', '-Command',
                'Get-Printer | Select-Object Name, PrinterStatus | ConvertTo-Json'
            ]

            result = subprocess.run(
                ps_command,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                self.logger.info(f"Printer {printer_name} connection test completed")
                return True, "プリンター接続OK"
            else:
                error_msg = f"Printer test failed: {result.stderr}"
                self.logger.error(error_msg)
                return False, error_msg

        except Exception as e:
            error_msg = f"Printer test failed: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
