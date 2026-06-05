import sys
import os
import time
import datetime
import subprocess
import json
import uuid
from pathlib import Path
import SafetyLogger
import Trade_Calculator as calc
import Option_strategy_core as core
import Chain_Analyzer
from excel_ledger_orderbook import log_execution_to_excel_ledger
from scanner_excel import play_alert_sound
from System_Config import (
    TEST_MODE_INTERACTIVE, ENABLE_ORDER_EXECUTION,
    ENABLE_PDB_PAUSE_AFTER_SIGNAL, MARGIN_REQUIREMENT_PCT
)

SCANNER_ROOT = Path(__file__).resolve().parent
STATE_FILE = SCANNER_ROOT / "scanner_state.json"

class OMSEngine:
    def __init__(self, broker_client):
        self.tsl = broker_client

    def init(self):
        pass

    def start(self):
        pass

    def stop(self):
        pass

    def health_check(self):
        return self.tsl is not None

    def _fetch_entry_oi(self, option_symbol: str) -> int:
        if self.tsl is None:
            return 0
        try:
            und = "SENSEX" if "SENSEX" in option_symbol else "NIFTY"
            chain = self.tsl.get_option_chain(underlying=und, strike_range=3)
            if chain and "options" in chain:
                for o in chain["options"]:
                    if o.get("symbol") == option_symbol:
                        return int(o.get("oi", 0))
        except Exception as e:
            SafetyLogger.log_error_with_context("OMSEngine", "fetch_entry_oi", e, {"symbol": option_symbol})
        return 0

    def get_ltp(self, option_symbol: str) -> float:
        try:
            val = self.tsl.get_ltp(option_symbol)
            if val is not None:
                return float(val)
        except Exception as e:
            SafetyLogger.log_error_with_context("OMSEngine", "fetch_ltp", e, {"symbol": option_symbol})
        return 0.0

    def print_signal(self, option_symbol, option_type, ltp, score):
        print("\n" + "=" * 60)
        print("🔥 EXECUTION ENGINE — VERIFIED SIGNAL")
        print(f"Instrument : {option_symbol}")
        print(f"Type       : {option_type}")
        print(f"LTP        : Rs {ltp}")
        print(f"Score      : {score}/100")
        print(f"Time       : {datetime.datetime.now().strftime('%H:%M:%S')}")
        print("=" * 60 + "\n", flush=True)

    def execute_verified_signal(self, option_symbol, option_type, score, signal_payload=None):
        if self.tsl is None:
             print("[\033[91mERROR\033[0m] No Dhan client — cannot execute.", flush=True)
             return False

        ltp = self.get_ltp(option_symbol)
        if ltp <= 0:
            return False

        self.print_signal(option_symbol, option_type, ltp, score)
        return self._process_trade_math(option_symbol, option_type, ltp, signal_payload)

    def _process_trade_math(self, option_symbol, option_type, ltp, signal_payload=None):
        import importlib
        importlib.reload(calc)
        importlib.reload(core)
        margin_req_pc = MARGIN_REQUIREMENT_PCT
        try:
             calc_package = calc.calculate_trade_parameters(ltp, option_symbol, margin_requirement_pc=margin_req_pc)
             is_verified = core.verify_trade_calculations(ltp, option_symbol, calc_package, margin_requirement_pc=margin_req_pc)
             if not is_verified:
                 return False
        except Exception as e:
             SafetyLogger.log_error_with_context("OMSEngine", "trade_math_fail", e)
             return False

        try:
             if not Chain_Analyzer.is_safe_to_trade(option_type):
                 return False
        except Exception as e:
             SafetyLogger.log_error_with_context("OMSEngine", "chain_macro_fail", e)
             return False

        return self._execute_and_spawn(option_symbol, option_type, ltp, calc_package, signal_payload)

    def _execute_and_spawn(self, option_symbol, option_type, ltp, calc_package, signal_payload=None):
        target_price = calc_package.target_price
        sl_price = calc_package.sl_price
        qty = calc_package.qty
        estimated_margin = calc_package.estimated_margin
        entry_oi = self._fetch_entry_oi(option_symbol)

        suffix = signal_payload.get("strategy_suffix", "") if signal_payload else ""
        total_filled = self._place_orders(option_symbol, qty, ltp, estimated_margin, suffix=suffix)
        if total_filled == 0:
            return False

        try:
            play_alert_sound("buy")
        except Exception:
            pass

        return self._spawn_price_tracker(option_symbol, option_type, ltp, entry_oi, target_price, sl_price, total_filled, estimated_margin, suffix=suffix)

    def _place_orders(self, option_symbol, qty, ltp, estimated_margin, suffix=""):
        total_qty_filled = 0
        placement_cycles = 3
        current_cycle = 0

        while total_qty_filled < qty and current_cycle < placement_cycles:
            pending = qty - total_qty_filled
            current_cycle += 1
            if TEST_MODE_INTERACTIVE:
                total_qty_filled += self._test_mode_fill(option_symbol, pending, ltp, total_qty_filled, qty, estimated_margin, suffix=suffix)
            elif ENABLE_ORDER_EXECUTION:
                total_qty_filled += self._live_mode_fill(option_symbol, pending, ltp, total_qty_filled, qty, estimated_margin, suffix=suffix)
            else:
                total_qty_filled += self._sim_mode_fill(option_symbol, pending, ltp, total_qty_filled, qty, estimated_margin, suffix=suffix)
        return total_qty_filled

    def _test_mode_fill(self, option_symbol, pending_qty, ltp, total_filled, total_qty, margin, suffix=""):
        order_id = f"TEST-BUY-{uuid.uuid4().hex[:12]}"
        test_inbox_file = SCANNER_ROOT / "test_orders_inbox.json"
        try:
            with open(test_inbox_file, "w") as f:
                json.dump({"order_id": order_id, "transaction_type": "BUY", "symbol": option_symbol, "quantity": pending_qty, "price": ltp, "timestamp": time.time()}, f)
        except Exception as e:
            SafetyLogger.log_error_with_context("OMSEngine", "test_mode_file_write", e)
        
        confirmation_file = SCANNER_ROOT / f"confirm_{order_id}.json"
        completed_qty = self._wait_test_confirmation(confirmation_file, pending_qty)
        self._log_fill(order_id, option_symbol, completed_qty, pending_qty, ltp, total_filled, total_qty, margin, suffix=suffix)
        return completed_qty

    def _wait_test_confirmation(self, confirmation_file, pending_qty):
        wait_time = 0
        while not confirmation_file.exists() and wait_time < 600: # 60 seconds (600 * 0.1)
            time.sleep(0.1)
            wait_time += 1
        if not confirmation_file.exists():
            return 0
        try:
            with open(confirmation_file, "r") as f:
                conf_data = json.load(f)
            confirmation_file.unlink()
            return int(conf_data.get("qty_confirmed", conf_data.get("quantity", pending_qty)))
        except Exception as e:
            SafetyLogger.log_error_with_context("OMSEngine", "test_confirmation_read", e)
            return pending_qty

    def _live_mode_fill(self, option_symbol, pending_qty, ltp, total_filled, total_qty, margin, suffix=""):
        exch = "BFO" if option_symbol.startswith(("SENSEX", "BANKEX")) else "NFO"
        try:
            order_id = self.tsl.order_placement(tradingsymbol=option_symbol, exchange=exch, quantity=pending_qty, price=0, trigger_price=0, order_type="MARKET", transaction_type="BUY", trade_type="MIS")
            completed_qty = pending_qty
            self._log_fill(order_id, option_symbol, completed_qty, pending_qty, ltp, total_filled, total_qty, margin, suffix=suffix)
            return completed_qty
        except Exception as e:
            SafetyLogger.log_error_with_context("OMSEngine", "dhan_order_placement", e)
            return 0

    def _sim_mode_fill(self, option_symbol, pending_qty, ltp, total_filled, total_qty, margin, suffix=""):
        order_id = f"TXN-SIM-{uuid.uuid4().hex[:12]}"
        self._log_fill(order_id, option_symbol, pending_qty, pending_qty, ltp, total_filled, total_qty, margin, suffix=suffix)
        return pending_qty

    def _log_fill(self, order_id, symbol, completed, pending, price, total_filled, total_qty, margin, suffix=""):
        import threading
        display_sym = f"{symbol} {suffix}".strip() if suffix else symbol
        if completed > 0:
            action = "BUY_PARTIAL" if total_filled + completed < total_qty else "BUY_CONFIRMED"
            mpx = margin * (completed / (total_qty or 1))
            try:
                threading.Thread(target=log_execution_to_excel_ledger, kwargs=dict(order_id=order_id, symbol=display_sym, action=action, quantity=completed, price=price, margin_used=mpx), daemon=True).start()
            except Exception as e:
                SafetyLogger.log_error_with_context("OMSEngine", "ledger_log_buy_confirmed", e)
        else:
            try:
                 threading.Thread(target=log_execution_to_excel_ledger, kwargs=dict(order_id=order_id, symbol=display_sym, action="BUY_TIMEOUT/FAILED", quantity=0, price=price, margin_used=0), daemon=True).start()
            except Exception as e:
                SafetyLogger.log_error_with_context("OMSEngine", "ledger_log_buy_failed", e)

    def _spawn_price_tracker(self, option_symbol, option_type, ltp, entry_oi, target_price, sl_price, qty, margin, suffix=""):
        import threading
        import Price_Check
        from models import TradePosition
        try:
            position = TradePosition(
                symbol=option_symbol,
                option_type=option_type,
                qty=qty,
                entry_ltp=ltp,
                target=target_price,
                sl=sl_price,
                initial_sl=sl_price,
                margin_used=margin,
                entry_time=datetime.datetime.now(),
                entry_oi=entry_oi,
                peak_price=ltp,
                strategy_suffix=suffix
            )
            tracker_thread = threading.Thread(target=Price_Check.run_price_tracker, args=(position,), daemon=True)
            tracker_thread.start()
            return True
        except Exception as e:
            SafetyLogger.log_error_with_context("OMSEngine", "spawn_price_tracker", e)
            return False

    def execute_sell(
        self,
        option_symbol: str,
        qty: int,
        current_ltp: float,
        margin_used: float,
    ) -> int:
        """Execute a sell order through TEST/LIVE/SIM modes.

        Returns total_qty_filled.
        """
        import threading
        total_qty_filled: int = 0
        placement_cycles: int = 3
        current_cycle: int = 0

        while total_qty_filled < qty and current_cycle < placement_cycles:
            pending = qty - total_qty_filled
            current_cycle += 1

            if TEST_MODE_INTERACTIVE:
                total_qty_filled += self._test_sell_fill(
                    option_symbol, pending, current_ltp,
                    total_qty_filled, qty, margin_used,
                )
            elif ENABLE_ORDER_EXECUTION:
                total_qty_filled += self._live_sell_fill(
                    option_symbol, pending, current_ltp,
                    total_qty_filled, qty, margin_used,
                )
            else:
                total_qty_filled += self._sim_sell_fill(
                    option_symbol, pending, current_ltp,
                    total_qty_filled, qty, margin_used,
                )
        return total_qty_filled

    # -- Sell: TEST mode -------------------------------------------
    def _test_sell_fill(
        self, symbol: str, pending: int, price: float,
        filled: int, total: int, margin: float,
    ) -> int:
        order_id = f"TEST-SELL-{uuid.uuid4().hex[:12]}"
        inbox = SCANNER_ROOT / "test_orders_inbox.json"
        try:
            with open(inbox, "w") as f:
                json.dump({
                    "order_id": order_id,
                    "transaction_type": "SELL",
                    "symbol": symbol,
                    "quantity": pending,
                    "price": price,
                    "timestamp": time.time(),
                }, f)
        except Exception as e:
            SafetyLogger.log_error_with_context("OMSEngine", "test_sell_file_write", e)

        confirm = SCANNER_ROOT / f"confirm_{order_id}.json"
        completed = self._wait_test_confirmation(confirm, pending)
        self._log_sell_fill(order_id, symbol, completed, pending,
                           price, filled, total, margin)
        return completed

    # -- Sell: LIVE mode -------------------------------------------
    def _live_sell_fill(
        self, symbol: str, pending: int, price: float,
        filled: int, total: int, margin: float,
    ) -> int:
        exch = "BFO" if symbol.startswith(("SENSEX", "BANKEX")) else "NFO"
        try:
            order_id = self.tsl.order_placement(
                tradingsymbol=symbol, exchange=exch,
                quantity=pending, price=0, trigger_price=0,
                order_type="MARKET", transaction_type="SELL",
                trade_type="MIS",
            )
            self._log_sell_fill(order_id, symbol, pending, pending,
                               price, filled, total, margin)
            return pending
        except Exception as e:
            SafetyLogger.log_error_with_context(
                "OMSEngine", "live_sell_placement", e,
                {"symbol": symbol, "qty": pending},
            )
            return 0

    # -- Sell: SIM mode --------------------------------------------
    def _sim_sell_fill(
        self, symbol: str, pending: int, price: float,
        filled: int, total: int, margin: float,
    ) -> int:
        order_id = f"TXN-SIM-{uuid.uuid4().hex[:12]}"
        self._log_sell_fill(order_id, symbol, pending, pending,
                           price, filled, total, margin)
        return pending

    # -- Sell ledger helper ----------------------------------------
    def _log_sell_fill(
        self, order_id: str, symbol: str, completed: int,
        pending: int, price: float, filled: int,
        total: int, margin: float,
    ) -> None:
        import threading
        if completed > 0:
            action = "SELL_PARTIAL" if filled + completed < total else "SELL_CONFIRMED"
            mpx = margin * (completed / (total or 1))
            try:
                threading.Thread(
                    target=log_execution_to_excel_ledger,
                    kwargs=dict(order_id=order_id, symbol=symbol,
                                action=action, quantity=completed,
                                price=price, margin_used=mpx),
                    daemon=True,
                ).start()
            except Exception as e:
                SafetyLogger.log_error_with_context(
                    "OMSEngine", "ledger_log_sell_confirmed", e)
        else:
            try:
                threading.Thread(
                    target=log_execution_to_excel_ledger,
                    kwargs=dict(order_id=order_id, symbol=symbol,
                                action="SELL_TIMEOUT/FAILED",
                                quantity=0, price=price,
                                margin_used=0),
                    daemon=True,
                ).start()
            except Exception as e:
                SafetyLogger.log_error_with_context(
                    "OMSEngine", "ledger_log_sell_failed", e)
