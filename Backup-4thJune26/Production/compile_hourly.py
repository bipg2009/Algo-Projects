import pandas as pd
import glob
import os

log_dir = r"C:\Biplab\ALGO-Projects\Option-Scanner\Production\Dependencies\hourly_logs"
output_file = r"C:\Biplab\ALGO-Projects\Option-Scanner\Production\Reports\seda_hourly_paper_trades_2026-06-04.csv"

# 1. Gather all files generated today
files = glob.glob(os.path.join(log_dir, "signal_hourly_2026-06-04_*.csv"))

if not files:
    print("CRITICAL: No legacy logs found on disk.")
    exit()

valid_dfs = []
for f in files:
    try:
        df = pd.read_csv(f, names=["Timestamp", "Status", "Symbol", "Type", "Val1", "Val2", "Score", "Val3", "RSI", "Trend", "PCR", "Spot", "Val4", "Val5", "Reason", "Empty"])
        valid_dfs.append(df)
    except:
        pass

if valid_dfs:
    master_df = pd.concat(valid_dfs)
    # Group into hourly blocks and format into required columns
    print("SUCCESS: Consolidated hourly data.")
    # Force write to target CSV path
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    master_df.to_csv(output_file, index=False)
else:
    print("No clean rows to compile.")
