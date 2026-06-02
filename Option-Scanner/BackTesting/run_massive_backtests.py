import os
import sys
import shutil
import subprocess
import time

# =====================================================================
# GLOBAL PATH & PIPELINE CONFIGURATIONS
# =====================================================================
WORKSPACE_DIR = r"C:\Biplab\ALGO-Projects\Option-Scanner"
REPORTS_NSE_DIR = (
    r"C:\Biplab\ALGO-Projects\Option-Scanner\BackTesting\Reports\NSE\2025_Q4"
)
TARGET_EXCHANGE = "NSE"

CHUNKS = [
    ("01-10-2025", "31-12-2025", "2025_Q4"),
]


# =====================================================================
# CLEAN FILE UTILITIES (Completely Discarded Regex Operations)
# =====================================================================
def copy_reports(phase_folder, chunk_name):
    """
    Copies backtest reports from workspace/Dependencies/backtest_results
    strictly to the designated local Reports directory.
    """
    src_dir = os.path.join(WORKSPACE_DIR, "Dependencies", "backtest_results")
    dest_dir_local = os.path.join(REPORTS_NSE_DIR, phase_folder, chunk_name)

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
            dest_file_loc = os.path.join(dest_dir_local, filename)
            shutil.copy2(src_file, dest_file_loc)
            copied_local += 1

    print(f"[REPORT] Copied {copied_local} reports locally to: {dest_dir_local}")


def run_chunk(start_date, end_date):
    """
    Runs the multi-day backtest for a specific chunk using clean subprocess args.
    """
    print(
        f"\n[RUNNING] Starting backtest chunk: {start_date} to {end_date} for {TARGET_EXCHANGE}..."
    )

    script_path = os.path.join(WORKSPACE_DIR, "BackTesting", "multi_day_backtest.py")

    # Clean positional arguments. No dynamic text-file modifications needed.
    cmd = [
        sys.executable,
        script_path,
        start_date,
        end_date,
        TARGET_EXCHANGE,
    ]

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

    results_dir = os.path.join(WORKSPACE_DIR, "Dependencies", "backtest_results")
    os.makedirs(results_dir, exist_ok=True)
    summary_txt_path = os.path.join(results_dir, "Console_Summary.txt")
    with open(summary_txt_path, "w", encoding="utf-8") as sf:
        sf.writelines(captured_lines)
    print(f"[CONSOLE LOG] Saved captured screen output to: {summary_txt_path}")

    return rc == 0


# =====================================================================
# PIPELINE AUTOMATION CONTROL ENGINE
# =====================================================================
def run_pipeline():
    """
    Executes historical sweeps reliably using your central System_Config values.
    """
    try:
        print("\n" + "=" * 80)
        print("                   STARTING MOMENTUM PIPELINE SWEEP")
        print("=" * 80)
        print("[INFO] Utilizing clean centralized thresholds from System_Config.py")

        # Iteratively execute active historical date ranges
        for start_dt, end_dt, name in CHUNKS:
            print(f"\n>>> Processing {name} ({start_dt} to {end_dt})")
            success = run_chunk(start_dt, end_dt)
            if success:
                # Saves output directly to our configured destination
                copy_reports("Momentum_RSI_65_Exit_60", name)
            else:
                print(f"[WARN] Chunk {name} failed or completed with errors.")
            time.sleep(2)

    except Exception as e:
        print(f"[CRITICAL ERROR] Pipeline execution encountered a crash: {e}")

    finally:
        print("\n[COMPLETE] Clean automated backtest pipeline execution finished.")


if __name__ == "__main__":
    run_pipeline()
