# Microsoft Print to PDFでの印刷テスト手順書

## 概要
手元のWindows環境でプリンターなしでも印刷結果を確認するため、Microsoft Print to PDFを使用してラベル印刷をPDFファイルとして出力します。

## 前提条件
- Windows 10/11（Microsoft Print to PDFが標準で利用可能）
- Python 3.13以上がインストール済み（3.11以上でも動作）
- 必要なPythonライブラリ：Pillow, pyodbc（オプション）

## セットアップ手順

### 1. 必要なライブラリのインストール
```cmd
pip install Pillow pyodbc
```

### 2. データベース接続設定（オプション）
実際のMKSystemデータベースから印刷キューデータを取得したい場合は、`test_pdf_print.py`の接続文字列を編集：

```python
conn_str = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=your-actual-server-name;"    # 実際のサーバー名
    "DATABASE=MKSystem;"
    "UID=your-actual-username;"          # 実際のユーザー名
    "PWD=your-actual-password;"          # 実際のパスワード
    "Encrypt=yes;"
    "TrustServerCertificate=yes;"
)
```

## 実行手順

### 方法1: Pythonスクリプト実行
```cmd
cd /path/to/angie/print_server
python test_pdf_print.py
```

**期待される出力:**
```
=== MK Print Server PDF出力テスト ===

印刷キューデータを取得中...
データベースから取得できませんでした。サンプルデータを使用します。
✅ キューデータ取得成功:
- ID: 1
- ジョブ名: 移送ラベル_T20250729-002
- データタイプ: IMAGE
- ステータス: Pending
- 優先度: 1

✅ ラベルデータ解析成功:
- type: transfer_label
- instruction_number: T20250729-002
- product_name: 091307 MM-103 面 メッキ 157 本金　塗装
- quantity: 2
- source_location: 本社
- destination_location: 小美玉
- qr_code: 
- created_at: 2025-07-29 03:52:53
- lot_number: A1904100191-2

ラベル画像を生成中...
PDF出力中...
✅ PDF出力完了: C:\path\to\transfer_label_20250129_143022.pdf
```

### 方法2: Microsoft Print to PDFでの直接印刷（Windows環境）

1. **生成されたPDFファイルを開く**
   - エクスプローラーで`transfer_label_xxxxxx.pdf`を開く

2. **印刷画面を開く**
   - Adobe ReaderまたはEdgeでPDFを開く
   - `Ctrl+P`で印刷ダイアログを開く

3. **プリンター選択**
   - プリンター: `Microsoft Print to PDF`を選択
   - 用紙サイズ: `A4`または`Letter`
   - 向き: `縦`

4. **印刷実行**
   - `印刷`ボタンをクリック
   - 保存先とファイル名を指定してPDFとして保存

## ラベル出力サンプル

生成されるラベルには以下の情報が含まれます：

```
┌─────────────────────────────────────┐
│          移送指示ラベル             │
├─────────────────────────────────────┤
│ 指示番号: T20250729-002            │
│ 商品: 091307 MM-103 面 メッキ        │
│       157 本金　塗装               │
│ 数量: 2個                          │
│ 本社 → 小美玉                      │
│ 作成: 2025-07-29 03:52:53          │
│ LOT: A1904100191-2                 │
└─────────────────────────────────────┘
```

## トラブルシューティング

### エラー1: `pyodbc.InterfaceError`
```
解決方法:
1. ODBC Driver 17 for SQL Serverのインストール確認
2. 接続文字列の修正
3. サンプルデータモードでのテスト実行
```

### エラー2: `ImportError: No module named 'PIL'`
```
解決方法:
pip install Pillow
```

### エラー3: フォントエラー
```
解決方法:
1. MS ゴシック(msgothic.ttc)の存在確認
2. メイリオ(meiryo.ttc)の代替使用
3. デフォルトフォントでのフォールバック
```

### エラー4: `Microsoft Print to PDF`が見つからない
```
解決方法:
1. Windows機能の有効化確認
   - 設定 > アプリ > オプション機能
   - "Microsoft Print to PDF"を有効化
2. デバイスとプリンターでの確認
   - コントロールパネル > デバイスとプリンター
   - "Microsoft Print to PDF"の存在確認
```

## データベース連携テスト

実際のMKSystemデータベースと連携する場合：

1. **接続文字列の設定**
   ```python
   # test_pdf_print.pyの接続設定を実環境に合わせて修正
   conn_str = "実際の接続文字列"
   ```

2. **印刷キューデータの確認**
   ```sql
   -- MKSystemで印刷キューの存在確認
   SELECT TOP 5 * FROM PrintQueue ORDER BY Id DESC;
   ```

3. **テスト実行**
   ```cmd
   python test_pdf_print.py
   ```

## 本格運用時の考慮事項

- **フォント**: 商用環境では適切な日本語フォントライセンスの確認
- **画像品質**: TD-4750の実際の解像度（203 DPI）に合わせた調整
- **QRコード**: 実際のQRコード生成ライブラリ（qrcode）の統合
- **用紙サイズ**: ラベル用紙の実際のサイズ（4インチ幅等）への対応

---

**作成日**: 2025年1月28日  
**バージョン**: 1.0.0