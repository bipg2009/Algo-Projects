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
import numpy as np
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
    """Returns EXIT if the option premium hits the active Stop Loss."""
    if current_ltp <= position.sl:
        return ("EXIT", "stop_loss_hit", position.sl)
    return None


def _check_trailing_stop(
    position: 'TradePosition', current_ltp: float
) -> tuple:
    """Implements continuous 15-point trailing SL with a 100-point jump lock."""
    peak: float = max(position.peak_price, current_ltp)
    position.peak_price = peak

    # Continuous 15-point trailing
    new_sl = round(peak - 15.0, 2)
    reason = "continuous_trailing"

    # Aggressive 5-point tightening lock after a 100-point massive runner
    if peak >= (position.entry_ltp + 100.0):
        new_sl = round(peak - 5.0, 2)
        reason = "massive_runner_lock"

    if new_sl > position.sl:
        return ("TRAIL", reason, new_sl)

    return None


def _check_supertrend_reversal(
    df_1m: pd.DataFrame, option_type: str, current_ltp: float, position: 'TradePosition', is_backtest: bool, df_5m: pd.DataFrame = None
) -> tuple:
    """Exit if 5m supertrend flips against position OR if 3 consecutive 1m HA candles form against position."""
    if df_1m is None or df_1m.empty or len(df_1m) < 4:
        return None

    # Step 1: Check 5m Supertrend Anchor
    if df_5m is not None and not df_5m.empty and "st_color" in df_5m.columns:
        st_5m = str(df_5m.iloc[-1]["st_color"]).upper()
        # If 5m Supertrend matches trade direction, we HOLD and ignore 1m noise
        if (option_type == "CE" and st_5m == "GREEN") or (option_type == "PE" and st_5m == "RED"):
            return None

    if "st_color" not in df_1m.columns:
        return None

    # Step 2: 1m HA Candle Reversal Logic (Runs if 5m Supertrend does NOT support trade)
    def is_candle_against_ha(index):
        try:
            # We need to calculate HA open/close up to the requested index
            # To do this safely and quickly, we extract the slice up to the index
            # Note: index is negative (e.g., -4, -3, -2, -1)
            idx_pos = len(df_1m) + index
            if idx_pos < 1:
                return False
                
            opens = df_1m['open'].values
            closes = df_1m['close'].values
            highs = df_1m['high'].values
            lows = df_1m['low'].values
            
            ha_close = (opens + highs + lows + closes) / 4.0
            ha_open = np.zeros(len(df_1m))
            ha_open[0] = (opens[0] + closes[0]) / 2.0
            
            for i in range(1, idx_pos + 1):
                ha_open[i] = (ha_open[i-1] + ha_close[i-1]) / 2.0
                
            c_open = ha_open[idx_pos]
            c_close = ha_close[idx_pos]
            
            if option_type == "CE":
                return c_close < c_open # HA Red
            else:
                return c_close > c_open # HA Green
        except Exception:
            return False

    c1 = is_candle_against_ha(-3)  # user's iloc[-2] (from previous minute)
    c2 = is_candle_against_ha(-2)  # user's iloc[-1] (from previous minute)
    c3 = is_candle_against_ha(-1)  # user's next candle forming
    
    # EXIT Trade if all 3 are the same
    if c1 and c2 and c3:
        return ("EXIT", "supertrend_reversal_3_candles", 0.0)
        
    current_forming = is_candle_against_ha(-1)
    last_closed = is_candle_against_ha(-2)
    
    current_sec = datetime.datetime.now().second
    if last_closed and current_forming and (is_backtest or current_sec >= 35):
        new_sl = round(current_ltp - 5.0, 2)
        if new_sl > position.sl:
            return ("TRAIL", "supertrend_reversal_warning", new_sl)
            
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

def _check_volume_validation(
    position: 'TradePosition', opt_row: dict, current_time: datetime.datetime
) -> tuple:
    """TEST ENV OVERRIDE: Exit if the discrete volume drops <= volume EMA, checked every 5 mins."""
    import indicator_engine as Indicators
    entry_time = getattr(position, "entry_time", None)
    if entry_time is None or current_time is None or opt_row is None:
        return None

    elapsed_min = (pd.to_datetime(current_time) - pd.to_datetime(entry_time)).total_seconds() / 60.0
    if int(elapsed_min) > 0 and int(elapsed_min) % 5 == 0:
        history = Indicators.CONTRACT_VOLUME_HISTORY.get(position.symbol)
        if history and history["ema_history"]:
            v_ema = history["ema_history"][-1]
            prev_cum = history["last_cumulative"]
            cum_vol = opt_row.get("volume", 0)
            discrete_v = max(0, cum_vol - prev_cum)
            if discrete_v <= v_ema:
                return ("EXIT", "volume_ema_failed_5m_check", 0.0)
    return None

