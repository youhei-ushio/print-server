#!/usr/bin/env python3
"""
印刷認証トークン生成スクリプト
使用方法: python generate_token.py
"""

import secrets
import string

def generate_print_token(length=64):
    """セキュアな印刷認証トークンを生成"""
    # 英数字 + 一部記号の文字セット
    alphabet = string.ascii_letters + string.digits + '-_'
    return ''.join(secrets.choice(alphabet) for _ in range(length))

if __name__ == '__main__':
    token = generate_print_token()
    print(f"PRINT_AUTH_TOKEN={token}")
    print(f"\n生成されたトークン: {token}")
    print(f"文字数: {len(token)}")
    print("\n設定方法:")
    print("1. Laravel側 (.env): 上記の行を追加")
    print("2. プリントサーバー側 (print_server/.env): 上記の行を追加")