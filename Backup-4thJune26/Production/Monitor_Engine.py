"""
Monitor_Engine.py — Position hypercare monitoring module.

Tracks open positions and decides HOLD / TRAIL / EXIT based on:
- Target hit
- Stop-loss hit
- Trailing stop logic (40% of profit trailed)
- Supertrend reversal
- OI unwinding (>15% drop from entry)
- Time-based exit (>45 min with <5 pts profit)
"""
import time
import datetime
import pandas as pd
import SafetyLogger
from System_Config import TARGET_POINTS, INITIAL_SL_POINTS
from models import TradePosition


# ── Lifecycle hooks ──────────────────────────────────────
def init():
    pass


def start():
    pass


def stop():
    pass


def health_check() -> bool:
    return True


# ── Constants ────────────────────────────────────────────
_TRAIL_START_PCT: float = 0.30   # Start trailing after 30% of target move
_TRAIL_LOCK_PCT: float = 0.60   # Lock in 60% of profit as trailing SL
_OI_UNWIND_PCT: float = 0.15    # Exit if OI drops >15% from entry
_STALE_HOLD_MIN: int = 12       # Minutes before time-based exit check
_STALE_HOLD_PTS: float = 0.0    # Min profit required to hold past time limit


# ── Exit checks (each ≤30 LOC) ──────────────────────────

def _check_target_hit(
    current_ltp: float, target: float, sl: float
) -> tuple:
    """Bypassed to allow infinite trend-riding via trailing stop-loss."""
    return None


def _check_stop_loss(
    position: 'TradePosition', df_1m: pd.DataFrame, current_ltp: float
) -> tuple:
    """Returns EXIT if Nifty spot hits the 20-point stop loss or premium hits trailed SL."""
    # 1. Spot-based SL Check (20 Nifty points)
    spot_sl = getattr(position, "spot_sl", 0.0)
    if spot_sl > 0.0 and df_1m is not None and not df_1m.empty:
        latest_row = df_1m.iloc[-1]
        current_spot_low = float(latest_row.get("low", latest_row["close"]))
        current_spot_high = float(latest_row.get("high", latest_row["close"]))
        
        if position.option_type == "CE" and current_spot_low <= spot_sl:
            return ("EXIT", "stop_loss_hit", position.sl)
        elif position.option_type == "PE" and current_spot_high >= spot_sl:
            return ("EXIT", "stop_loss_hit", position.sl)

    # 2. Premium-based SL Check
    if current_ltp <= position.sl:
        return ("EXIT", "stop_loss_hit", position.sl)
    return None


def _check_trailing_stop(
    position: 'TradePosition', current_ltp: float, current_time: datetime.datetime = None
) -> tuple:
    """Implements Phase-based Trailing SL."""
    peak: float = max(position.peak_price, current_ltp)
    position.peak_price = peak

    entry_time = getattr(position, "entry_time", None)
    if entry_time is None or current_time is None:
        return None

    elapsed_min = (pd.to_datetime(current_time) - pd.to_datetime(entry_time)).total_seconds() / 60.0

    if elapsed_min < 2.0:
        return None  # Phase 1 absolute priority (no trailing)

    # Phase 2: After 2 minutes, SL is at least Entry + 0.50, and trails peak by 15.0
    phase1_sl = round(position.entry_ltp + 0.50, 2)
    dynamic_sl = round(peak - 15.0, 2)
    
    new_sl = max(phase1_sl, dynamic_sl)
    
    # If the new SL is above the current price, the stop is hit immediately
    if current_ltp <= new_sl:
        reason = "2_min_cold_protection_failed" if new_sl == phase1_sl else "dynamic_trail_hit"
        print(f"[{current_time}] EXIT: {reason} at LTP {current_ltp} (SL was {new_sl})", flush=True)
        return ("EXIT", reason, new_sl)
    
    if new_sl > position.sl:
        if new_sl == phase1_sl and position.sl < phase1_sl:
            print(f"[{current_time}] 2-Minute Cold Protection ENDS. SL moved to Entry + 0.50 -> {new_sl}", flush=True)
            return ("TRAIL", "2_min_cold_protection_end", new_sl)
        else:
            print(f"[{current_time}] Phase 2 Dynamic Trail: LTP Peak {peak}, SL trailing 15 pts behind -> {new_sl}", flush=True)
            return ("TRAIL", "15_pt_dynamic_trail", new_sl)

    return None


