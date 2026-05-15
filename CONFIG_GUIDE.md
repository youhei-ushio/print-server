# MK Print Server 設定ガイド

## 概要

MK Print Serverの環境設定ファイル（.env）の設定方法とパラメータの詳細説明です。

**最新情報確認日:** 2025年1月28日

## 基本セットアップ

### 1. 設定ファイルの作成

```cmd
# .env.exampleをコピーして.envファイルを作成
copy .env.example .env
```

### 2. 必須設定項目

以下の項目は必ず設定してください：

```env
# データベース接続（必須）
DB_SERVER=your-sql-server-host
DB_NAME=MKSystem
DB_USER=your-username          # Windows認証の場合は空白
DB_PASSWORD=your-password      # Windows認証の場合は空白
```

## データベース設定詳細

### SQL Server認証の場合

```env
DB_SERVER=192.168.1.100
DB_NAME=MKSystem
DB_USER=mkprint_user
DB_PASSWORD=secure_password123
DB_DRIVER={ODBC Driver 18 for SQL Server}
DB_ENCRYPT=yes
DB_TRUST_SERVER_CERTIFICATE=yes
```

### Windows認証の場合

```env
DB_SERVER=localhost
DB_NAME=MKSystem
DB_USER=
DB_PASSWORD=
DB_DRIVER={ODBC Driver 18 for SQL Server}
DB_ENCRYPT=yes
DB_TRUST_SERVER_CERTIFICATE=yes
```

### 名前付きインスタンスの場合

```env
DB_SERVER=localhost
DB_INSTANCE=SQLEXPRESS
DB_NAME=MKSystem
# その他の設定...
```

### カスタムポートの場合

```env
DB_SERVER=192.168.1.100
DB_PORT=1433
DB_NAME=MKSystem
# その他の設定...
```

## ODBCドライバー選択

### 推奨ドライバー（2025年1月時点）

```env
# 最新版（推奨）
DB_DRIVER={ODBC Driver 18 for SQL Server}

# 安定版
DB_DRIVER={ODBC Driver 17 for SQL Server}
```

### ドライバー別の機能

| ドライバー | 暗号化オプション | 新機能 | 推奨用途 |
|-----------|-----------------|--------|----------|
| ODBC Driver 18 | mandatory, optional, strict | 高度なセキュリティ | 本番環境 |
| ODBC Driver 17 | yes, no | 標準機能 | 互換性重視 |

## セキュリティ設定

### 暗号化オプション（ODBC Driver 18）

```env
# 必須暗号化（最高セキュリティ）
DB_ENCRYPT=mandatory

# オプション暗号化（推奨）
DB_ENCRYPT=yes

# 暗号化なし（開発環境のみ）
DB_ENCRYPT=no
```

### 証明書検証

```env
# 自己署名証明書を許可（開発環境）
DB_TRUST_SERVER_CERTIFICATE=yes

# 正式な証明書のみ許可（本番環境）
DB_TRUST_SERVER_CERTIFICATE=no
```

## プリントサーバー動作設定

### 基本設定

```env
# ポーリング間隔（推奨: 5-30秒）
POLLING_INTERVAL=10

# リトライ回数（推奨: 2-5回）
MAX_RETRY_COUNT=3

# タイムアウト（推奨: 30-60秒）
DEFAULT_TIMEOUT=30

# 同時実行ジョブ数（推奨: 3-10個）
MAX_CONCURRENT_JOBS=5
```

### パフォーマンス調整

**高負荷環境（多数の印刷ジョブ）:**
```env
POLLING_INTERVAL=5
MAX_CONCURRENT_JOBS=10
DEFAULT_TIMEOUT=45
```

**軽負荷環境（少数の印刷ジョブ）:**
```env
POLLING_INTERVAL=30
MAX_CONCURRENT_JOBS=3
DEFAULT_TIMEOUT=30
```

## ログ設定

### 本番環境推奨設定

```env
LOG_LEVEL=INFO
LOG_FILE=logs/print_server.log
LOG_MAX_SIZE=10
LOG_BACKUP_COUNT=5
LOG_CONSOLE=true
```

### デバッグ環境設定

