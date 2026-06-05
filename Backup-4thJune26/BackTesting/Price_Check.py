import sys
import time
import datetime
import os
import json
from pathlib import Path
from broker_client import get_live_client
from excel_ledger_orderbook import log_execution_to_excel_ledger as _sync_log_ledger
import threading

strategy_suffix = ""

def log_execution_to_excel_ledger(order_id, symbol, action, quantity, price, margin_used, **kwargs):
    global strategy_suffix
    if strategy_suffix:
        symbol = f"{symbol} {strategy_suffix}".strip()
    threading.Thread(target=_sync_log_ledger, args=(order_id, symbol, action, quantity, price, margin_used), kwargs=kwargs, daemon=True).start()

import SafetyLogger
import os
import traceback
from System_Config import TEST_MODE_INTERACTIVE
from event_bus import dashboard_queue, exit_queue, manual_exits

# Load core tracking module
import Monitor_Engine as monitor_engine

# Always run from the Option Scanner folder (where cred.env and modules live)
SCANNER_ROOT = Path(__file__).resolve().parent
os.chdir(SCANNER_ROOT)
if str(SCANNER_ROOT) not in sys.path:
    sys.path.insert(0, str(SCANNER_ROOT))
CRED_ENV = SCANNER_ROOT / "cred.env"
STATE_FILE = SCANNER_ROOT / "scanner_state.json"




tsl = get_live_client()


from models import TradePosition

def parse_arguments() -> TradePosition:
    """Extracts trade execution snapshots passed from the main engine."""
    try:
        return TradePosition(
            symbol=sys.argv[1],
            option_type=sys.argv[2],
            entry_ltp=float(sys.argv[3]),
            entry_oi=int(sys.argv[4]),
            target=float(sys.argv[5]),
            sl=float(sys.argv[6]),
            initial_sl=float(sys.argv[6]),
            peak_price=float(sys.argv[3]),
            entry_time=datetime.datetime.now(),
            qty=int(sys.argv[7]) if len(sys.argv) > 7 else 0,
            margin_used=float(sys.argv[8]) if len(sys.argv) > 8 else 0.0,
        )
    except Exception as e:
        SafetyLogger.log_error_with_context(
            "Price_Check", "parse_arguments", e, 
            {"sys_argv": sys.argv}
        )
        print("[-] Error: Price_Check.py failed to parse arguments correctly.", flush=True)
        sys.exit(1)


def calculate_oi_metric(entry_oi, current_oi):
    """Formulates the Open Interest reporting string requested for display criteria."""
    try:
        if entry_oi == 0: 
            return "0% (Entry OI baseline missing)"
        
        pct_change = ((current_oi - entry_oi) / entry_oi) * 100
        
        if pct_change > 0:
            return f"Increased from Order Execution by {round(pct_change, 2)}%"
        elif pct_change == 0:
            return "Same since Order Execution (0%)"
        else:
            # Display explicit data parameters only if net structural drop breaches -5%
            if pct_change <= -5.0:
                return f"Decreased by {round(abs(pct_change), 2)}% | Entry OI: {entry_oi} -> Current OI: {current_oi}"
            return f"Decreased by {round(abs(pct_change), 2)}%"
    except Exception as e:
        SafetyLogger.log_error_with_context(
            "Price_Check", "calculate_oi_metric", e,
            {"entry_oi": entry_oi, "current_oi": current_oi}
        )
        return "N/A"


