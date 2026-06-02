import os
import sys
import datetime
import traceback
from pathlib import Path

SCANNER_ROOT = Path(__file__).resolve().parent
LOG_DIR = SCANNER_ROOT / "Dependencies" / "log_files"

def log_error_with_context(module_name: str, operation_name: str, error: Exception, context_dict: dict = None):
    """
    Standardized, timestamped logging of critical trading algorithm errors with context.
    Persists to Dependencies/log_files/error_safety_arena.log and prints to standard output with coloring.
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
    except Exception:
        pass
        
    error_msg = f"[{timestamp}] [CRITICAL ERROR] [{module_name}] in [{operation_name}]: {error}\n"
    if context_dict:
        error_msg += f"    Context: {context_dict}\n"
    error_msg += "    Traceback:\n"
    tb_str = "".join(traceback.format_exception(type(error), error, error.__traceback__))
    for line in tb_str.splitlines():
        error_msg += f"        {line}\n"
    error_msg += "-" * 80 + "\n"
    
    # 1. Print formatted ANSI error to terminal for the operator
    print(f"\n\033[91m[SAFETY ENGINE ALERT - {timestamp}]\033[0m", flush=True)
    print(f"\033[91mModule: {module_name} | Operation: {operation_name}\033[0m", flush=True)
    print(f"\033[93mSeverity: HIGH | Exception: {error}\033[0m", flush=True)
    if context_dict:
        print(f"\033[94mContext: {context_dict}\033[0m", flush=True)
    print("\033[91mTraceback Output:\033[0m", flush=True)
    print(tb_str, flush=True)
    
    # 2. Append to persistent error_safety_arena.log file
    log_file = LOG_DIR / "error_safety_arena.log"
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(error_msg)
    except Exception as e:
        print(f"[-] [SafetyLogger] Failed to write to {log_file}: {e}", flush=True)
        
    # 3. Safely update Communication registry of status
    try:
        import Communication
        # Map filenames to exact naming used in registry
        reg_name = module_name
        if not reg_name.endswith(".py"):
            reg_name += ".py"
        Communication.update_module_status(reg_name, "ERROR", error=str(error))
    except Exception:
        pass
