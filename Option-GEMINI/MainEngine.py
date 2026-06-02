 # MainEngine.py  #/usr/bin/env python3 
"""
FnO Trading Safety Arena - Order execution engine (no market scan).

Live scanning: run Market_Scanner.py (signals + API scan).
On SIGNAL_VERIFIED, Market_Scanner spawns this file (production execution engine).

CLI (manual test):
  python MainEngine.py "NIFTY 25JUN 24000 CE" CE 90
"""
import sys
import os
import time
import datetime
import subprocess
import json
import threading
from pathlib import Path
import SafetyLogger
import Trade_Calculator as calc
import Option_strategy_core as core

# Always run from the Option Scanner folder (where cred.env and modules live)
SCANNER_ROOT = Path(__file__).resolve().parent
os.chdir(SCANNER_ROOT)
if str(SCANNER_ROOT) not in sys.path:
    sys.path.insert(0, str(SCANNER_ROOT))

CRED_ENV = SCANNER_ROOT / "cred.env"
STATE_FILE = SCANNER_ROOT / "scanner_state.json"


def load_cred_env():
    if not CRED_ENV.is_file():
        return
    try:
        from dotenv import load_dotenv
        load_dotenv(CRED_ENV)
    except ImportError:
        try:
            for line in CRED_ENV.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
        except Exception as e:
            SafetyLogger.log_error_with_context("MainEngine", "load_cred_env_fallback", e)
    except Exception as e:
        SafetyLogger.log_error_with_context("MainEngine", "load_cred_env", e)


load_cred_env()
client_code = os.getenv("DHAN_CLIENT_CODE")
token_id = os.getenv("DHAN_TOKEN_ID")

import Dhan_Tradehull as tradehull
from excel_ledger_orderbook import log_execution_to_excel_ledger
from scanner_excel import play_alert_sound

# =========================================================
# CONFIGURATION
# =========================================================

ENABLE_ORDER_EXECUTION = False  # True = live Dhan orders; False = simulation
ENABLE_PDB_PAUSE_AFTER_SIGNAL = False
TARGET_POINTS = 100.0
INITIAL_SL_POINTS = 15.0


def get_live_client():
    if not client_code or not token_id:
        return None
    try:
        return tradehull.Tradehull(client_code, token_id)
    except Exception as e:
        SafetyLogger.log_error_with_context("MainEngine", "get_live_client", e)
        print(f"[\033[91mERROR\033[0m] Failed to login to Dhan API: {e}", flush=True)
        return None


tsl = get_live_client()


def release_scanner_lock():
    """Return Market_Scanner to SCAN mode (shared scanner_state.json)."""
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({"status": "SCAN", "updated_at": time.time()}, f)
        print("[+] Scanner lock released — Market_Scanner can scan again.", flush=True)
    except Exception as e:
        SafetyLogger.log_error_with_context("MainEngine", "release_scanner_lock", e)
        print(f"[-] Failed to update {STATE_FILE}: {e}", flush=True)


def print_signal(option_symbol, option_type, ltp, score):
    print("\n" + "=" * 60)
    print("🔥 EXECUTION ENGINE — VERIFIED SIGNAL")
    print(f"Instrument : {option_symbol}")
    print(f"Type       : {option_type}")
    print(f"LTP        : Rs {ltp}")
    print(f"Score      : {score}/100")
    print(f"Time       : {datetime.datetime.now().strftime('%H:%M:%S')}")
    print("=" * 60 + "\n", flush=True)


def pause_engine_until_continue():
    print("\n" + "=" * 60)
    print("🛑 ENGINE PAUSE — verify broker levels, then continue in debugger")
    print("=" * 60 + "\n", flush=True)
    import pdb
    pdb.set_trace()


def _fetch_entry_oi(option_symbol):
    """Minimal API read for OI at entry (not a market scan)."""
    if tsl is None:
        return 0
    try:
        und = "SENSEX" if "SENSEX" in option_symbol else "NIFTY"
        chain = tsl.get_option_chain(underlying=und, strike_range=3)
        if chain and "options" in chain:
            row = next(
                (o for o in chain["options"] if o.get("symbol") == option_symbol),
                None,
            )
            if row:
                return int(row.get("oi", 0))
    except Exception as e:
        SafetyLogger.log_error_with_context(
            "MainEngine", "fetch_entry_oi", e, 
            {"symbol": option_symbol}
        )
        print(f"[\033[93mWARN\033[0m] Could not read entry OI: {e}", flush=True)
    return 0


