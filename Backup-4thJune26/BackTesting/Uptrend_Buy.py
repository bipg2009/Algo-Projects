import pandas as pd
from typing import Optional, Dict, Any
import indicator_engine
from System_Config import TARGET_POINTS, INITIAL_SL_POINTS, ADX_CHOP_THRESHOLD

# Uptrend Strategy: Buy the Dip (Pullback to Value)
# Regime: Trending Market (ADX > 22) + Uptrend (EMA20 > EMA50) + Rising ADX
# Trigger: Price pulls back to dynamic support (VWAP or EMA 20) with volume exhaustion.


def init() -> None:
    pass


def start() -> None:
    pass


def stop() -> None:
    pass


def health_check() -> bool:
    return True


def find_previous_swing_low(
    df_1m: pd.DataFrame, window: int = 20, exclude_recent: int = 3
) -> float:
    """
    Finds the lowest low in the recent historical window, strictly excluding the current pullback.
    This completely avoids 'left/right' pivot confirmation which can exhibit repainting or lookahead characteristics.
    """
    if len(df_1m) < (window + exclude_recent):
        if len(df_1m) > exclude_recent:
            return float(df_1m["low"].iloc[:-exclude_recent].min())
        return float(df_1m["low"].iloc[0])  # Fallback to day open

    # Look at the historical structural base, excluding the immediate current pullback
    search_slice = df_1m["low"].iloc[-(window + exclude_recent) : -exclude_recent]
    return float(search_slice.min())


def detect_uptrend_pullback_signal(df_1m: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """
    Detects high-probability pullback entries in an established 1m uptrend.
    """
    import System_Config

    if not getattr(System_Config, "ENABLE_CE_TRADES", True):
        return None

    if df_1m is None or len(df_1m) < 20:
        return None

    current = df_1m.iloc[-1]
    previous = df_1m.iloc[-2]

    # 1. Regime Filter: Must be strong UpTrend
    adx = current.get("ADX", 0)
    prev_adx = previous.get("ADX", 0)
    ema20 = current.get("EMA20", 0)
    ema50 = current.get("EMA50", 0)

    # Trend must be > 22 and still strengthening (ADX rising)
    if adx < ADX_CHOP_THRESHOLD or adx <= prev_adx or ema20 <= ema50:
        return None  # Not a strong, strengthening uptrend

    curr_low = current.get("low", 0)

    # 1.5 Structure Confirmation: Price must print a Higher Low relative to the last swing low
    prev_swing_low = find_previous_swing_low(df_1m)
    if curr_low <= prev_swing_low:
        return None  # Violated Higher Low structure (equal or lower trough)

    vwap = current.get("VWAP", 0)
    curr_close = current.get("close", 0)
    prev_close = previous.get("close", 0)

    # 2. Distance check: Price must be touching/rejecting either VWAP or EMA20 dynamically (using volatility ATR)
    atr = current.get("ATR", 15)
    touch_vwap = abs(curr_low - vwap) <= atr * 0.25
    touch_ema = abs(curr_low - ema20) <= atr * 0.25

    if not (touch_vwap or touch_ema):
        return None

    # 3. Confirmation: Rejection of lower prices
    curr_open = current.get("open", 0)
    curr_high = current.get("high", 0)

    # Must be a bullish (green) candle
    if curr_close <= curr_open:
        return None

    # Must prove rejection: lower wick must be greater than or equal to the candle body
    lower_wick = min(curr_open, curr_close) - curr_low
    body = abs(curr_close - curr_open)

    if lower_wick < body:
        return None

    # 3.1 Price Action Confirmation: Buyers must take control.
    # We check if curr_high > prev_high so the backtest correctly simulates a live tick trigger.
    prev_high = previous.get("high", 0)
    bullish_breakout_confirmed = curr_high > prev_high
    if not bullish_breakout_confirmed:
        return None

    # 3.5 Momentum Exhaustion: Pullback losing momentum via RSI rollover
    rsi_series = indicator_engine.calculate_rsi_series(df_1m)
    if rsi_series is None or len(rsi_series) < 2:
        return None

    curr_rsi = rsi_series.iloc[-1]
    prev_rsi = rsi_series.iloc[-2]

    # 1. RSI must be rolling up (current RSI > previous RSI) to confirm momentum bottomed out
    # 2. RSI must stay above 45.0 (bullish zone) but BELOW 75.0 (to avoid buying a climax top)
    if curr_rsi <= prev_rsi or curr_rsi < 42.0 or curr_rsi > 72.0:
        return None

    # 3.6 Overextension / Climax Filter: Ensure price isn't severely stretched from the mean
    atr = current.get("ATR", 15)
    ema20 = current.get("EMA20", 0)
    vwap = current.get("VWAP", 0)

    # If price is floating >1.5 ATR above VWAP, it is vulnerable to mean reversion
    if vwap > 0 and (curr_close - vwap) > (atr * 1.5):
        return None

    # 3.7 Higher Timeframe Trend Alignment: 5m EMA20 must be > 5m EMA50
    # This filters out lunchtime chop and ensures the macro intraday trend is bullish
    ema_5m_20 = current.get("EMA_5m_20", 0)
    ema_5m_50 = current.get("EMA_5m_50", 0)
    if ema_5m_20 > 0 and ema_5m_50 > 0 and ema_5m_20 <= ema_5m_50:
        return None

    # 4. Volume Exhaustion: True exhaustion requires the pullback to dry up
    curr_vol = current.get("volume", 0)
    prev_vol = previous.get("volume", 0)
    prev_prev_vol = df_1m.iloc[-3].get("volume", 0) if len(df_1m) >= 3 else prev_vol

    if "volume" in df_1m.columns and len(df_1m) >= 20:
        avg_vol = df_1m["volume"].rolling(20).mean().iloc[-1]
    else:
        avg_vol = prev_vol

    # Exhaustion Rule 1: The pullback volume must dry up.
    # It must EITHER be slightly lower than the rolling average (10% buffer), OR strictly lower than the preceding candle.
    if prev_vol >= (avg_vol * 1.1) and prev_vol >= prev_prev_vol:
        return None

    # Exhaustion Rule 2: Buyers must step back in with expanding volume on the bounce
    if curr_vol <= prev_vol:
        return None

    atr = current.get("ATR", 15)

    # 5. Delta Assumption Removed
    # We no longer estimate premium points using underlying_points_target * 0.5
    # The true option target will be calculated by the execution engine using the ACTUAL option premium data (LTP).
    # We provide the underlying targets strictly for structural trailing reference.

    return {
        "signal": "BUY",
        "option_type": "CE",
        "delta_target": 0.50,  # Target moneyness for strike selection only
        "reason": "Uptrend Pullback to Support (VWAP/EMA) + Vol Exhaustion",
        "sl_premium_points": INITIAL_SL_POINTS,  # Fallback
        "target_premium_points": TARGET_POINTS,  # Fallback
        "sl_underlying": curr_close - 20.0,  # True structural SL (20 Nifty points)
        "target_underlying": curr_close + (atr * 2.0),  # True structural target
        "trail_activation_underlying": curr_close + atr,
        "trail_step_underlying": atr * 0.5,
    }
