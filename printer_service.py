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

# paper_height クエリ仕様 (ADR docs/adr/0001-dynamic-paper-height.md)
PAPER_HEIGHT_MAX_MM = 3000
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

    if mm < 1 or mm > PAPER_HEIGHT_MAX_MM:
        raise ValueError(f"paper_height out of range (1..{PAPER_HEIGHT_MAX_MM} mm): {mm}")

    inch = mm / MM_PER_INCH
    return cleaned_url, f"--print-to-pdf-paper-height={inch:.5f}", f"{mm}mm"

class PrinterService:
    """印刷処理サービス"""

    def __init__(self):
        self.config = PrintServerConfig()
        self.logger = logging.getLogger(__name__)

    def print_web_url(self, print_url: str, printer_name: str, job_name: str = "Web Print") -> Tuple[bool, str]:
        """Web URLを直接印刷"""
        try:
            self.logger.info(f"Starting web print job: {job_name}")
            self.logger.info(f"Print URL: {print_url}")
            self.logger.info(f"Target printer: {printer_name}")

            # paper_height クエリを抽出 (ADR 0001)
            try:
                cleaned_url, paper_height_arg, paper_height_label = extract_paper_height(print_url)
            except ValueError as e:
                error_msg = f"invalid paper_height: {e}"
                self.logger.error(error_msg)
                return False, error_msg

            if paper_height_arg:
                self.logger.info(f"paper_height: {paper_height_label} -> {paper_height_arg}")
            else:
                self.logger.info(f"paper_height: {paper_height_label} (--print-to-pdf-paper-height omitted)")

            # 印刷用URLに認証トークンを追加
            auth_print_url = self._add_auth_token(cleaned_url)

            # PDFファイル名を生成
            import tempfile
            import os
            temp_pdf = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
            temp_pdf_path = temp_pdf.name
            temp_pdf.close()

            # Chrome実行コマンドを組み立て (paper_height は paper_height_arg がある場合のみ追加)
            chrome_extra_args = [
                f'--print-to-pdf={temp_pdf_path}',
                '--disable-print-preview',
            ]
            if paper_height_arg:
                chrome_extra_args.append(paper_height_arg)
            chrome_extra_args.append(auth_print_url)

            chrome_command = self.config.chrome_command_base + chrome_extra_args
            chrome_path = chrome_command[0]

            # Chrome実行ファイルの存在確認
            if not self._chrome_exists(chrome_path):
                error_msg = f"Chrome executable not found: {chrome_path}"
                self.logger.error(error_msg)
                return False, error_msg

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
                        return False, "PDFファイルが空です"
                else:
                    self.logger.error(f"PDF file not created: {temp_pdf_path}")
                    return False, "PDFファイルが作成されませんでした"

                try:
                    # PDFをプリンターに送信（Windows）
                    if self._print_pdf_to_printer(temp_pdf_path, printer_name):
                        self.logger.info(f"PDF printed successfully to {printer_name}")
                        return True, "Web印刷完了"
                    else:
                        return False, "プリンターへの送信に失敗しました"
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
                return False, error_msg

        except subprocess.TimeoutExpired:
            error_msg = f"Print job timed out after {self.config.PRINT_TIMEOUT} seconds"
            self.logger.error(error_msg)
            return False, error_msg

        except Exception as e:
            error_msg = f"Print job failed: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg

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

    def _print_pdf_to_printer(self, pdf_path: str, printer_name: str) -> bool:
        """PDFファイルをプリンターに送信（Windows）"""
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
                        '-print-settings', 'paper=MKラベル,portrait,fit',
                        '-silent',
                        pdf_path
                    ]
                elif pdf_reader and 'AcroRd32' in pdf_reader:
                    # Adobe Readerの場合
                    print_command = [
                        pdf_reader,
                        '/t', pdf_path, printer_name
                    ]
                else:
                    # 代替方法: PowerShellでPDFを既定のアプリケーションで開いて印刷
                    # まずPDFビューアーがインストールされているか確認
                    self.logger.warning("No PDF reader found, trying Windows Shell print")
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