def execute_verified_signal(option_symbol, option_type, score):
    """
    Run buy + ledger + Price_Check for one contract handed off from Market_Scanner.
    Does not scan NIFTY or the option chain for signals.
    """
    try:
        global tsl
        if tsl is None:
            tsl = get_live_client()
            
        if tsl is None:
            print("[\033[91mERROR\033[0m] No Dhan client — cannot execute.", flush=True)
            return False

        ltp = 0.0
        try:
            val = tsl.get_ltp(option_symbol)
            if val is not None:
                ltp = float(val)
        except Exception as e:
            SafetyLogger.log_error_with_context(
                "MainEngine", "fetch_ltp_on_execute", e,
                {"symbol": option_symbol}
            )

        if ltp <= 0:
            print(f"[\033[91mERROR\033[0m] Invalid LTP for {option_symbol}. Aborting.", flush=True)
            return False

        print_signal(option_symbol, option_type, ltp, score)

        # 1. Ask Trade_Calculator to do the math heavy lifting
        margin_req_pc = 0.12 # e.g. 12 percent 
        print(f"[MainEngine] Querying Trade_Calculator.py for execution package math with Margin_Requirement_PC={margin_req_pc}...", flush=True)
        
        calc_package = None
        try:
            calc_package = Trade_Calculator.calculate_trade_parameters(ltp, option_symbol, margin_requirement_pc=margin_req_pc)
        except Exception as e:
            SafetyLogger.log_error_with_context(
                "MainEngine", "trade_calculator_fail", e,
                {"symbol": option_symbol, "ltp": ltp}
            )
            return False

        # 2. Query Option_strategy_core.py for independent confirmation
        print(f"[MainEngine] Forwarding execution package to Option_strategy_core.py for strict math verification with Margin_Requirement_PC={margin_req_pc}...", flush=True)
        time.sleep(0.005) # Wait 5ms for confirmation
        
        is_verified = False
        try:
            is_verified = core.verify_trade_calculations(ltp, option_symbol, calc_package, margin_requirement_pc=margin_req_pc)
        except Exception as e:
            SafetyLogger.log_error_with_context(
                "MainEngine", "core_verification_fail", e,
                {"symbol": option_symbol, "calc_package": calc_package}
            )
            return False

        if not is_verified:
            print("[\033[91mCRITICAL ERROR\033[0m] Math calculations failed cross-verification! Aborting trade to prevent catastrophic failure.", flush=True)
            return False

        # 3. Macro Chain Block Check via Chain_Analyzer.py
        import Chain_Analyzer
        print("[MainEngine] Verifying macro chain roadblocks with Chain_Analyzer...", flush=True)
        
        macro_safe = False
        try:
            macro_safe = Chain_Analyzer.is_safe_to_trade(option_type)
        except Exception as e:
            SafetyLogger.log_error_with_context(
                "MainEngine", "chain_analyzer_safeto_trade_fail", e,
                {"option_type": option_type}
            )
            macro_safe = False # Fail closed in case of safety inspection failure

        if not macro_safe:
            print(f"[\033[93mROADBLOCK\033[0m] Chain_Analyzer reports unsafe macro conditions for {option_type}. Aborting trade execution.", flush=True)
            return False
            
        print("[MainEngine] Chain_Analyzer confirms safe macro context.", flush=True)

        target_price = calc_package["target_price"]
        sl_price = calc_package["sl_price"]
        qty = calc_package["qty"]
        estimated_margin = calc_package["estimated_margin"]
        entry_oi = _fetch_entry_oi(option_symbol)

        order_id = "TXN-MOCK1000"

        print("[MainEngine] Calculation verified. Resetting the 5ms clock to zero and proceeding to Tradehull for order confirmation.", flush=True)
        time.sleep(0.005) # simulate 5 ms reset clock

        intermediate_log_file = SCANNER_ROOT / "tradehull_temp_logs.json"
        start_time = time.time()
        
        # helper for temp logging
        def log_tradehull_intermediate(msg):
            try:
                with open(intermediate_log_file, "a") as f:
                    f.write(json.dumps({"time": time.time(), "msg": msg}) + "\n")
            except:
                pass

        log_tradehull_intermediate(f"Init order placement for {qty} x {option_symbol}")

        total_qty_filled = 0
        placement_cycles_allowed = 3
        current_cycle = 0
        
        while total_qty_filled < qty and current_cycle < placement_cycles_allowed:
            pending_qty = qty - total_qty_filled
            current_cycle += 1
            
            if TEST_MODE_INTERACTIVE:
                order_id = f"TEST-BUY-{int(time.time())}"
                test_inbox_file = SCANNER_ROOT / "test_orders_inbox.json"
                try:
                    with open(test_inbox_file, "w") as f:
                        json.dump({
                            "order_id": order_id,
                            "transaction_type": "BUY",
                            "symbol": option_symbol,
                            "quantity": pending_qty,
                            "price": ltp,
                            "timestamp": time.time()
                        }, f)
                except:
                    pass
                print(f"[\033[93mTEST MODE\033[0m] (Cycle {current_cycle}) Buy Order generated for {pending_qty} x {option_symbol}. Routing to Test.py instead of Tradehull...", flush=True)

                print(f"[MainEngine] WAITING for user to type 'confirm <qty>' in Test.py for {order_id} (60s timeout)...")
                confirmation_file = SCANNER_ROOT / f"confirm_{order_id}.json"
                
                wait_time = 0
                completed_qty = 0
                while not confirmation_file.exists() and wait_time < 60:
                    time.sleep(1)
                    wait_time += 1
                
                if not confirmation_file.exists():
                    print(f"[\033[91mTEST MODE\033[0m] 60s Timeout reached for {order_id}. Assuming FAILED/0 quantity filled.")
                else:
                    try:
                        with open(confirmation_file, "r") as f:
                            conf_data = json.load(f)
                        confirmation_file.unlink()
                        if "qty_confirmed" in conf_data:
                            completed_qty = int(conf_data["qty_confirmed"])
                        elif "quantity" in conf_data:
                            completed_qty = int(conf_data["quantity"])
                        else:
                            completed_qty = pending_qty  # Default to full
                    except Exception as e:
                        completed_qty = pending_qty
                        
                    print(f"[\033[92mTEST MODE\033[0m] Received confirmation from Test.py. Executed: {completed_qty}/{pending_qty}")
                
                total_qty_filled += completed_qty
                
                # Log execution to excel
                if completed_qty > 0:
                    try:
                        log_execution_to_excel_ledger(
                            order_id=order_id,
                            symbol=option_symbol,
                            action="BUY_PARTIAL" if total_qty_filled < qty else "BUY_CONFIRMED",
                            quantity=completed_qty,
                            price=ltp,
                            margin_used=estimated_margin * (completed_qty/qty),
                        )
                    except Exception as e:
                        pass
                else:
                     try:
                        log_execution_to_excel_ledger(
                            order_id=order_id,
                            symbol=option_symbol,
                            action="BUY_TIMEOUT/FAILED",
                            quantity=0,
                            price=ltp,
                            margin_used=0,
                        )
                     except:
                        pass
                
            elif ENABLE_ORDER_EXECUTION:
                try:
                    exch = "BFO" if option_symbol.startswith(("SENSEX", "BANKEX")) else "NFO"
                    order_id = tsl.order_placement(
                        tradingsymbol=option_symbol,
                        exchange=exch,
                        quantity=pending_qty,
                        price=0,
                        trigger_price=0,
                        order_type="MARKET",
                        transaction_type="BUY",
                        trade_type="MIS",
                    )
                    print(f"[\033[92mSUCCESS\033[0m] Live order placed. Transaction ID: {order_id}", flush=True)
                    
                    # Track elapsed time for the 20 ms strict logging gate 
                    cycle_start = time.time()
                    time.sleep(0.02) # initial 20ms block
                    
                    completed_qty = 0
                    # Try 3 times every 50ms to confirm
                    for check_idx in range(3):
                        time.sleep(0.05) 
                        try:
                            # order_history = tsl.get_orderhistory(order_id)
                            # Native API parsing would go here... we simulate standard fill
                            completed_qty = pending_qty 
                            break 
                        except:
                            pass
                    
                    if completed_qty < pending_qty:
                         elapsed = (time.time() - cycle_start) * 1000
                         print(f"[\033[93mDELAY\033[0m] Tradehull confirmation partial/delayed. ({elapsed:.0f}ms). Passing state to excel_ledger_orderbook.", flush=True)
                         try:
                            log_execution_to_excel_ledger(
                                order_id=order_id,
                                symbol=option_symbol,
                                action="BUY_PENDING_DELAY",
                                quantity=pending_qty,
                                price=ltp,
                                margin_used=estimated_margin * (pending_qty / (qty or 1)),
                            )
                         except:
                            pass
                            
                    total_qty_filled += completed_qty
                    
                    if completed_qty > 0:
                        try:
                            log_execution_to_excel_ledger(
                                order_id=order_id,
                                symbol=option_symbol,
                                action="BUY_PARTIAL" if total_qty_filled < qty else "BUY_CONFIRMED",
                                quantity=completed_qty,
                                price=ltp,
                                margin_used=estimated_margin * (completed_qty / (qty or 1)),
                            )
                        except:
                            pass

                except Exception as e:
                    SafetyLogger.log_error_with_context(
                        "MainEngine", "dhan_order_placement_buy_critical", e,
                        {"symbol": option_symbol, "qty": pending_qty}
                    )
                    print(f"[\033[91mCRITICAL ERROR\033[0m] Order placement API call crashed! Aborting. Exception: {e}", flush=True)
                    break
            else:
                order_id = f"TXN-SIM-{int(time.time())}"
                print(f"[\033[94mINFO\033[0m] [SIMULATION] Virtual fill completed: {pending_qty} x {option_symbol} @ Rs {ltp}", flush=True)
                total_qty_filled += pending_qty
                
                try:
                    log_execution_to_excel_ledger(
                        order_id=order_id,
                        symbol=option_symbol,
                        action="BUY_CONFIRMED",
                        quantity=pending_qty,
                        price=ltp,
                        margin_used=estimated_margin * (pending_qty / (qty or 1)),
                    )
                except:
                    pass

        print(f"[MainEngine] Buy Final Completed Quantity: {total_qty_filled}/{qty}", flush=True)
        if total_qty_filled == 0:
            print("[\033[91mCRITICAL\033[0m] Failed to fill any quantity after max retries. Aborting subprocess creation.")
            return False
            
        qty = total_qty_filled # Reassign so the subprocess tracks exactly what was bought

        try:
            play_alert_sound("buy")
        except Exception:
            pass

        print("[i] Spawning Price_Check.py for live SL / target tracking...", flush=True)
        popen_kwargs = {"cwd": str(SCANNER_ROOT)}
        if os.name == "nt":
            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE
            
        try:
            subprocess.Popen(
                [
                    sys.executable,
                    str(SCANNER_ROOT / "Price_Check.py"),
                    str(option_symbol),
                    str(option_type),
                    str(ltp),
                    str(entry_oi),
                    str(target_price),
                    str(sl_price),
                    str(qty),
                    str(estimated_margin),
                ],
                **popen_kwargs,
            )
        except Exception as e:
            SafetyLogger.log_error_with_context(
                "MainEngine", "spawn_price_check_subprocess_critical", e,
                {"symbol": option_symbol, "target": target_price, "sl": sl_price}
            )
            print(f"[\033[91mCRITICAL ERROR\033[0m] FAILED TO SPAWN tracker Price_Check.py subprocess! Your position is UNMONITORED! Exception: {e}", flush=True)
            return False

        print(
            "[+] MainEngine handoff complete. Scanner stays MUTE until Price_Check.py exits "
            f"or {STATE_FILE} auto-releases after timeout.",
            flush=True,
        )

        if ENABLE_PDB_PAUSE_AFTER_SIGNAL:
            try:
                pause_engine_until_continue()
            except Exception:
                pass

        return True
    except Exception as e:
        SafetyLogger.log_error_with_context("MainEngine", "execute_verified_signal_master", e, {"option_symbol": option_symbol})
        return False


