# MK Print Server - Windows インストール手順書

## 概要

MK Print Serverは、Webシステムからの印刷指示をデータベース経由で受け取り、Windows環境のラベルプリンター（TD-4750等）で印刷を実行するPythonアプリケーションです。

## システム要件

- **OS**: Windows 10/11 または Windows Server 2019/2022
- **メモリ**: 最小 2GB RAM（推奨 4GB以上）
- **ストレージ**: 最小 1GB の空き容量
- **ネットワーク**: SQL Server（MKSystem）への接続
- **プリンター**: TD-4750またはWindows対応ラベルプリンター

## インストール手順

### 1. Python 3.13のインストール

#### 1.1 Python公式サイトからダウンロード
1. [Python公式サイト](https://www.python.org/downloads/windows/)にアクセス
2. **Python 3.13.5**（2025年1月時点の最新安定版）をダウンロード
   - ※ インストール時は公式サイトで最新版を確認してください
3. `python-3.13.5-amd64.exe`を実行

#### 1.2 Pythonのインストール設定
```
✅ 重要な設定項目：
□ "Add Python 3.13 to PATH" にチェック（必須）
□ "Install for all users" を選択（推奨）
□ インストール先: C:\Python313（推奨）
```

#### 1.3 インストール確認
```cmd
# コマンドプロンプトを開いて確認
python --version
# 出力例: Python 3.13.1

pip --version
# 出力例: pip 24.x.x
```

### 2. ODBC Driver for SQL Serverのインストール

#### 2.1 Microsoft ODBC Driver 17のダウンロード
1. [Microsoft公式サイト](https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server)にアクセス
2. **ODBC Driver 17 for SQL Server**をダウンロード
3. `msodbcsql.msi`を実行してインストール

#### 2.2 インストール確認
```cmd
# ODBCデータソースアドミニストレーターで確認
odbcad32.exe
# 「ドライバー」タブで "ODBC Driver 17 for SQL Server" の存在確認
```

### 3. MK Print Serverのセットアップ

#### 3.1 アプリケーションフォルダの作成
```cmd
# 管理者権限でコマンドプロンプトを開く
mkdir C:\MKPrintServer
cd C:\MKPrintServer
```

#### 3.2 プロジェクトファイルのコピー
以下のファイルを`C:\MKPrintServer`にコピー：

```
C:\MKPrintServer\
├── main.py
├── config.py
├── database.py
├── printer_service.py
├── queue_processor.py
├── requirements.txt
├── .env.example
└── logs\           # 空フォルダを作成
```

#### 3.3 Python依存関係のインストール
```cmd
cd C:\MKPrintServer
pip install -r requirements.txt
```

**requirements.txtの内容:**
```txt
pyodbc==4.0.39
pillow==10.0.1
qrcode==7.4.2
python-dotenv==1.0.0
pywin32==306
```

### 4. データベース接続設定

#### 4.1 環境設定ファイルの作成
```cmd
copy .env.example .env
notepad .env
```

#### 4.2 .envファイルの編集
```env
# データベース接続設定
DB_SERVER=your-sql-server-name
DB_NAME=MKSystem
DB_USER=your-username
DB_PASSWORD=your-password

# ログ設定
LOG_LEVEL=INFO
LOG_FILE=logs/print_server.log

# ポーリング設定
POLLING_INTERVAL=10
```

**⚠️ 設定値の確認ポイント:**
- `DB_SERVER`: SQL Serverのホスト名またはIPアドレス
- `DB_USER`: MKSystemデータベースへの読み書き権限を持つユーザー
- `DB_PASSWORD`: 上記ユーザーのパスワード

### 5. プリンターの設定

#### 5.1 TD-4750プリンターのセットアップ
1. **プリンタードライバーのインストール**
   - Brother公式サイトからTD-4750用ドライバーをダウンロード
   - インストーラーを実行してドライバーをインストール

2. **プリンターの物理接続**
   - USBケーブルでPCとプリンターを接続
   - 電源を入れてプリンターを認識させる

3. **Windowsプリンター設定**
   ```cmd
   # プリンター一覧の確認
   wmic printer list brief
   ```

#### 5.2 データベースへのプリンター登録
```sql
-- MKSystemデータベースで実行
INSERT INTO PrinterMaster (
    PrinterName, DisplayName, Location, PrinterType, IsActive
) VALUES (
    'Brother TD-4750TNWB', 'TD-4750ラベルプリンター', 'オフィス', 'Label', 1
);
```

### 6. 動作テスト

#### 6.1 基本動作確認
```cmd
cd C:\MKPrintServer
python main.py
```

**正常起動時の出力例:**
```
============================================================
MK Print Server - Queue Processor Only
============================================================
Polling Interval: 10 seconds
Database Server: your-sql-server-name
Database Name: MKSystem
Log Level: INFO
Log File: logs/print_server.log

Available Windows Printers:
  - Brother TD-4750TNWB

Registered Printers in Database:
  - TD-4750ラベルプリンター (Brother TD-4750TNWB)
============================================================

Starting MK Print Server (Queue Processor Mode)...
Print server is running. Press Ctrl+C to stop.
Queue Status - Pending: 0, Processing: 0, Completed: 0, Failed: 0
```

#### 6.2 印刷テスト
Webシステムから移送指示を作成し、印刷ボタンをクリックして動作確認を行います。

### 7. Windowsサービス化（本番運用用）

#### 7.1 NSSM（Non-Sucking Service Manager）のインストール
1. [NSSM公式サイト](https://nssm.cc/download)からダウンロード
2. `nssm-2.24.zip`を解凍し、`nssm.exe`を`C:\Windows\System32`にコピー

#### 7.2 サービスの登録
```cmd
# 管理者権限でコマンドプロンプトを開く
nssm install "MK Print Server"
```

**NSSM設定画面で入力:**
- **Path**: `C:\Python311\python.exe`
- **Startup directory**: `C:\MKPrintServer`
- **Arguments**: `main.py`
- **Service name**: `MK Print Server`

#### 7.3 サービスの開始
```cmd
# サービスの開始
net start "MK Print Server"

# サービス状態の確認
sc query "MK Print Server"
```

#### 7.4 自動起動の設定
```cmd
# 自動起動の設定
sc config "MK Print Server" start= auto
```

### 8. トラブルシューティング

#### 8.1 よくある問題と解決方法

**問題1: Python実行時に「python is not recognized」エラー**
```cmd
# 解決方法: PATHの確認と追加
echo %PATH%
# PATHにC:\Python313;C:\Python313\Scripts;が含まれているか確認
```

**問題2: データベース接続エラー**
```
エラー例: SQLSTATE[08001] [Microsoft][ODBC Driver 17 for SQL Server]...

解決方法:
1. SQL Server接続文字列の確認
2. ファイアウォール設定の確認
3. SQL Server認証設定の確認
```

**問題3: プリンターが見つからない**
```cmd
# Windows上でプリンター一覧を確認
wmic printer list brief

# プリンタードライバーの再インストール
# デバイスマネージャーでプリンターの状態確認
```

#### 8.2 ログファイルの確認
```cmd
# ログファイルの確認
type C:\MKPrintServer\logs\print_server.log

# リアルタイムログ監視（PowerShell）
Get-Content C:\MKPrintServer\logs\print_server.log -Wait -Tail 10
```

### 9. メンテナンス

#### 9.1 定期メンテナンス項目
- **ログファイルのローテーション**（月1回）
- **印刷キューの状態確認**（週1回）
- **プリンター接続状態の確認**（日1回）

#### 9.2 バックアップ
```cmd
# 設定ファイルのバックアップ
copy C:\MKPrintServer\.env C:\MKPrintServer\backup\.env_%date%
```

### 10. セキュリティ設定

#### 10.1 アクセス権限
```cmd
# フォルダアクセス権限の設定
icacls C:\MKPrintServer /grant "NT AUTHORITY\SYSTEM":F
icacls C:\MKPrintServer /grant "Administrators":F
icacls C:\MKPrintServer /remove "Users"
```

#### 10.2 Windows Defender設定
```
除外設定の追加:
- プロセス: python.exe
- フォルダー: C:\MKPrintServer
- ファイル: C:\MKPrintServer\main.py
```

---

## サポート

**システム管理者向けの連絡先:**
- 技術サポート: [システム管理者のメールアドレス]
- 緊急時対応: [緊急連絡先]

**ドキュメント更新日:** 2025年1月28日
**バージョン:** 1.1.0
**Python情報確認日:** 2025年1月28日（Python 3.13.5が最新）