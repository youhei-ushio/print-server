"""
データベース接続管理 - クリーン実装
仕様書: docs/print-server-specification.md
"""

import pyodbc
import logging
from typing import List, Dict, Optional, Any
from contextlib import contextmanager
from config import PrintServerConfig

class DatabaseManager:
    """データベース接続管理クラス"""
    
    def __init__(self):
        self.config = PrintServerConfig()
        self.logger = logging.getLogger(__name__)
    
    @contextmanager
    def get_connection(self):
        """データベース接続コンテキストマネージャー"""
        conn = None
        try:
            conn = pyodbc.connect(self.config.connection_string)
            yield conn
        except Exception as e:
            self.logger.error(f"Database connection failed: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def get_pending_jobs(self) -> List[Dict[str, Any]]:
        """待機中の印刷ジョブを取得"""
        query = """
        SELECT TOP 10
            pq.Id,
            pq.PrinterId,
            pq.JobName,
            pq.PrintUrl,
            pq.Priority,
            pq.RetryCount,
            pq.MaxRetryCount,
            pm.PrinterName,
            pm.DisplayName as PrinterDisplayName,
            pm.TimeoutSeconds
        FROM PrintQueue pq
        INNER JOIN PrinterMaster pm ON pq.PrinterId = pm.Id
        WHERE pq.Status = 'Pending'
        AND pm.IsActive = 1
        ORDER BY pq.Priority ASC, pq.RequestedAt ASC
        """
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                
                jobs = []
                for row in cursor.fetchall():
                    jobs.append({
                        'Id': row.Id,
                        'PrinterId': row.PrinterId,
                        'JobName': row.JobName,
                        'PrintUrl': row.PrintUrl,
                        'Priority': row.Priority,
                        'RetryCount': row.RetryCount,
                        'MaxRetryCount': row.MaxRetryCount,
                        'PrinterName': row.PrinterName,
                        'PrinterDisplayName': row.PrinterDisplayName,
                        'TimeoutSeconds': row.TimeoutSeconds
                    })
                
                return jobs
                
        except Exception as e:
            self.logger.error(f"Failed to get pending jobs: {e}")
            return []
    
    def update_job_status(self, job_id: int, status: str, error_message: str = None, increment_retry: bool = False):
        """ジョブステータスを更新"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if status == 'Processing':
                    query = """
                    UPDATE PrintQueue 
                    SET Status = ?, ProcessedAt = GETDATE()
                    WHERE Id = ?
                    """
                    cursor.execute(query, (status, job_id))
                    
                elif status == 'Completed':
                    query = """
                    UPDATE PrintQueue 
                    SET Status = ?, CompletedAt = GETDATE()
                    WHERE Id = ?
                    """
                    cursor.execute(query, (status, job_id))
                    
                elif status == 'Failed':
                    if increment_retry:
                        query = """
                        UPDATE PrintQueue 
                        SET Status = ?, ErrorMessage = ?, RetryCount = RetryCount + 1
                        WHERE Id = ?
                        """
                        cursor.execute(query, (status, error_message, job_id))
                    else:
                        query = """
                        UPDATE PrintQueue 
                        SET Status = ?, ErrorMessage = ?
                        WHERE Id = ?
                        """
                        cursor.execute(query, (status, error_message, job_id))
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to update job status: {e}")
            raise
    
    def add_print_log(self, job_id: int, printer_id: int, log_level: str, message: str):
        """印刷ログを追加"""
        query = """
        INSERT INTO PrintLog (JobId, PrinterId, LogLevel, Message, CreatedAt)
        VALUES (?, ?, ?, ?, GETDATE())
        """
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (job_id, printer_id, log_level, message))
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to add print log: {e}")
    
    def get_active_printers(self) -> List[Dict[str, Any]]:
        """有効なプリンター一覧を取得"""
        query = """
        SELECT Id, PrinterName, DisplayName, MaxRetryCount, TimeoutSeconds
        FROM PrinterMaster
        WHERE IsActive = 1
        ORDER BY DisplayName
        """
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                
                printers = []
                for row in cursor.fetchall():
                    printers.append({
                        'Id': row.Id,
                        'PrinterName': row.PrinterName,
                        'DisplayName': row.DisplayName,
                        'MaxRetryCount': row.MaxRetryCount,
                        'TimeoutSeconds': row.TimeoutSeconds
                    })
                
                return printers
                
        except Exception as e:
            self.logger.error(f"Failed to get active printers: {e}")
            return []