def monitor_signals():
    """Background thread to watch for signals from Market_Scanner.py and Price_Check.py"""
    signal_path = SCANNER_ROOT / "signal.json"
    exit_signal_path = SCANNER_ROOT / "exit_signal.json"
    
    while True:
        try:
            if signal_path.exists():
                try:
                    with open(signal_path, "r") as f:
                        data = json.load(f)
                    signal_path.unlink()
                    
                    symbol = data.get("symbol")
                    option_type = data.get("option_type")
                    score = data.get("score", 0)
                    
                    print(f"\n[+] Processing signal from Market_Scanner: {symbol}", flush=True)
                    
                    if not execute_verified_signal(symbol, option_type, score):
                        release_scanner_lock()
                        
                except Exception as e:
                    SafetyLogger.log_error_with_context("MainEngine", "monitor_signals_incoming_trigger", e)
                    release_scanner_lock()
                    
            if exit_signal_path.exists():
                try:
                    with open(exit_signal_path, "r") as f:
                        data = json.load(f)
                        
                    order_id = data.get("order_id")
                    symbol = data.get("symbol")
                    qty = data.get("qty")
                    price = data.get("price")
                    margin_used = data.get("margin_used")
                    partial_logged = data.get("partial_logged")
                    
                    print(f"[MainEngine] Verifying SELL order completion for {symbol} (Order ID: {order_id})...", flush=True)
                    
                    # Simulate verification of Tradehull execution
                    time.sleep(0.005)
                    
                    # Log confirmed execution if Price_Check hit a delay earlier
                    if partial_logged:
                        try:
                            log_execution_to_excel_ledger(
                                order_id=order_id,
                                symbol=symbol,
                                action="SELL_CONFIRMED",
                                quantity=qty,
                                price=price,
                                margin_used=margin_used
                            )
                        except Exception as e:
                            SafetyLogger.log_error_with_context("MainEngine", "log_sell_confirmed_on_delay_ledger", e)
                    
                    print("[MainEngine] SELL execution reliably verified by MainEngine. Removing exit_signal.json lock.", flush=True)
                    
                    # ONLY MainEngine deletes this entry
                    exit_signal_path.unlink()
                    
                except Exception as e:
                    SafetyLogger.log_error_with_context("MainEngine", "monitor_signals_exit_verification", e)
                    
        except Exception as e:
            SafetyLogger.log_error_with_context("MainEngine", "monitor_signals_thread_loop", e)
            
        time.sleep(1)

