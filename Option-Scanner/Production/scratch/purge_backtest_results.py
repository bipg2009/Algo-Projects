import os
import glob

RESULTS_DIR = r"c:\Biplab\ALGO-Projects\Option-Scanner\Dependencies\backtest_results"

def main():
    print("=" * 60)
    print("PURGING OLD BACKTEST RESULTS")
    print("=" * 60)
    
    # Files to delete
    patterns = [
        "backtest_trades_*.csv",
        "backtest_monitor_*.csv",
        "backtest_scan_log_*.csv",
        "backtest_summary_*.csv",
        "Aggregated_*.csv",
        "Candle_Comparison_Report.csv",
        "Consolidated_*.csv"
    ]
    
    deleted_count = 0
    for pat in patterns:
        files = glob.glob(os.path.join(RESULTS_DIR, pat))
        for f in files:
            try:
                os.remove(f)
                deleted_count += 1
            except Exception as e:
                print(f"Error deleting {f}: {e}")
                
    print(f"Purged {deleted_count} stale/corrupted backtest files.")
    print("Your backtest_results folder is now clean and ready for fresh runs!")

if __name__ == "__main__":
    main()
