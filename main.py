#!/usr/bin/env python3
"""
プリントサーバー メインエントリーポイント - クリーン実装
仕様書: docs/print-server-specification.md

使用方法:
    python main.py                 # 通常起動
    python main.py --test          # テストモード
    python main.py --install       # Windowsサービス登録
    python main.py --remove        # Windowsサービス削除
"""

import sys
import os
import logging
import argparse
from logging.handlers import RotatingFileHandler

# パスを追加してモジュールをインポート
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import PrintServerConfig
from database import DatabaseManager
from printer_service import PrinterService
from queue_processor import QueueProcessor

def setup_logging():
    """ログ設定を初期化"""
    config = PrintServerConfig()
    
    # ログディレクトリを作成
    log_dir = os.path.dirname(config.LOG_FILE)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # ルートロガーを設定
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, config.LOG_LEVEL))
    
    # ファイルハンドラー
    file_handler = RotatingFileHandler(
        config.LOG_FILE,
        maxBytes=config.LOG_MAX_SIZE,
        backupCount=config.LOG_MAX_FILES,
        encoding='utf-8'
    )
    file_handler.setLevel(getattr(logging, config.LOG_LEVEL))
    
    # コンソールハンドラー
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # フォーマッター
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def test_system():
    """システム動作テスト"""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("=== プリントサーバー システムテスト開始 ===")
        
        # データベース接続テスト
        logger.info("データベース接続テスト...")
        db_manager = DatabaseManager()
        printers = db_manager.get_active_printers()
        logger.info(f"有効なプリンター数: {len(printers)}")
        
        for printer in printers:
            logger.info(f"プリンター: {printer['DisplayName']} ({printer['PrinterName']})")
        
        # 待機中ジョブの確認
        logger.info("待機中ジョブの確認...")
        pending_jobs = db_manager.get_pending_jobs()
        logger.info(f"待機中ジョブ数: {len(pending_jobs)}")
        
        for job in pending_jobs[:3]:  # 最初の3件のみ表示
            logger.info(f"ジョブ {job['Id']}: {job['JobName']} (URL: {job['PrintUrl']})")
        
        # プリンターサービステスト
        logger.info("プリンターサービステスト...")
        printer_service = PrinterService()
        
        if printers:
            test_printer = printers[0]['PrinterName']
            success, message = printer_service.test_printer_connection(test_printer)
            logger.info(f"プリンターテスト結果: {success} - {message}")
        
        logger.info("=== システムテスト完了 ===")
        return True
        
    except Exception as e:
        logger.error(f"システムテストエラー: {e}")
        return False

def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description='Angie Print Server')
    parser.add_argument('--test', action='store_true', help='システムテストを実行')
    parser.add_argument('--install', action='store_true', help='Windowsサービスとして登録')
    parser.add_argument('--remove', action='store_true', help='Windowsサービスを削除')
    
    args = parser.parse_args()
    
    # ログ設定
    logger = setup_logging()
    logger.info("Angie Print Server starting...")
    
    try:
        if args.test:
            # テストモード
            success = test_system()
            sys.exit(0 if success else 1)
            
        elif args.install:
            # Windowsサービス登録
            logger.info("Windows service installation not implemented yet")
            sys.exit(1)
            
        elif args.remove:
            # Windowsサービス削除
            logger.info("Windows service removal not implemented yet")
            sys.exit(1)
            
        else:
            # 通常起動
            logger.info("Starting print queue processor...")
            
            # 設定情報を表示
            config = PrintServerConfig()
            logger.info(f"Database: {config.DB_SERVER}/{config.DB_DATABASE}")
            logger.info(f"Poll interval: {config.POLL_INTERVAL} seconds")
            logger.info(f"Chrome path: {config.CHROME_PATH}")
            
            # キュープロセッサーを開始
            processor = QueueProcessor()
            processor.start()
            
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"Application error: {e}")
        sys.exit(1)
    finally:
        logger.info("Angie Print Server stopped")

if __name__ == '__main__':
    main()