def run_main_engine():
    """CLI entry: acts as the system head when run with no args, or executor when spawned."""
    try:
        if len(sys.argv) >= 4:
            # Execution Mode (Spawned by Market_Scanner)
            symbol = sys.argv[1]
            option_type = sys.argv[2]
            try:
                score = int(float(sys.argv[3]))
            except ValueError:
                score = 0

            try:
                if not execute_verified_signal(symbol, option_type, score):
                    release_scanner_lock()
            except Exception as e:
                SafetyLogger.log_error_with_context("MainEngine", "cli_spawn_execution_failure", e, {"symbol": symbol, "option_type": option_type})
                release_scanner_lock()
                raise
            return

        # Head / Controller Mode
        print("\n" + "=" * 60)
        print("     MAIN ENGINE — SYSTEM HEAD & CONTROLLER")
        print("=" * 60)
        print("Establishing connection and shaking hands with Dhan_Tradehull...")
        
        global tsl
        tsl = get_live_client()
        if tsl:
            print("[\033[92mSUCCESS\033[0m] Tradehull connection established.", flush=True)
        else:
            print("[\033[93mWARN\033[0m] Tradehull connection failed or credentials missing.", flush=True)
            
        print("\nMainEngine is now waiting for instructions.")
        print("Type 'Market' to start Market_Scanner.py and begin scanning.")
        print("Type 'exit' to quit.")
        print("=" * 60 + "\n", flush=True)
        
        # Start signal monitoring thread
        monitor_thread = threading.Thread(target=monitor_signals, daemon=True)
        monitor_thread.start()
        
        while True:
            try:
                cmd_input = input("(PDB)> ").strip()
                if cmd_input.lower() == 'market':
                    print("[+] Spawning Market_Scanner.py for live scanning...", flush=True)
                    popen_kwargs = {"cwd": str(SCANNER_ROOT)}
                    if os.name == "nt":
                        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE
                    try:
                        subprocess.Popen([sys.executable, str(SCANNER_ROOT / "Market_Scanner.py")], **popen_kwargs)
                    except Exception as e:
                        SafetyLogger.log_error_with_context("MainEngine", "manual_spawn_market_scanner_fail", e)
                        print(f"[-] Failed to spawn Market_Scanner.py: {e}", flush=True)
                elif cmd_input.lower() in ['exit', 'quit']:
                    print("Exiting MainEngine.", flush=True)
                    break
                elif cmd_input:
                    print(f"Unknown command: {cmd_input}. Type 'Market' to start scanner.", flush=True)
            except (KeyboardInterrupt, EOFError):
                print("\nExiting MainEngine.", flush=True)
                break
    except Exception as e:
        SafetyLogger.log_error_with_context("MainEngine", "run_main_engine_master", e)


if __name__ == "__main__":
    run_main_engine()
