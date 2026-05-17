"""
キュープロセッサー - クリーン実装
仕様書: docs/print-server-specification.md
"""

import time
import logging
from typing import Dict, Any
from database import DatabaseManager
from printer_service import PrinterService
from config import PrintServerConfig

class QueueProcessor:
    """印刷キュー処理クラス"""
    
    def __init__(self):
        self.config = PrintServerConfig()
        self.db_manager = DatabaseManager()
        self.printer_service = PrinterService()
        self.logger = logging.getLogger(__name__)
        self.running = False
    
    def start(self):
        """キュー処理を開始"""
        self.running = True
        self.logger.info("Print queue processor started")
        
        try:
            while self.running:
                self._process_pending_jobs()
                time.sleep(self.config.POLL_INTERVAL)
                
        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal")
        except Exception as e:
            self.logger.error(f"Queue processor error: {e}")
        finally:
            self.running = False
            self.logger.info("Print queue processor stopped")
    
    def stop(self):
        """キュー処理を停止"""
        self.running = False
        self.logger.info("Print queue processor stop requested")
    
    def _process_pending_jobs(self):
        """待機中のジョブを処理"""
        try:
            jobs = self.db_manager.get_pending_jobs()
            
            if not jobs:
                return
            
            self.logger.info(f"Found {len(jobs)} pending job(s)")
            
            for job in jobs:
                if not self.running:
                    break
                
                self._process_single_job(job)
                
        except Exception as e:
            self.logger.error(f"Error processing pending jobs: {e}")
    
    def _process_single_job(self, job: Dict[str, Any]):
        """単一ジョブを処理"""
        job_id = job['Id']
        job_name = job['JobName']
        
        try:
            self.logger.info(f"Processing job {job_id}: {job_name}")
            
            # ジョブステータスを処理中に更新
            self.db_manager.update_job_status(job_id, 'Processing')
            self.db_manager.add_print_log(
                job_id, 
                job['PrinterId'], 
                'Info', 
                f"印刷処理開始: {job_name}"
            )
            
            # 印刷実行
            success, message, retryable = self.printer_service.print_web_url(
                job['PrintUrl'],
                job['PrinterName'],
                job_name
            )

            if success:
                # 成功
                self.db_manager.update_job_status(job_id, 'Completed')
                self.db_manager.add_print_log(
                    job_id,
                    job['PrinterId'],
                    'Info',
                    f"印刷完了: {message}"
                )
                self.logger.info(f"Job {job_id} completed successfully")

            else:
                # 失敗 - リトライ判定 (恒久エラーはリトライ上限を待たずに Failed)
                retry_count = job['RetryCount']
                max_retry = job['MaxRetryCount']

                if retryable and retry_count < max_retry:
                    # リトライ
                    self.db_manager.update_job_status(job_id, 'Pending', message, increment_retry=True)
                    self.db_manager.add_print_log(
                        job_id,
                        job['PrinterId'],
                        'Warning',
                        f"印刷失敗、リトライ {retry_count + 1}/{max_retry}: {message}"
                    )
                    self.logger.warning(f"Job {job_id} failed, retry {retry_count + 1}/{max_retry}: {message}")

                else:
                    # 最終失敗 (リトライ上限到達 or 恒久エラー)
                    self.db_manager.update_job_status(job_id, 'Failed', message)
                    failure_kind = "恒久エラー" if not retryable else "印刷最終失敗"
                    self.db_manager.add_print_log(
                        job_id,
                        job['PrinterId'],
                        'Error',
                        f"{failure_kind}: {message}"
                    )
                    self.logger.error(f"Job {job_id} failed permanently ({failure_kind}): {message}")
                    
        except Exception as e:
            error_msg = f"Job processing error: {str(e)}"
            self.logger.error(f"Job {job_id} processing error: {e}")
            
            # エラーログを記録
            try:
                self.db_manager.update_job_status(job_id, 'Failed', error_msg)
                self.db_manager.add_print_log(
                    job_id, 
                    job['PrinterId'], 
                    'Error', 
                    error_msg
                )
            except Exception as db_error:
                self.logger.error(f"Failed to update job status after error: {db_error}")