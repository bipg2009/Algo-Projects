"""
Lightweight Dhan client for backtests — no xlwings, no Market_Scanner import.
"""

import os
import sys

from dotenv import load_dotenv
from dhanhq import DhanContext, dhanhq


class BacktestTsl:
    def __init__(self):
        import base64
        import json
        import time
        
        def is_token_valid(token_str):
            try:
                parts = token_str.split('.')
                if len(parts) < 2:
                    return False
                payload_b64 = parts[1]
                payload_b64 += '=' * (4 - len(payload_b64) % 4)
                payload = json.loads(base64.b64decode(payload_b64).decode('utf-8'))
                return payload.get("exp", 0) > (time.time() + 300)
            except Exception:
                return False

        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # 1. First attempt: Load cred.env
        cred_loaded = False
        for cred_file in (
            os.path.join(os.path.dirname(__file__), "cred.env"),
            os.path.join(root, "cred.env"),
            "cred.env",
        ):
            if os.path.isfile(cred_file):
                load_dotenv(cred_file, override=True)
                cred_loaded = True
                break

        client = os.getenv("DHAN_CLIENT_CODE")
        token = os.getenv("DHAN_TOKEN_ID")
        
        # 2. Check if token is expired/invalid. If so, fall back to cred1.env
        if not cred_loaded or not token or not is_token_valid(token):
            print("[AUTH] cred.env token is expired, invalid, or missing. Falling back to cred1.env...", flush=True)
            for cred1_file in (
                os.path.join(os.path.dirname(__file__), "cred1.env"),
                os.path.join(root, "cred1.env"),
                "cred1.env",
            ):
                if os.path.isfile(cred1_file):
                    load_dotenv(cred1_file, override=True)
                    client = os.getenv("DHAN_CLIENT_CODE")
                    token = os.getenv("DHAN_TOKEN_ID")
                    break

        if not client or not token:
            raise RuntimeError(
                "Set DHAN_CLIENT_CODE and DHAN_TOKEN_ID in cred.env or cred1.env (project root or BackTesting/)."
            )

        self.Dhan = dhanhq(DhanContext(client, token))
        print("-----Logged into Dhan (backtest client)-----", flush=True)


    def convert_to_date_time(self, ts):
        return self.Dhan.convert_to_date_time(ts)


def get_scanner_module():
    """Object with .tsl for NSE-Option-Scanner-Backtest."""
    return type("BacktestScanner", (), {"tsl": BacktestTsl()})()