def _check_supertrend_reversal(
    df_1m: pd.DataFrame, option_type: str
) -> tuple:
    """Exit if supertrend flips against position direction."""
    if df_1m is None or df_1m.empty or len(df_1m) < 2:
        return None

    if "st_color" not in df_1m.columns:
        return None

    st_color: str = str(df_1m.iloc[-2]["st_color"]).upper()

    if option_type == "CE" and st_color == "RED":
        return ("EXIT", "supertrend_reversal_to_red", 0.0)
    if option_type == "PE" and st_color == "GREEN":
        return ("EXIT", "supertrend_reversal_to_green", 0.0)
    return None


def _check_oi_unwinding(
    entry_oi: int, opt_row: dict
) -> tuple:
    """Exit if open interest drops more than _OI_UNWIND_PCT from entry."""
    if entry_oi <= 0 or opt_row is None:
        return None

    current_oi: int = int(opt_row.get("oi", entry_oi))
    if current_oi <= 0:
        return None

    drop_pct: float = (entry_oi - current_oi) / entry_oi
    if drop_pct >= _OI_UNWIND_PCT:
        pct_display = round(drop_pct * 100, 1)
        return ("EXIT", f"oi_unwinding_{pct_display}pct", 0.0)
    return None

def _check_stale_hold(
    position: 'TradePosition', current_time: datetime.datetime, current_ltp: float
) -> tuple:
    """Exit if the trade has been held for > _STALE_HOLD_MIN (12 mins) and is not in profit."""
    entry_time = getattr(position, "entry_time", None)
    if entry_time is None or current_time is None:
        return None

    elapsed_min = (pd.to_datetime(current_time) - pd.to_datetime(entry_time)).total_seconds() / 60.0
    if elapsed_min >= _STALE_HOLD_MIN:
        if current_ltp <= (position.entry_ltp + _STALE_HOLD_PTS):
            return ("EXIT", f"stale_trade_{_STALE_HOLD_MIN}m_loss", 0.0)
    return None


def _check_time_decay(
    position: 'TradePosition', current_ltp: float, current_time: datetime.datetime = None
) -> tuple:
    """12-minute momentum time cutoff: exits if elapsed time is exactly 12 minutes and profit < 5.0 points."""
    entry_time = getattr(position, "entry_time", None)
    if entry_time is None or current_time is None:
        return None

    elapsed_min: float = (pd.to_datetime(current_time) - pd.to_datetime(entry_time)).total_seconds() / 60.0
    # At exactly 12 minutes (using a small margin of error for candle intervals)
    if 11.5 <= elapsed_min <= 12.5:
        profit: float = current_ltp - position.entry_ltp
        if profit < 5.0:
            return ("EXIT", "time_cutoff_12m", 0.0)
    return None


# ── Main orchestrator ────────────────────────────────────

def execute_hypercare_monitoring(
    position: 'TradePosition',
    df_1m: pd.DataFrame,
    opt_row: dict,
    current_ltp: float,
) -> tuple:
    """Core position monitor called by Price_Check.py every tick.

    Returns:
        (action, reason, updated_sl) where action ∈ {HOLD, TRAIL, EXIT}
    """
    try:
        sl: float = position.sl
        target: float = position.target
        option_type: str = position.option_type
        entry_oi: int = int(position.entry_oi)

        # Priority order: target > SL > trailing > reversal > OI > time
        result = _check_target_hit(current_ltp, target, sl)
        if result:
            return result

        result = _check_stop_loss(position, df_1m, current_ltp)
        if result:
            return result

        current_time = df_1m.iloc[-1]["start_Time"] if not df_1m.empty and "start_Time" in df_1m.columns else None

        result = _check_trailing_stop(position, current_ltp, current_time)
        if result:
            return result

        result = _check_supertrend_reversal(df_1m, option_type)
        if result:
            return result

        result = _check_oi_unwinding(entry_oi, opt_row)
        if result:
            return result
        
        result = _check_stale_hold(position, current_time, current_ltp)
        if result:
            return result

        result = _check_time_decay(position, current_ltp, current_time)
        if result:
            return result

        return ("HOLD", "no_exit_condition_met", sl)

    except Exception as e:
        SafetyLogger.log_error_with_context(
            "Monitor_Engine", "execute_hypercare_monitoring", e,
            {"symbol": getattr(position, "symbol", "Unknown"), "ltp": current_ltp}
        )
        return ("HOLD", f"monitor_error_{e}", position.sl)
