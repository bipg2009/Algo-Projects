"""
Lightweight Dhan client for backtests — no xlwings, no Market_Scanner import.
"""

import os
import sys

from dotenv import load_dotenv
from dhanhq import DhanContext, dhanhq


class BacktestTsl:
    def __init__(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for cred in (
            os.path.join(os.path.dirname(__file__), "cred.env"),
            os.path.join(root, "cred.env"),
            "cred.env",
        ):
            if os.path.isfile(cred):
                load_dotenv(cred)
                break

        client = os.getenv("DHAN_CLIENT_CODE")
        token = os.getenv("DHAN_TOKEN_ID")
        if not client or not token:
            raise RuntimeError(
                "Set DHAN_CLIENT_CODE and DHAN_TOKEN_ID in cred.env (project root or BackTesting/)."
            )

        self.Dhan = dhanhq(DhanContext(client, token))
        print("-----Logged into Dhan (backtest client)-----", flush=True)

    def convert_to_date_time(self, ts):
        return self.Dhan.convert_to_date_time(ts)


def get_scanner_module():
    """Object with .tsl for NSE-Option-Scanner-Backtest."""
    return type("BacktestScanner", (), {"tsl": BacktestTsl()})()
