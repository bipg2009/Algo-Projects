#!/usr/bin/env python3
"""
Excel-compatible order execution ledger (CSV).
Used by MainEngine.py after each BUY/SELL.
"""

import os
import csv
import time
import datetime
from pathlib import Path

SCANNER_ROOT = Path(__file__).resolve().parent
DEFAULT_LEDGER = SCANNER_ROOT / "trading_execution_ledger.csv"


def log_info(msg):
    print(f"[\033[94mINFO\033[0m] {msg}")


def log_success(msg):
    print(f"[\033[92mSUCCESS\033[0m] {msg}")


def log_warn(msg):
    print(f"[\033[93mWARN\033[0m] {msg}")


def log_error(msg):
    print(f"[\033[91mERROR\033[0m] {msg}")


def log_execution_to_excel_ledger(
    order_id,
    symbol,
    action,
    quantity,
    price,
    margin_used,
    ledger_file=None,
):
    """
    Append one execution row to trading_execution_ledger.csv in Option Scanner folder.
    Retries if the file is locked (e.g. open in Excel).
    """
    if ledger_file is None:
        ledger_path = DEFAULT_LEDGER
    else:
        ledger_path = Path(ledger_file)
        if not ledger_path.is_absolute():
            ledger_path = SCANNER_ROOT / ledger_path

    headers = [
        "Timestamp",
        "Order ID",
        "Symbol",
        "Action (BUY/SELL)",
        "Quantity",
        "Execution Price (INR)",
        "Margin Consumed (INR)",
        "System Status",
    ]

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row_data = [
        timestamp,
        order_id,
        symbol,
        action.upper(),
        quantity,
        f"Rs {price:,.2f}",
        f"Rs {margin_used:,.2f}",
        "FILLED",
    ]

    max_retries = 5
    retry_delay = 1.5
    ledger_str = str(ledger_path)

    for attempt in range(max_retries):
        try:
            file_exists = ledger_path.is_file()
            with open(ledger_str, mode="a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(headers)
                    log_success(f"Initialized new ledger: '{ledger_str}'")
                writer.writerow(row_data)

            log_success(
                f"Ledger entry recorded: [OrderID: {order_id}] "
                f"{action.upper()} {quantity} of {symbol} @ Rs {price}"
            )
            return True

        except PermissionError:
            log_warn(
                f"File locked: '{ledger_str}' may be open in Excel. "
                f"Retry {attempt + 1}/{max_retries} in {retry_delay}s..."
            )
            time.sleep(retry_delay)

        except Exception as e:
            log_error(f"Failed to write ledger: {e}")
            break

    log_error(f"Could not write order {order_id} to ledger.")
    return False
