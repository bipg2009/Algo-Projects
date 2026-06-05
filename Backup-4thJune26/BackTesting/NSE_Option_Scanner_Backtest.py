"""
NSE Option Scanner backtest (full Dhan/API engine).
Reports are written to BackTesting/Reports/.

Usage:
    python NSE_Option_Scanner_Backtest.py 2026-05-22
    python NSE_Option_Scanner_Backtest.py 2026-05-22 --expiry 1
    python NSE_Option_Scanner_Backtest.py 2026-05-22 -t 5

Strategy: 1m bars, session 09:15–15:30 IST, hard exit 15:12.
-t / --timeframes is legacy only (ignored).
"""

import argparse
import importlib.util
import os
import re
import sys
import traceback
import Dhan_Tradehull as tradehull  

# Move up one level from 'BackTesting' to 'Option Scanner'
sys.path.append(r"C:\Biplab\DHAN\ALGO\2025\Option Scanner")
import MainEngine as main_engine    

BACKTEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BACKTEST_DIR)
REPORTS_DIR = os.path.join(BACKTEST_DIR, "Reports")
DEFAULT_EXPIRY_CODE = 1

_FULL_ENGINE = None


def _load_full_engine():
    global _FULL_ENGINE
    if _FULL_ENGINE is not None:
        return _FULL_ENGINE

    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)
    os.chdir(PROJECT_ROOT)

    engine_path = os.path.join(PROJECT_ROOT, "NSE-Option-Scanner-Backtest.py")
    spec = importlib.util.spec_from_file_location("nse_full_backtest", engine_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _FULL_ENGINE = mod
    return mod


def run_backtest(test_date, timeframe=None, expiry_code=DEFAULT_EXPIRY_CODE):
    """
    Run the full 1m setup + 1m trigger backtest.
    timeframe is accepted for CLI compatibility but not used by the full engine.
    """
    if timeframe is not None:
        print(
            f"Note: full backtest uses 1m only; ignoring timeframe={timeframe}m.",
            flush=True,
        )

    os.makedirs(REPORTS_DIR, exist_ok=True)
    prev_cwd = os.getcwd()
    os.chdir(PROJECT_ROOT)
    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)

    try:
        engine = _load_full_engine()
        return engine.run_backtest(
            test_date,
            expiry_code,
            results_dir=REPORTS_DIR,
        )
    finally:
        os.chdir(prev_cwd)


_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$|^\d{2}-\d{2}-\d{4}$")


def _parse_timeframe(value):
    try:
        return int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid timeframe: {value}")


def _validate_date(value):
    if value.startswith("-") and value[1:].isdigit():
        raise argparse.ArgumentTypeError(
            f"'{value}' looks like a timeframe flag, not a date. "
            "Use: py NSE_Option_Scanner_Backtest.py 2026-05-22 -t 5"
        )
    if not _DATE_RE.match(value):
        raise argparse.ArgumentTypeError(
            f"Invalid date '{value}'. Use YYYY-MM-DD (e.g. 2026-05-22)."
        )
    return value


def main():
    parser = argparse.ArgumentParser(
        description="Run NSE option scanner backtest; CSVs go to BackTesting/Reports/.",
        epilog="Example: py NSE_Option_Scanner_Backtest.py 2026-05-22 -t 5",
    )
    parser.add_argument(
        "date",
        type=_validate_date,
        help="Test date YYYY-MM-DD (required; not -5 alone)",
    )
    parser.add_argument(
        "--expiry",
        "-e",
        type=int,
        default=DEFAULT_EXPIRY_CODE,
        help="Expiry code for option chain (0-3). Default: 1",
    )
    parser.add_argument(
        "--timeframes",
        "-t",
        type=_parse_timeframe,
        default=None,
        help="Legacy flag (e.g. 5). Engine is 1m-only; value is ignored.",
    )
    args = parser.parse_args()

    try:
        run_backtest(args.date, timeframe=args.timeframes, expiry_code=args.expiry)
    except Exception:
        print("Backtest failed. Traceback:", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)

    print(f"\nReports folder: {REPORTS_DIR}")


if __name__ == "__main__":
    main()
