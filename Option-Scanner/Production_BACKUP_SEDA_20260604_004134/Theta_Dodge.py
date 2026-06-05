import pandas as pd
from typing import Optional, Dict, Any

# Theta-Dodge Execution Logic
# Duration: 1-5 minutes (Max 3 candles)
# Strategy: Mean Reversion Scalp in Choppy Markets (ADX < 22)

def init() -> None:
    pass

def start() -> None:
    pass

def stop() -> None:
    pass

def health_check() -> bool:
    return True

def _is_choppy(adx: float) -> bool:
    return adx < 22.0

def _is_atr_tradable(current_atr: float) -> bool:
    # 5-18 points is the tradable range for chop scalp. < 5 is dead, > 18 is volatile.
    return 5.0 <= current_atr <= 18.0

def _is_atr_expanding(current_atr: float, prev_atr: float) -> bool:
    # Disable if ATR is expanding
    return current_atr > prev_atr

def _is_orb_active(current_time) -> bool:
    # Disable if within the Opening Range Breakout window (e.g., first 45 mins)
    try:
        time_obj = current_time.time()
        return time_obj.hour == 9 and time_obj.minute >= 15 or (time_obj.hour == 10 and time_obj.minute == 0)
    except Exception:
        return False

def detect_scalp_signal(df_1m: pd.DataFrame, tsl, opt_symbol: str) -> Optional[Dict[str, Any]]:
    if df_1m is None or len(df_1m) < 2:
        return None

    current = df_1m.iloc[-1]
    previous = df_1m.iloc[-2]
    
    # ORB filter
    if _is_orb_active(current.name):
        return None
    
    adx = current.get("ADX", 100)
    if not _is_choppy(adx):
        return None

    # ATR expansion filter
    current_atr = current.get("ATR", 0)
    previous_atr = previous.get("ATR", 0)
    if not _is_atr_tradable(current_atr) or _is_atr_expanding(current_atr, previous_atr):
        return None

    curr_close = current.get("close", 0)
    prev_close = previous.get("close", 0)
    
    curr_lower_bb = current.get("Lower_BB", 0)
    prev_lower_bb = previous.get("Lower_BB", 0)
    curr_upper_bb = current.get("Upper_BB", 0)
    prev_upper_bb = previous.get("Upper_BB", 0)
    
    vwap = current.get("VWAP", 0)
    middle_bb = current.get("Middle_BB", 0)

    # Pre-check direction to avoid unnecessary API calls
    potential_ce = (prev_close < prev_lower_bb and curr_close > curr_lower_bb and curr_close > vwap)
    potential_pe = (prev_close > prev_upper_bb and curr_close < curr_upper_bb and curr_close < vwap)

    if not potential_ce and not potential_pe:
        return None

    # Fetch Option Volume only if Nifty logic passes
    try:
        exch = 'BFO' if opt_symbol.startswith(('SENSEX', 'BANKEX')) else 'NFO'
        opt_df = tsl.get_intraday_data(opt_symbol, exch, 1)
        if opt_df is None or opt_df.empty or len(opt_df) < 20:
            return None
        opt_vol = pd.to_numeric(opt_df["volume"], errors="coerce").fillna(0.0)
        current_vol = opt_vol.iloc[-2]
        avg_vol = opt_vol.rolling(window=20).mean().iloc[-2]
        if current_vol <= 1.5 * avg_vol:
            return None
    except Exception:
        return None



    # CE LOGIC: BB re-entry from below AND price > VWAP
    if potential_ce:
        return {
            "signal": "BUY",
            "option_type": "CE",
            "delta_target": 0.50, # Adjusted for better liquidity/exits
            "reason": "Theta-Dodge CE Scalp",
            "sl_underlying": curr_close - 15,
            "trail_activation_underlying": curr_close + 10,
            "trail_step_underlying": 5,
            "time_stop_candles": 3,
            "strategy": "theta_dodge"
        }
    
    # PE LOGIC: BB re-entry from above AND price < VWAP
    if potential_pe:
        return {
            "signal": "BUY",
            "option_type": "PE",
            "delta_target": 0.50, # Adjusted for better liquidity/exits
            "reason": "Theta-Dodge PE Scalp",
            "sl_underlying": curr_close + 15,
            "trail_activation_underlying": curr_close - 10,
            "trail_step_underlying": 5,
            "time_stop_candles": 3,
            "strategy": "theta_dodge"
        }

    return None
