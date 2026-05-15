# Windows PDF印刷の解決策

## 問題
PDFファイルの印刷時に「この操作に対して指定されたファイルには、アプリケーションが関連付けられていません」エラーが発生

## 解決策（優先順）

### 1. SumatraPDF をインストール（推奨）
最も軽量で確実な方法：
```bash
# ダウンロード
https://www.sumatrapdfreader.org/download-free-pdf-viewer

# インストール後、プリントサーバーが自動的に検出して使用
```

### 2. Adobe Reader DC をインストール
一般的なPDFリーダー：
```bash
# ダウンロード
https://get.adobe.com/jp/reader/

# インストール後、プリントサーバーが自動的に検出して使用
```

### 3. Windows 10/11 の標準機能を使用
Microsoft Edge がPDFをサポート：
```powershell
# PDFファイルの既定のアプリをEdgeに設定
Settings > Apps > Default apps > Choose default apps by file type > .pdf > Microsoft Edge
```

### 4. pywin32 を使用（開発者向け）
requirements.txt に追加：
```
pywin32>=306
```

そして印刷コードを更新：
```python
import win32api
win32api.ShellExecute(0, "print", pdf_path, f'/d:"{printer_name}"', ".", 0)
```

## 現在の実装
プリントサーバーは以下の順序で印刷を試みます：
1. SumatraPDF（最速・最軽量）
2. Adobe Reader（互換性最高）
3. Windows Shell API（PDFビューアーが何かインストールされていれば動作）

## トラブルシューティング
- PDFビューアーがインストールされているか確認
- プリンター名が正しいか確認（空白を含む場合は引用符で囲む）
- 管理者権限で実行してみる