"""
プリントサーバー設定管理 - クリーン実装
仕様書: docs/print-server-specification.md
"""

import os
from typing import Dict, Any

# .envファイルを読み込み
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenvがインストールされていない場合は環境変数のみ使用
    pass

class PrintServerConfig:
    """プリントサーバー設定クラス"""

    # データベース接続設定
    DB_SERVER = os.getenv('DB_SERVER', 'localhost')
    DB_DATABASE = os.getenv('DB_DATABASE', 'MKSystem')
    DB_USER = os.getenv('DB_USER', '')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_DRIVER = os.getenv('DB_DRIVER', '{ODBC Driver 17 for SQL Server}')
    DB_TIMEOUT = int(os.getenv('DB_TIMEOUT', '30'))

    # 印刷システム設定
    POLL_INTERVAL = int(os.getenv('PRINT_POLL_INTERVAL', '2'))
    MAX_RETRY_COUNT = int(os.getenv('PRINT_MAX_RETRY', '3'))
    PRINT_TIMEOUT = int(os.getenv('PRINT_TIMEOUT', '30'))
    CHROME_PATH = os.getenv('CHROME_PATH', '')
    PRINT_AUTH_TOKEN = os.getenv('PRINT_AUTH_TOKEN', '')

    # Chrome印刷用引数（用紙サイズは printer_service で PrinterType に応じて動的付与）
    CHROME_ARGS = [
        '--headless=new',  # 新しいヘッドレスモード
        '--disable-gpu',
        '--disable-dev-shm-usage',
        '--no-sandbox',
        '--disable-web-security',
        '--allow-running-insecure-content',
        '--no-first-run',
        '--disable-default-apps',
        '--disable-extensions',
        '--disable-sync',
    ]

    LABEL_DEFAULT_PAPER_WIDTH_INCH = 3.14961  # 80mm

    # ログ設定
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/print_server.log')
    LOG_MAX_SIZE = int(os.getenv('LOG_MAX_SIZE', '10485760'))  # 10MB
    LOG_MAX_FILES = int(os.getenv('LOG_MAX_FILES', '5'))

    @property
    def connection_string(self) -> str:
        """データベース接続文字列を生成"""
        conn_str = (
            f"DRIVER={self.DB_DRIVER};"
            f"SERVER={self.DB_SERVER};"
            f"DATABASE={self.DB_DATABASE};"
        )

        # 認証方式の判定
        if self.DB_USER and self.DB_PASSWORD:
            # SQL Server認証
            conn_str += f"UID={self.DB_USER};PWD={self.DB_PASSWORD};"
        else:
            # Windows認証（デフォルト）
            conn_str += "Trusted_Connection=yes;"

        conn_str += f"Connection Timeout={self.DB_TIMEOUT}"
        return conn_str

    @property
    def chrome_command_base(self) -> list:
        """Chrome実行コマンドのベースを取得"""
        # Chrome実行パスを自動検出
        chrome_path = self._find_chrome_path()
        return [chrome_path] + self.CHROME_ARGS

    def _find_chrome_path(self) -> str:
        """Chrome実行パスを検出"""
        # 環境変数で指定されている場合はそれを使用
        if self.CHROME_PATH:
            return self.CHROME_PATH

        # Windows環境での一般的なChromeパスを検索
        import platform
        if platform.system() == 'Windows':
            possible_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                r"C:\Users\{}\AppData\Local\Google\Chrome\Application\chrome.exe".format(os.getenv('USERNAME', '')),
                # Microsoft Edge (Chromium)
                r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                # Chromium
                r"C:\Program Files\Chromium\Application\chrome.exe",
            ]

            for path in possible_paths:
                if os.path.exists(path):
                    return path

        # デフォルトでchrome.exeを返す（PATHに含まれている場合）
        return 'chrome.exe'
