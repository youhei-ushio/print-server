#!/usr/bin/env python3
"""
クリーン実装プリントサーバー起動スクリプト
仕様書: docs/print-server-specification.md
"""

import sys
import os

# パスを追加してモジュールをインポート
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from main_clean import main
    
    print("=== Angie Print Server (Clean Implementation) ===")
    print("仕様書: docs/print-server-specification.md")
    print("=" * 50)
    
    # クリーン実装のメイン処理を実行
    sys.exit(main())
    
except ImportError as e:
    print(f"❌ モジュールインポートエラー: {e}")
    print("クリーン実装ファイルが正しく配置されているか確認してください。")
    sys.exit(1)
except Exception as e:
    print(f"❌ 予期しないエラー: {e}")
    sys.exit(1)