import sys
import os
import time
import json
import threading
import subprocess
from pathlib import Path
import SafetyLogger
from oms_engine import OMSEngine

SCANNER_ROOT = Path(__file__).resolve().parent
os.chdir(SCANNER_ROOT)
if str(SCANNER_ROOT) not in sys.path:
    sys.path.insert(0, str(SCANNER_ROOT))

CRED_ENV = SCANNER_ROOT / "cred.env"
STATE_FILE = SCANNER_ROOT / "scanner_state.json"
SIGNAL_FILE = SCANNER_ROOT / "signal.json"
EXIT_SIGNAL_FILE = SCANNER_ROOT / "exit_signal.json"

def load_cred_env():
    if not CRED_ENV.is_file(): return
    try:
        from dotenv import load_dotenv
        load_dotenv(CRED_ENV)
    except Exception:
        pass

load_cred_env()

def get_live_client():
    client_code = os.getenv("DHAN_CLIENT_CODE")
    token_id = os.getenv("DHAN_TOKEN_ID")
    if not client_code or not token_id:
        return None
    try:
        import Dhan_Tradehull as tradehull
        return tradehull.Tradehull(client_code, token_id)
    except Exception as e:
        SafetyLogger.log_error_with_context("MainEngine", "get_live_client", e)
        return None

def release_scanner_lock():
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({"status": "SCAN", "updated_at": time.time()}, f)
    except Exception:
        pass

class AppEngine:
    def __init__(self):
        self.tsl = get_live_client()
        self.oms = OMSEngine(self.tsl)

    def init(self):
        self.oms.init()

    def start(self):
        self.oms.start()
        monitor_thread = threading.Thread(target=self._monitor_signals, daemon=True)
        monitor_thread.start()
        self._command_loop()

    def _command_loop(self):
        print("\n=== SYSTEM CONTROLLER ===")
        print("Type 'Market' to start Market_Scanner, 'atr' for ATR, 'pdb' for debugger, 'exit' to quit.")
        while True:
            try:
                cmd = input("(Controller)> ").strip().lower()
                if cmd == 'market':
                    kwargs = {"cwd": str(SCANNER_ROOT)}
                    if os.name == "nt": kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE
                    subprocess.Popen([sys.executable, str(SCANNER_ROOT / "Market_Scanner.py")], **kwargs)
                elif cmd == 'atr':
                    try:
                        import indicator_engine
                        import importlib
                        importlib.reload(indicator_engine)
                        if hasattr(indicator_engine, 'display_atr_details'):
                            indicator_engine.display_atr_details(self.tsl)
                        else:
                            print("Error: 'display_atr_details' not found in indicator_engine. Please ensure your local indicator_engine.py is fully synced with the cloud environment.")
                    except Exception as e:
                        print(f"Error showing ATR: {e}")
                elif cmd == 'pdb':
                    import pdb; pdb.set_trace()
                elif cmd == 'reload':
                    import oms_engine
                    import Trade_Calculator
                    import Option_strategy_core
                    import importlib
                    importlib.reload(Trade_Calculator)
                    importlib.reload(Option_strategy_core)
                    importlib.reload(oms_engine)
                    importlib.reload(sys.modules['MainEngine']) if 'MainEngine' in sys.modules else None
                    print("Modules reloaded!")
                elif cmd == 'exit' or cmd == 'quit':
                    break
            except Exception:
                break
        self.stop()

    def stop(self):
        self.oms.stop()

    def health_check(self):
        return self.oms.health_check()
    
    def _monitor_signals(self):
        while True:
            try:
                if SIGNAL_FILE.exists():
                    self._process_signal_file()
                if EXIT_SIGNAL_FILE.exists():
                    self._process_exit_signal_file()
            except Exception as e:
                SafetyLogger.log_error_with_context("MainEngine", "monitor", e)
            time.sleep(0.05)

    def _process_signal_file(self):
        with open(SIGNAL_FILE, "r") as f: data = json.load(f)
        SIGNAL_FILE.unlink()
        sym = data.get("symbol")
        typ = data.get("option_type")
        score = data.get("score", 0)
        if not self.oms.execute_verified_signal(sym, typ, score):
            release_scanner_lock()

    def _process_exit_signal_file(self):
        with open(EXIT_SIGNAL_FILE, "r") as f: data = json.load(f)
        from excel_ledger_orderbook import log_execution_to_excel_ledger
        import threading
        if data.get("partial_logged"):
            try:
                threading.Thread(target=log_execution_to_excel_ledger, args=(data["order_id"], data["symbol"], "SELL_CONFIRMED", data["qty"], data["price"], data["margin_used"]), daemon=True).start()
            except Exception: pass
        EXIT_SIGNAL_FILE.unlink()

def run_main_engine():
    app = AppEngine()
    app.init()
    if len(sys.argv) >= 4:
        sym, typ, score_str = sys.argv[1], sys.argv[2], sys.argv[3]
        try:
            score = int(float(score_str))
        except ValueError:
            score = 0
        if not app.oms.execute_verified_signal(sym, typ, score):
            release_scanner_lock()
    else:
        app.start()

if __name__ == "__main__":
    run_main_engine()
