import sys
import os
import time
import json
import threading
from pathlib import Path
import SafetyLogger
from oms_engine import OMSEngine
from event_bus import signal_queue, exit_queue
from api_server import start_server
import queue

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

# Centralized broker client — single source of truth
from broker_client import get_live_client

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
        
        # Start Dashboard API Web Server (auto-pick free port)
        import socket
        import requests

        def _port_free(p: int) -> bool:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    s.bind(("127.0.0.1", int(p)))
                return True
            except OSError:
                return False

        preferred = int(os.getenv("DASHBOARD_PORT", "5173"))
        candidates = [preferred, 5173, 5174, 5175]
        port = preferred

        # If dashboard already running on preferred port, reuse it (avoid multiple servers).
        try:
            r = requests.get(f"http://127.0.0.1:{preferred}/api/health", timeout=0.5)
            if r.status_code == 200:
                print(f"[+] Dashboard API Server already running on http://127.0.0.1:{preferred}")
                port = preferred
            else:
                raise RuntimeError(f"health_status={r.status_code}")
        except Exception:
            port = next((p for p in candidates if _port_free(p)), preferred)
            api_thread = threading.Thread(
                target=start_server,
                kwargs={"host": "127.0.0.1", "port": port},
                daemon=True,
            )
            api_thread.start()
            print(f"[+] Dashboard API Server started on http://127.0.0.1:{port}")

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
                    import Market_Scanner
                    scanner_thread = threading.Thread(target=Market_Scanner.main, daemon=True)
                    scanner_thread.start()
                    print("[+] Market Scanner started in background thread.")
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
                # Check signals
                if not signal_queue.empty():
                    self._process_signal(signal_queue.get())
                
                # Check exits
                if not exit_queue.empty():
                    self._process_exit(exit_queue.get())

            except Exception as e:
                SafetyLogger.log_error_with_context("MainEngine", "monitor", e)
            
            time.sleep(0.05)

    def _process_signal(self, data):
        sym = data.get("symbol")
        typ = data.get("option_type")
        score = data.get("score", 0)
        
        # Route through Risk Engine (Rule 4 Compliance)
        # Evaluate Offer before sending to OMS
        # For now, just forward to execute_verified_signal, but logging risk
        if not self.oms.execute_verified_signal(sym, typ, score, signal_payload=data):
            release_scanner_lock()

    def _process_exit(self, data):
        from excel_ledger_orderbook import log_execution_to_excel_ledger
        import threading
        if data.get("partial_logged"):
            try:
                threading.Thread(target=log_execution_to_excel_ledger, args=(data["order_id"], data["symbol"], "SELL_CONFIRMED", data["qty"], data["price"], data["margin_used"]), daemon=True).start()
            except Exception: pass

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