def _check_time_decay_cascade(
    position: 'TradePosition', df_1m: pd.DataFrame, df_5m: pd.DataFrame, current_ltp: float, current_time: datetime.datetime = None, option_type: str = "CE", is_backtest: bool = False
) -> tuple:
    """Time decay cascade: Checks every 6 mins. If momentum is weak and 5m Supertrend fails, trailing SL is pulled tight when 1m HA reverses."""
    entry_time = getattr(position, "entry_time", None)
    if entry_time is None or current_time is None:
        return None

    elapsed_min: float = (pd.to_datetime(current_time) - pd.to_datetime(entry_time)).total_seconds() / 60.0
    
    for multiplier in range(1, 40):  # Covers up to 240 minutes
        target_minutes = multiplier * 6
        if (target_minutes - 0.5) <= elapsed_min <= (target_minutes + 0.5):
            required_profit = multiplier * 2.5
            if current_ltp < (position.entry_ltp + required_profit):
                # Momentum is weak. Check 5m Supertrend protection.
                if df_5m is not None and not df_5m.empty and "st_color" in df_5m.columns:
                    st_5m = str(df_5m.iloc[-1]["st_color"]).upper()
                    if (option_type == "CE" and st_5m == "GREEN") or (option_type == "PE" and st_5m == "RED"):
                        return None # Protected by Supertrend
                
                # Supertrend is opposite (or missing). Check 1m HA candles.
                if df_1m is not None and not df_1m.empty and len(df_1m) >= 3:
                    def is_ha_against(idx):
                        try:
                            idx_pos = len(df_1m) + idx
                            if idx_pos < 1: return False
                            opens, closes = df_1m['open'].values, df_1m['close'].values
                            highs, lows = df_1m['high'].values, df_1m['low'].values
                            ha_close = (opens + highs + lows + closes) / 4.0
                            ha_open = np.zeros(len(df_1m))
                            ha_open[0] = (opens[0] + closes[0]) / 2.0
                            for i in range(1, idx_pos + 1):
                                ha_open[i] = (ha_open[i-1] + ha_close[i-1]) / 2.0
                            c_open, c_close = ha_open[idx_pos], ha_close[idx_pos]
                            return (c_close < c_open) if option_type == "CE" else (c_close > c_open)
                        except Exception:
                            return False

                    c_prev = is_ha_against(-2) # Completed
                    c_curr = is_ha_against(-1) # Forming
                    
                    current_sec = datetime.datetime.now().second
                    is_65_pct_formed = is_backtest or current_sec >= 35
                    
                    if c_prev and c_curr and is_65_pct_formed:
                        new_sl = round(current_ltp - 5.0, 2)
                        if new_sl > position.sl:
                            return ("TRAIL", f"{target_minutes}m_momentum_st_cascade", new_sl)
    return None


# ── Main orchestrator ────────────────────────────────────

def execute_hypercare_monitoring(
    position: 'TradePosition',
    df_1m: pd.DataFrame,
    opt_row: dict,
    current_ltp: float,
    is_backtest: bool = False,
    df_5m: pd.DataFrame = None
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

        result = _check_trailing_stop(position, current_ltp)
        if result:
            return result

        result = _check_supertrend_reversal(df_1m, option_type, current_ltp, position, is_backtest, df_5m)
        if result:
            return result

        result = _check_oi_unwinding(entry_oi, opt_row)
        if result:
            return result

        current_time = df_1m.iloc[-1]["start_Time"] if not df_1m.empty and "start_Time" in df_1m.columns else None
        
        result = _check_stale_hold(position, current_time, current_ltp)
        if result:
            return result
            
        result = _check_volume_validation(position, opt_row, current_time)
        if result:
            return result

        result = _check_time_decay_cascade(position, df_1m, df_5m, current_ltp, current_time, option_type, is_backtest)
        if result:
            return result

        # Rule 4: RSI Exhaustion check (3 fully closed candles)
        if not df_1m.empty and len(df_1m) >= 4 and "RSI_14" in df_1m.columns:
            rsi_3 = df_1m.iloc[-4]["RSI_14"]
            rsi_2 = df_1m.iloc[-3]["RSI_14"]
            rsi_1 = df_1m.iloc[-2]["RSI_14"]
            
            if option_type == "CE":
                # Decreasing for CE
                if rsi_1 < rsi_2 < rsi_3:
                    return ("EXIT", "rsi_exhaustion", 0.0)
            elif option_type == "PE":
                # Increasing for PE
                if rsi_1 > rsi_2 > rsi_3:
                    return ("EXIT", "rsi_exhaustion", 0.0)

        return ("HOLD", "no_exit_condition_met", sl)

    except Exception as e:
        SafetyLogger.log_error_with_context(
            "Monitor_Engine", "execute_hypercare_monitoring", e,
            {"symbol": getattr(position, "symbol", "Unknown"), "ltp": current_ltp}
        )
        return ("HOLD", f"monitor_error_{e}", position.sl)
