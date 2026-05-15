#!/usr/bin/env python3
"""
クリーン実装プリントサーバーのテストスクリプト
仕様書: docs/print-server-specification.md

使用方法: python test_clean_system.py
"""

import sys
import os
import logging

# パスを追加してモジュールをインポート
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from config_clean import PrintServerConfig
    from database_clean import DatabaseManager
    from printer_service_clean import PrinterService
    from queue_processor_clean import QueueProcessor
except ImportError as e:
    print(f"モジュールのインポートエラー: {e}")
    print("必要なファイルが見つかりません。クリーン実装ファイルが正しく配置されているか確認してください。")
    sys.exit(1)

def setup_test_logging():
    """テスト用ログ設定"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

def test_config():
    """設定テスト"""
    logger = logging.getLogger(__name__)
    logger.info("=== 設定テスト開始 ===")
    
    try:
        config = PrintServerConfig()
        
        logger.info(f"データベースサーバー: {config.DB_SERVER}")
        logger.info(f"データベース名: {config.DB_DATABASE}")
        logger.info(f"ポーリング間隔: {config.POLL_INTERVAL}秒")
        logger.info(f"最大リトライ回数: {config.MAX_RETRY_COUNT}")
        logger.info(f"印刷タイムアウト: {config.PRINT_TIMEOUT}秒")
        logger.info(f"Chrome パス: {config.CHROME_PATH}")
        
        logger.info("接続文字列生成テスト...")
        conn_str = config.connection_string
        logger.info(f"接続文字列: {conn_str}")
        
        logger.info("Chrome コマンドベース生成テスト...")
        chrome_cmd = config.chrome_command_base
        logger.info(f"Chrome コマンド: {' '.join(chrome_cmd)}")
        
        logger.info("✅ 設定テスト完了")
        return True
        
    except Exception as e:
        logger.error(f"❌ 設定テストエラー: {e}")
        return False

def test_database():
    """データベーステスト"""
    logger = logging.getLogger(__name__)
    logger.info("=== データベーステスト開始 ===")
    
    try:
        db_manager = DatabaseManager()
        
        # プリンター取得テスト
        logger.info("有効プリンター取得テスト...")
        printers = db_manager.get_active_printers()
        logger.info(f"有効プリンター数: {len(printers)}")
        
        for printer in printers:
            logger.info(f"  - {printer['DisplayName']} ({printer['PrinterName']})")
        
        # 待機ジョブ取得テスト
        logger.info("待機ジョブ取得テスト...")
        pending_jobs = db_manager.get_pending_jobs()
        logger.info(f"待機ジョブ数: {len(pending_jobs)}")
        
        for job in pending_jobs[:3]:  # 最初の3件のみ表示
            logger.info(f"  ジョブ {job['Id']}: {job['JobName']} (優先度: {job['Priority']})")
            logger.info(f"    URL: {job['PrintUrl']}")
        
        # ログ追加テスト
        if pending_jobs:
            test_job = pending_jobs[0]
            logger.info("ログ追加テスト...")
            db_manager.add_print_log(
                test_job['Id'], 
                test_job['PrinterId'], 
                'Info', 
                'テストログエントリ'
            )
            logger.info("✅ ログ追加成功")
        
        logger.info("✅ データベーステスト完了")
        return True
        
    except Exception as e:
        logger.error(f"❌ データベーステストエラー: {e}")
        return False

def test_printer_service():
    """プリンターサービステスト"""
    logger = logging.getLogger(__name__)
    logger.info("=== プリンターサービステスト開始 ===")
    
    try:
        printer_service = PrinterService()
        
        # プリンター接続テスト
        logger.info("プリンター接続テスト...")
        test_printer = "Microsoft Print to PDF"
        success, message = printer_service.test_printer_connection(test_printer)
        logger.info(f"接続テスト結果: {success} - {message}")
        
        # Web URL印刷テスト（実際の印刷は行わない、コマンド生成のみ）
        logger.info("Web URL印刷テスト（ドライラン）...")
        test_url = "http://localhost:11081/v3/logistics/transfer-item/1/print-label"
        
        # 実際の印刷処理はスキップして、コマンド構築のみテスト
        config = PrintServerConfig()
        chrome_command = config.chrome_command_base + [
            f'--print-to-pdf=/tmp/test_print.pdf',
            test_url
        ]
        logger.info(f"Chrome コマンド: {' '.join(chrome_command)}")
        
        logger.info("✅ プリンターサービステスト完了")
        return True
        
    except Exception as e:
        logger.error(f"❌ プリンターサービステストエラー: {e}")
        return False

def test_queue_processor():
    """キュープロセッサーテスト"""
    logger = logging.getLogger(__name__)
    logger.info("=== キュープロセッサーテスト開始 ===")
    
    try:
        # QueueProcessor インスタンス作成テスト
        processor = QueueProcessor()
        logger.info("キュープロセッサー初期化成功")
        
        # 待機ジョブの処理シミュレーション（実際の処理は行わない）
        db_manager = DatabaseManager()
        pending_jobs = db_manager.get_pending_jobs()
        
        if pending_jobs:
            test_job = pending_jobs[0]
            logger.info(f"処理対象ジョブ: {test_job['JobName']}")
            logger.info(f"プリンター: {test_job['PrinterDisplayName']}")
            logger.info(f"URL: {test_job['PrintUrl']}")
            logger.info("（実際の印刷処理はスキップ）")
        else:
            logger.info("処理対象の待機ジョブがありません")
        
        logger.info("✅ キュープロセッサーテスト完了")
        return True
        
    except Exception as e:
        logger.error(f"❌ キュープロセッサーテストエラー: {e}")
        return False

def main():
    """メインテスト処理"""
    logger = setup_test_logging()
    
    logger.info("クリーン実装プリントサーバー テスト開始")
    logger.info("=" * 50)
    
    test_results = []
    
    # 各テストを実行
    test_results.append(("設定テスト", test_config()))
    test_results.append(("データベーステスト", test_database()))
    test_results.append(("プリンターサービステスト", test_printer_service()))
    test_results.append(("キュープロセッサーテスト", test_queue_processor()))
    
    # 結果サマリー
    logger.info("=" * 50)
    logger.info("テスト結果サマリー:")
    
    all_passed = True
    for test_name, result in test_results:
        status = "✅ 成功" if result else "❌ 失敗"
        logger.info(f"  {test_name}: {status}")
        if not result:
            all_passed = False
    
    logger.info("=" * 50)
    
    if all_passed:
        logger.info("🎉 すべてのテストが成功しました")
        logger.info("クリーン実装プリントサーバーは正常に動作する準備ができています")
        return 0
    else:
        logger.error("⚠️  一部のテストが失敗しました")
        logger.error("問題を修正してからプリントサーバーを起動してください")
        return 1

if __name__ == '__main__':
    sys.exit(main())