```env
LOG_LEVEL=DEBUG
DEBUG_MODE=true
DEBUG_SQL=true
DEBUG_PRINTER=true
TEST_MODE=false
```

### ログレベル詳細

| レベル | 用途 | 出力内容 |
|--------|------|----------|
| DEBUG | 開発・デバッグ | 全ての詳細情報 |
| INFO | 本番運用 | 重要な処理情報 |
| WARNING | 監視 | 警告・注意事項 |
| ERROR | エラー監視 | エラー情報のみ |
| CRITICAL | 緊急対応 | 致命的エラーのみ |

## 環境別設定例

### 開発環境

```env
# データベース
DB_SERVER=localhost
DB_INSTANCE=SQLEXPRESS
DB_NAME=MKSystem_Dev
DB_USER=
DB_PASSWORD=
DB_TRUST_SERVER_CERTIFICATE=yes

# 動作設定
POLLING_INTERVAL=30
MAX_RETRY_COUNT=2
DEBUG_MODE=true
TEST_MODE=true

# ログ
LOG_LEVEL=DEBUG
LOG_CONSOLE=true
```

### テスト環境

```env
# データベース
DB_SERVER=test-server.company.com
DB_NAME=MKSystem_Test
DB_USER=test_user
DB_PASSWORD=test_password
DB_ENCRYPT=yes

# 動作設定
POLLING_INTERVAL=15
MAX_RETRY_COUNT=3
DEBUG_MODE=false
TEST_MODE=false

# ログ
LOG_LEVEL=INFO
LOG_CONSOLE=true
```

### 本番環境

```env
# データベース
DB_SERVER=prod-server.company.com
DB_NAME=MKSystem
DB_USER=prod_print_user
DB_PASSWORD=complex_secure_password
DB_DRIVER={ODBC Driver 18 for SQL Server}
DB_ENCRYPT=mandatory
DB_TRUST_SERVER_CERTIFICATE=no

# 動作設定
POLLING_INTERVAL=10
MAX_RETRY_COUNT=3
MAX_CONCURRENT_JOBS=5
DEBUG_MODE=false
TEST_MODE=false

# ログ
LOG_LEVEL=INFO
LOG_CONSOLE=false
AUTO_CLEANUP_DAYS=30
```

## トラブルシューティング

### 接続エラーの場合

1. **ドライバー確認**
   ```cmd
   # インストール済みドライバーの確認
   odbcad32.exe
   ```

2. **接続テスト**
   ```python
   # config.pyでの接続文字列確認
   python -c "from config import Config; print(Config().connection_string)"
   ```

### パフォーマンス問題の場合

1. **ポーリング間隔の調整**
   - 高負荷時: `POLLING_INTERVAL=5`
   - CPU負荷軽減: `POLLING_INTERVAL=30`

2. **同時実行数の調整**
   - 高性能マシン: `MAX_CONCURRENT_JOBS=10`
   - 低性能マシン: `MAX_CONCURRENT_JOBS=2`

### メモリ不足の場合

```env
# メモリ使用量の制限
MAX_MEMORY_USAGE=256
MAX_COMPLETED_JOBS=50
AUTO_CLEANUP_DAYS=7
```

## セキュリティ最適化

### 本番環境でのセキュリティ強化

```env
# 最高レベルのセキュリティ
DB_ENCRYPT=mandatory
DB_TRUST_SERVER_CERTIFICATE=no

# IPアドレス制限（実装時）
ALLOWED_IP_RANGES=192.168.1.0/24

# 管理APIトークン（実装時）
ADMIN_API_TOKEN=complex-random-token-here
```

## バックアップ・メンテナンス

### 自動メンテナンス設定

```env
# 完了ジョブの自動削除（30日後）
AUTO_CLEANUP_DAYS=30

# 統計情報の更新（24時間毎）
DB_STATS_UPDATE_INTERVAL=24

# ヘルスチェック（15分毎）
HEALTH_CHECK_INTERVAL=15
```

---

**設定に関する質問や問題がある場合は、システム管理者に連絡してください。**

**作成日:** 2025年1月28日  
**バージョン:** 1.0.0