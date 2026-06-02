import os
import sys
import shutil
import subprocess
import time
import re

# Configurations
# ONEDRIVE_BASE = r"C:\Users\bipla\OneDrive\BACKTEST"
WORKSPACE_DIR = r"C:\Biplab\ALGO-Projects\Option-Scanner\BackTesting\Reports\NSE"

CHUNKS = [
    # ("01-01-2025", "31-03-2025", "2025_Q1"), # Completed & copied locally
    ("01-04-2025", "30-06-2025", "2025_Q2"),
    ("01-07-2025", "30-09-2025", "2025_Q3"),
    ("01-10-2025", "31-12-2025", "2025_Q4"),
    ("01-01-2026", "31-03-2026", "2026_Q1"),
    ("01-04-2026", "30-06-2026", "2026_Q2"),
]


def modify_file(filepath, patterns):
    """
    Reads a file, applies a list of (regex_pattern, replacement) tuples, and writes it back.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    original = content
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)

    if content != original:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[CONFIG] Modified {os.path.basename(filepath)}")
    else:
        print(f"[CONFIG] No changes needed for {os.path.basename(filepath)}")


def backup_file(filepath):
    backup_path = filepath + ".bak"
    shutil.copy2(filepath, backup_path)
    print(f"[BACKUP] Created backup of {os.path.basename(filepath)}")


def restore_file(filepath):
    backup_path = filepath + ".bak"
    if os.path.exists(backup_path):
        shutil.move(backup_path, filepath)
        print(f"[BACKUP] Restored {os.path.basename(filepath)} from backup")


def copy_reports(phase_folder, chunk_name):
    """
    Copies the backtest reports from workspace/Dependencies/backtest_results
    strictly to the local Reports/May-Runs folder.
    """
    src_dir = os.path.join(WORKSPACE_DIR, "Dependencies", "backtest_results")

    # Copy strictly to local Reports/May-Runs folder
    dest_dir_local = os.path.join(
        WORKSPACE_DIR, "BackTesting", "Reports", "May-Runs", phase_folder, chunk_name
    )
    os.makedirs(dest_dir_local, exist_ok=True)

    files_to_copy = [
        "Aggregated_NORMAL_Report.csv",
        "Aggregated_HEIKIN_ASHI_Report.csv",
        "Aggregated_VOLUME_Report.csv",
        "Candle_Comparison_Report.csv",
        "Console_Summary.txt",
    ]

    copied_local = 0
    for filename in files_to_copy:
        src_file = os.path.join(src_dir, filename)
        if os.path.exists(src_file):
            # Local copy
            dest_file_loc = os.path.join(dest_dir_local, filename)
            shutil.copy2(src_file, dest_file_loc)
            copied_local += 1

    print(f"[REPORT] Copied {copied_local} reports locally to: {dest_dir_local}")


def run_chunk(start_date, end_date):
    """
    Runs the multi-day backtest for a specific chunk using subprocess.
    """
    print(f"\n[RUNNING] Starting backtest chunk: {start_date} to {end_date}...")
    cmd = [sys.executable, "multi_day_backtest.py", start_date, end_date]

    # We execute and stream stdout to the console/log
    process = subprocess.Popen(
        cmd,
        cwd=WORKSPACE_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    captured_lines = []
    while True:
        output = process.stdout.readline()
        if output == "" and process.poll() is not None:
            break
        if output:
            stripped = output.strip()
            print(stripped)
            captured_lines.append(output)

    rc = process.poll()
    if rc != 0:
        print(f"[ERROR] Backtest process failed with return code {rc}")

    # Write captured console output to a summary file
    results_dir = os.path.join(WORKSPACE_DIR, "Dependencies", "backtest_results")
    os.makedirs(results_dir, exist_ok=True)
    summary_txt_path = os.path.join(results_dir, "Console_Summary.txt")
    with open(summary_txt_path, "w", encoding="utf-8") as sf:
        sf.writelines(captured_lines)
    print(f"[CONSOLE LOG] Saved captured screen output to: {summary_txt_path}")

    return rc == 0


def run_pipeline():
    # Make backups of configs first to guarantee we leave them untouched
    config_file = os.path.join(WORKSPACE_DIR, "System_Config.py")
    strategy_file = os.path.join(WORKSPACE_DIR, "Uptrend_Buy.py")

    backup_file(config_file)
    backup_file(strategy_file)

    try:
        # ==========================================
        # PHASE 1: Standard Configuration (RSI 61.0)
        # ==========================================
        print("\n" + "=" * 80)
        print("                   STARTING PHASE 1: STANDARD CONFIG (RSI 58.0)")
        print("=" * 80)

        # 1. Enable CE trades and ensure CE_RSI_TRIGGER is 58.0
        patterns_phase1 = [
            (r"ENABLE_CE_TRADES:\s*bool\s*=\s*\w+", "ENABLE_CE_TRADES: bool = True"),
            (r"CE_RSI_TRIGGER:\s*float\s*=\s*[0-9.]+", "CE_RSI_TRIGGER: float = 58.0"),
        ]
        modify_file(config_file, patterns_phase1)

        for start_dt, end_dt, name in CHUNKS:
            print(f"\n>>> Phase 1: Processing {name} ({start_dt} to {end_dt})")
            success = run_chunk(start_dt, end_dt)
            if success:
                copy_reports("Standard_RSI_61", name)
            else:
                print(f"[WARN] Chunk {name} failed or completed with errors.")
            time.sleep(2)  # Brief cooldown between chunks

        # ==========================================
        # PHASE 2: RSI 75+ Configuration
        # ==========================================
        print("\n" + "=" * 80)
        print("                   STARTING PHASE 2: RSI 75+ CONFIG")
        print("=" * 80)

        # 1. Set CE_RSI_TRIGGER to 75.0
        patterns_phase2_config = [
            (r"CE_RSI_TRIGGER:\s*float\s*=\s*[0-9.]+", "CE_RSI_TRIGGER: float = 75.0")
        ]
        modify_file(config_file, patterns_phase2_config)

        # 2. Relax FOMO ceiling in Uptrend_Buy.py from 75.0 to 85.0
        patterns_phase2_strategy = [
            (r"curr_rsi\s*>\s*75\.0", "curr_rsi > 85.0"),
            (r"BELOW\s*75\.0", "BELOW 85.0"),
        ]
        modify_file(strategy_file, patterns_phase2_strategy)

        for start_dt, end_dt, name in CHUNKS:
            print(f"\n>>> Phase 2: Processing {name} ({start_dt} to {end_dt})")
            success = run_chunk(start_dt, end_dt)
            if success:
                copy_reports("RSI_75_Config", name)
            else:
                print(f"[WARN] Chunk {name} failed or completed with errors.")
            time.sleep(2)  # Brief cooldown between chunks

    except Exception as e:
        print(f"[CRITICAL ERROR] Pipeline execution encountered a crash: {e}")

    finally:
        # Guarantee restore of files
        restore_file(config_file)
        restore_file(strategy_file)
        print("\n[COMPLETE] Massive automated backtest pipeline finished execution.")


if __name__ == "__main__":
    run_pipeline()
