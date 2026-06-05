# Running-Backtest.py
import argparse
from NSE_Option_Scanner_Backtest import REPORTS_DIR, run_backtest

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run NSE option scanner backtest (output: BackTesting/Reports/)"
    )
    parser.add_argument("date", help="Date to backtest (YYYY-MM-DD)")
    parser.add_argument(
        "--expiry",
        "-e",
        type=int,
        default=1,
        help="Expiry code for option chain (0-3). Default: 1",
    )
    args = parser.parse_args()

    run_backtest(args.date, expiry_code=args.expiry)
    print(f"\nReports folder: {REPORTS_DIR}")
