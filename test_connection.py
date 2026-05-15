#!/usr/bin/env python3
"""
クリーン実装データベース接続テスト
"""

import sys
import os
import logging

# パスを追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_connection():
    """データベース接続テスト"""
    try:
        from config_clean import PrintServerConfig
        from database_clean import DatabaseManager
        
        print("=== クリーン実装データベース接続テスト ===")
        
        # 設定確認
        config = PrintServerConfig()
        print(f"データベース: {config.DB_SERVER}/{config.DB_DATABASE}")
        print(f"接続文字列: {config.connection_string}")
        
        # データベース接続テスト
        print("\nデータベース接続中...")
        db_manager = DatabaseManager()
        
        # プリンター取得テスト
        printers = db_manager.get_active_printers()
        print(f"有効プリンター数: {len(printers)}")
        
        for printer in printers:
            print(f"  - {printer['DisplayName']} ({printer['PrinterName']})")
        
        # 待機ジョブ取得テスト
        pending_jobs = db_manager.get_pending_jobs()
        print(f"待機ジョブ数: {len(pending_jobs)}")
        
        for job in pending_jobs:
            print(f"  ジョブ {job['Id']}: {job['JobName']}")
            print(f"    URL: {job['PrintUrl']}")
        
        print("\n✅ データベース接続テスト成功")
        return True
        
    except ImportError as e:
        print(f"❌ モジュールインポートエラー: {e}")
        return False
    except Exception as e:
        print(f"❌ 接続エラー: {e}")
        return False

if __name__ == '__main__':
    success = test_connection()
    sys.exit(0 if success else 1)