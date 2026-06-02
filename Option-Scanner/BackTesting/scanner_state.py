import sys
import os
import time
import json
import datetime
from System_Config import STATE_FILE, MUTE_RELEASE_SEC

def set_shared_state(status_str: str) -> None:
    try:
        with open(STATE_FILE, "w") as f:
            json.dump({"status": status_str, "updated_at": time.time()}, f)
    except Exception as e:
        print(f"[-] Shared state write failure: {e}", flush=True)

def get_shared_state() -> str:
    try:
        with open(STATE_FILE, "r") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data.get("status", "SCAN")
            return "SCAN"
    except Exception:
        return "SCAN"

def maybe_release_stale_mute() -> None:
    if not os.path.exists(STATE_FILE):
        return
    try:
        with open(STATE_FILE, "r") as f:
            data = json.load(f)
        if data.get("status") != "MUTE":
            return
        updated = float(data.get("updated_at", 0))
        if time.time() - updated > MUTE_RELEASE_SEC:
            set_shared_state("SCAN")
    except Exception:
        pass

def await_915_market_open() -> None:
    print(f"[*] Core Scanner initialized at {datetime.datetime.now().strftime('%H:%M:%S')}.", flush=True)
    while True:
        now = datetime.datetime.now()
        if now.weekday() < 5 and now.time() >= datetime.time(9, 15):
            print("[+] 09:15 AM Market Opening boundary breached. Beginning data routing loops.", flush=True)
            break
        if now.weekday() >= 5:
            print("[-] Weekend detected. Scanner shutting down.", flush=True)
            sys.exit(0)
        print(f"[{now.strftime('%H:%M:%S')}] Pre-market session. Awaiting 9:15 AM open...", flush=True)
        time.sleep(30.0)