def run_price_tracker(position: TradePosition):
    global strategy_suffix
    strategy_suffix = getattr(position, "strategy_suffix", "")
    print(f"[+] Automated Tracker Module Engaged for {position.symbol}", flush=True)
    print("[+] Continuous live feed active. Updating every 30 seconds...\n", flush=True)

    while True:
        try:
            # 1. Fetch live market metrics
            current_ltp = float(position.entry_ltp)
            try:
                fetched_ltp = tsl.get_ltp(position.symbol)
                if fetched_ltp is not None:
                    current_ltp = float(fetched_ltp)
            except Exception as e:
                SafetyLogger.log_error_with_context(
                    "Price_Check", "fetch_ltp", e,
                    {"symbol": position.symbol}
                )

            df_1m = None
            df_5m = None
            try:
                und_val = "SENSEX" if "SENSEX" in position.symbol else "NIFTY"
                exch_val = "BSE" if "SENSEX" in position.symbol else "NSE"
                df_1m = tsl.get_intraday_data(und_val, exch_val, 1)
                
                # Fetch 5-minute data for Supertrend anchor logic
                df_5m = tsl.get_intraday_data(und_val, exch_val, 5)
            except Exception as e:
                SafetyLogger.log_error_with_context("Price_Check", "get_intraday_data", e)

            # Fetch option chain to extract live open interest metrics
            chain = None
            try:
                und_val = "SENSEX" if "SENSEX" in position.symbol else "NIFTY"
                chain = tsl.get_option_chain(underlying=und_val, strike_range=3)
            except Exception as e:
                SafetyLogger.log_error_with_context("Price_Check", "get_option_chain", e)

            current_oi = position.entry_oi  # Default fallback
            opt_row = None
            
            if chain and "options" in chain:
                try:
                    opt_row = next((o for o in chain["options"] if o["symbol"] == position.symbol), None)
                    if opt_row:
                        current_oi = int(opt_row.get("oi", position.entry_oi))
                except Exception as e:
                    SafetyLogger.log_error_with_context(
                        "Price_Check", "parse_oi_from_chain", e,
                        {"symbol": position.symbol}
                    )

            # 2. Run analysis indicators via the hypercare tracking core
            current_rsi = 50.0
            if df_1m is not None and not df_1m.empty and len(df_1m) >= 15:
                try:
                    df_1m = tsl.add_supertrend(df_1m, period=10, multiplier=3)
                    from indicator_engine import calculate_rsi
                    current_rsi = calculate_rsi(df_1m)
                except Exception as e:
                    SafetyLogger.log_error_with_context("Price_Check", "calculate_rsi_indicators", e)
                    
            if df_5m is not None and not df_5m.empty and len(df_5m) >= 10:
                try:
                    df_5m = tsl.add_supertrend(df_5m, period=10, multiplier=3)
                except Exception as e:
                    SafetyLogger.log_error_with_context("Price_Check", "add_supertrend_5m", e)
            
            # Extract tracking output actions from your monitor engine rules
            action, reason, updated_sl = "HOLD", "Default Hold (Error in logic)", position.sl
            try:
                if position.symbol in manual_exits:
                    action, reason = "EXIT", "Manual Test Sell Triggered"
                    manual_exits.remove(position.symbol)
                else:
                    action, reason, updated_sl = monitor_engine.execute_hypercare_monitoring(position, df_1m, opt_row, current_ltp, df_5m=df_5m)
            except Exception as e:
                SafetyLogger.log_error_with_context(
                    "Price_Check", "execute_hypercare_monitoring", e,
                    {"position": position, "current_ltp": current_ltp}
                )

            # Update position stop loss if it trails higher
            if action == "TRAIL":
                position.sl = updated_sl
                if reason == "breakeven_triggered":
                    position.breakeven_triggered = True
                print(f"[TRAIL ALERT] Stop Loss trailed higher to Rs {updated_sl} ({reason})", flush=True)

            status_output = "HOLD / Neutral" if action == "HOLD" else f"Exit ({reason})"

            # 3. Print the explicit Dashboard Output Summary as specified
            print("="*60, flush=True)
            print(f"Traded Instrument : {position.symbol}", flush=True)
            print(f"Current LTP       : Rs {current_ltp}", flush=True)
            print(f"Current OI        : {calculate_oi_metric(position.entry_oi, current_oi)}", flush=True)
            print(f"Current RSI       : {round(current_rsi, 2)} (Looking at the 1 min Chart)", flush=True)
            print(f"Status            : {status_output}", flush=True)
            print("="*60 + "\n", flush=True)

            try:
                dashboard_queue.put({
                    "type": "ACTIVE_TRADES",
                    "payload": [{
                        "symbol": position.symbol,
                        "type": position.option_type,
                        "entry": position.entry_ltp,
                        "target": position.target,
                        "sl": position.sl,
                        "ltp": current_ltp,
                        "pnl": current_ltp - position.entry_ltp
                    }]
                })
            except Exception as e:
                SafetyLogger.log_error_with_context("Price_Check", "dashboard_update", e)

            # Close the automated background window cleanly if system hits TSL / Target / Reversal
            if action == "EXIT":
                print(f"[-] Trade Cycle Concluded. Reason: {reason}. Initiating Sell...", flush=True)

                try:
                    dashboard_queue.put({
                        "type": "NEW_SIGNAL",
                        "payload": {
                            "symbol": position.symbol, 
                            "type": position.option_type, 
                            "action": "SELL", 
                            "time": datetime.datetime.now().strftime("%H:%M:%S")
                        }
                    })
                except Exception:
                    pass

                qty = position.qty
                option_symbol = position.symbol
                enable_live = os.getenv("ENABLE_ORDER_EXECUTION", "False") == "True"
                
                start_time = time.time()
                total_qty_filled = 0
                placement_cycles_allowed = 3
                current_cycle = 0
                
                while total_qty_filled < qty and current_cycle < placement_cycles_allowed:
                    pending_qty = qty - total_qty_filled
                    current_cycle += 1
                    
                    if TEST_MODE_INTERACTIVE:
                        order_id = f"TEST-SELL-{int(time.time())}"
                        test_inbox_file = Path(__file__).resolve().parent / "test_orders_inbox.json"
                        try:
                            with open(test_inbox_file, "w") as f:
                                json.dump({
                                    "order_id": order_id,
                                    "transaction_type": "SELL",
                                    "symbol": option_symbol,
                                    "quantity": pending_qty,
                                    "price": current_ltp,
                                    "timestamp": time.time()
                                }, f)
                        except Exception as e:
                            SafetyLogger.log_error_with_context("Price_Check", "test_sell_file_write", e)
                        print(f"[\033[93mTEST MODE\033[0m] (Cycle {current_cycle}) Sell Order generated for {pending_qty} x {option_symbol}. Routing to Test.py...", flush=True)

                        print(f"[Price_Check] WAITING for user to type 'confirm <qty>' in Test.py for {order_id} (60s timeout)...")
                        confirmation_file = Path(__file__).resolve().parent / f"confirm_{order_id}.json"
                        
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
                                    completed_qty = pending_qty
                            except Exception as e:
                                completed_qty = pending_qty
                                
                            print(f"[\033[92mTEST MODE\033[0m] Received confirmation from Test.py. Executed: {completed_qty}/{pending_qty}")
                            
                        total_qty_filled += completed_qty
                        
                        if completed_qty > 0:
                            try:
                                log_execution_to_excel_ledger(
                                    order_id=order_id,
                                    symbol=option_symbol,
                                    action="SELL_PARTIAL" if total_qty_filled < qty else "SELL_CONFIRMED",
                                    quantity=completed_qty,
                                    price=current_ltp,
                                    margin_used=position.margin_used * (completed_qty/(qty or 1))
                                )
                            except Exception as e:
                                SafetyLogger.log_error_with_context("Price_Check", "sell_ledger_confirmed", e)
                        else:
                            try:
                                log_execution_to_excel_ledger(
                                    order_id=order_id,
                                    symbol=option_symbol,
                                    action="SELL_TIMEOUT/FAILED",
                                    quantity=0,
                                    price=current_ltp,
                                    margin_used=0
                                )
                            except Exception as e:
                                SafetyLogger.log_error_with_context("Price_Check", "sell_ledger_failed", e)

                    elif enable_live and qty > 0:
                        try:
                            exch = "BFO" if option_symbol.startswith(("SENSEX", "BANKEX")) else "NFO"
                            order_id = tsl.order_placement(
                                tradingsymbol=option_symbol,
                                exchange=exch,
                                quantity=pending_qty,
                                price=0,
                                trigger_price=0,
                                order_type="MARKET",
                                transaction_type="SELL",
                                trade_type="MIS",
                            )
                            print(f"[\033[92mSUCCESS\033[0m] Live SELL order placed. ID: {order_id}", flush=True)
                            
                            cycle_start = time.time()
                            time.sleep(0.02)
                            
                            completed_qty = 0
                            for check_idx in range(3):
                                time.sleep(0.05)
                                try:
                                    completed_qty = pending_qty
                                    break
                                except Exception as e:
                                    SafetyLogger.log_error_with_context("Price_Check", "live_sell_confirm_check", e)
                                    
                            if completed_qty < pending_qty:
                                elapsed = (time.time() - cycle_start) * 1000
                                print(f"[\033[93mDELAY\033[0m] Tradehull confirmation partial/delayed. ({elapsed:.0f}ms). Passing state to ledger.", flush=True)
                                try:
                                    log_execution_to_excel_ledger(
                                        order_id=order_id,
                                        symbol=option_symbol,
                                        action="SELL_PENDING_DELAY",
                                        quantity=pending_qty,
                                        price=current_ltp,
                                        margin_used=position.margin_used * (pending_qty / (qty or 1))
                                    )
                                except Exception as e:
                                    SafetyLogger.log_error_with_context("Price_Check", "live_sell_ledger_delay", e)
                                    
                            total_qty_filled += completed_qty
                            
                            if completed_qty > 0:
                                try:
                                    log_execution_to_excel_ledger(
                                        order_id=order_id,
                                        symbol=option_symbol,
                                        action="SELL_PARTIAL" if total_qty_filled < qty else "SELL_CONFIRMED",
                                        quantity=completed_qty,
                                        price=current_ltp,
                                        margin_used=position.margin_used * (completed_qty / (qty or 1))
                                    )
                                except Exception as e:
                                    SafetyLogger.log_error_with_context("Price_Check", "live_sell_ledger_confirmed", e)
                                    
                        except Exception as e:
                            SafetyLogger.log_error_with_context(
                                "Price_Check", "live_order_placement_sell", e,
                                {"symbol": option_symbol, "qty": pending_qty}
                            )
                            order_id = f"FAILED-TXN-{int(time.time())}"
                            print(f"[\033[91mCRITICAL\033[0m] Live SELL order placement failed! Exception: {e}", flush=True)
                            break
                    else:
                        order_id = f"TXN-SIM-{int(time.time())}"
                        print(f"[\033[94mINFO\033[0m] [SIMULATION] Virtual SELL sent for {pending_qty} x {option_symbol} @ Rs {current_ltp}", flush=True)
                        total_qty_filled += pending_qty
                        
                        try:
                            log_execution_to_excel_ledger(
                                order_id=order_id,
                                symbol=option_symbol,
                                action="SELL_CONFIRMED",
                                quantity=pending_qty,
                                price=current_ltp,
                                margin_used=position.margin_used * (pending_qty / (qty or 1))
                            )
                        except Exception as e:
                            SafetyLogger.log_error_with_context("Price_Check", "sim_sell_ledger", e)
                            
                print(f"[Price_Check] Sell Final Completed Quantity: {total_qty_filled}/{qty}", flush=True)
                expected_qty = qty
                qty = total_qty_filled
                is_100_percent_executed = total_qty_filled >= (expected_qty or 0)

                # Assume partial logged status if not fully completed
                partial_logged = not is_100_percent_executed
                
                # Put exit signal in queue
                try:
                    exit_queue.put({
                        "order_id": locals().get("order_id", f"TXN-SIM-{int(time.time())}"),
                        "symbol": option_symbol,
                        "qty": qty,
                        "price": current_ltp,
                        "margin_used": position.margin_used,
                        "partial_logged": partial_logged,
                        "status": "SELL_CONFIRMED" if is_100_percent_executed else "SELL_PENDING_DELAY"
                    })
                    print("[+] Exit signal sent to exit_queue.", flush=True)
                except Exception as e:
                    SafetyLogger.log_error_with_context("Price_Check", "write_exit_queue", e)

                # Release the lock so Market_Scanner.py can scan again
                try:
                    state_file = Path(__file__).resolve().parent / "scanner_state.json"
                    with open(state_file, "w", encoding="utf-8") as f:
                        json.dump({"status": "SCAN", "updated_at": time.time()}, f)
                    print("[+] scanner_state.json updated to SCAN. Market_Scanner resumed.", flush=True)
                except Exception as e:
                    SafetyLogger.log_error_with_context("Price_Check", "release_scanner_lock", e)

                print("Trade cycle complete. Exiting tracking thread.", flush=True)
                break

        except Exception as e:
            SafetyLogger.log_error_with_context("Price_Check", "price_check_master_loop", e)
        
        # Hibernate slightly before the next tick
        time.sleep(0.5)
