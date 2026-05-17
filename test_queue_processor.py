"""
QueueProcessor._process_single_job のリトライ判定テスト
仕様: docs/adr/0001-dynamic-paper-height.md
"""

import sys
import unittest
from unittest.mock import MagicMock, patch

# テスト環境 (Linux/CI) には pyodbc が無いので import 前にモックを差し込む
sys.modules.setdefault('pyodbc', MagicMock())

from queue_processor import QueueProcessor  # noqa: E402


JOB_TEMPLATE = {
    'Id': 1,
    'JobName': 'test-job',
    'PrinterId': 10,
    'PrintUrl': 'http://example.test/label/1',
    'PrinterName': 'P1',
    'RetryCount': 0,
    'MaxRetryCount': 3,
}


class ProcessSingleJobTest(unittest.TestCase):

    def setUp(self):
        # インスタンス化時の DatabaseManager / PrinterService をモックに差し替える
        with patch('queue_processor.DatabaseManager'), patch('queue_processor.PrinterService'):
            self.qp = QueueProcessor()
        self.qp.db_manager = MagicMock()
        self.qp.printer_service = MagicMock()

    def _status_history(self):
        # update_job_status の第2引数 (status) の履歴
        return [c.args[1] for c in self.qp.db_manager.update_job_status.call_args_list]

    def test_permanent_error_skips_retry(self):
        """retryable=False の失敗はリトライせず即 Failed"""
        self.qp.printer_service.print_web_url.return_value = (
            False, "invalid paper_height: out of range", False,
        )
        self.qp._process_single_job(dict(JOB_TEMPLATE, RetryCount=0))

        self.assertEqual(self._status_history(), ['Processing', 'Failed'])

    def test_retryable_error_within_limit_marks_pending(self):
        """retryable=True かつリトライ枠が残っていれば Pending に戻す"""
        self.qp.printer_service.print_web_url.return_value = (
            False, "timeout", True,
        )
        self.qp._process_single_job(dict(JOB_TEMPLATE, RetryCount=0))

        self.assertEqual(self._status_history(), ['Processing', 'Pending'])

    def test_retryable_error_at_limit_marks_failed(self):
        """retryable=True でもリトライ上限に達していれば Failed"""
        self.qp.printer_service.print_web_url.return_value = (
            False, "timeout", True,
        )
        self.qp._process_single_job(dict(JOB_TEMPLATE, RetryCount=3, MaxRetryCount=3))

        self.assertEqual(self._status_history(), ['Processing', 'Failed'])

    def test_success_marks_completed(self):
        self.qp.printer_service.print_web_url.return_value = (
            True, "Web印刷完了", True,
        )
        self.qp._process_single_job(dict(JOB_TEMPLATE))

        self.assertEqual(self._status_history(), ['Processing', 'Completed'])


if __name__ == '__main__':
    unittest.main()
