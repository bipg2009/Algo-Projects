# Indicators.py

import pandas as pd
import numpy as np
import SafetyLogger

# =========================================================
# INDICATOR CONFIGURATIONS
# =========================================================

EMA_FAST = 9
EMA_SLOW = 20
VOLUME_EMA_PERIOD = 20

# Maintains state for the discrete volume parser
CONTRACT_VOLUME_HISTORY = {}

# =========================================================
# RSI CALCULATION
# =========================================================

def calculate_rsi_series(df, period=14):
    try:
        if df is None or df.empty or "close" not in df.columns:
            return pd.Series(50.0, index=df.index if df is not None else [0])
            
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.rolling(period).mean()
        avg_loss = loss.rolling(period).mean()

        rs = avg_gain / (avg_loss + 1e-9)
        rsi = 100 - (100 / (1 + rs))
        return rsi
    except Exception as e:
        SafetyLogger.log_error_with_context(
            "Indicators", "calculate_rsi_series", e, 
            {"df_len": len(df) if df is not None else 0, "period": period}
        )
        # Return a safe, neutral default series (50.0) so subsequent code does not crash
        length = len(df) if df is not None else 1
        return pd.Series(50.0, index=range(length))

def calculate_rsi(df, period=14):
    try:
        rsi_series = calculate_rsi_series(df, period)
        if len(rsi_series) < 2:
            return 50.0
        val = rsi_series.iloc[-2]
        return 50.0 if pd.isna(val) else float(val)
    except Exception as e:
        SafetyLogger.log_error_with_context(
            "Indicators", "calculate_rsi", e, 
            {"df_len": len(df) if df is not None else 0, "period": period}
        )
        return 50.0

# =========================================================
# VWAP
# =========================================================

def add_vwap(df):
    try:
        if df is None or df.empty:
            return df
        work = df.copy()
        required = ["high", "low", "close", "volume"]
        missing = [col for col in required if col not in work.columns]
        if missing:
            raise KeyError(f"Missing required columns for VWAP calculation: {missing}")
            
        typical_price = (work["high"] + work["low"] + work["close"]) / 3
        cumulative_tpv = (typical_price * work["volume"]).cumsum()
        cumulative_volume = work["volume"].cumsum()
        work["VWAP"] = cumulative_tpv / (cumulative_volume + 1e-9)
        return work
    except Exception as e:
        SafetyLogger.log_error_with_context(
            "Indicators", "add_vwap", e,
            {"columns": list(df.columns) if df is not None else []}
        )
        # Safely fall back by return copy with fallback VWAP to prevent NaN crashes
        fallback = df.copy() if df is not None else pd.DataFrame()
        if "close" in fallback.columns:
            fallback["VWAP"] = fallback["close"]
        else:
            fallback["VWAP"] = 0.0
        return fallback

# =========================================================
# EXPONENTIAL MOVING AVERAGES (EMA)
# =========================================================

def add_ema(df):
    try:
        if df is None or df.empty:
            return df
        work = df.copy()
        if "close" not in work.columns:
            raise KeyError("Missing required column 'close' for EMA calculation")
            
        work["EMA9"] = work["close"].ewm(span=EMA_FAST).mean()
        work["EMA20"] = work["close"].ewm(span=EMA_SLOW).mean()
        return work
    except Exception as e:
        SafetyLogger.log_error_with_context(
            "Indicators", "add_ema", e,
            {"columns": list(df.columns) if df is not None else []}
        )
        fallback = df.copy() if df is not None else pd.DataFrame()
        if "close" in fallback.columns:
            fallback["EMA9"] = fallback["close"]
            fallback["EMA20"] = fallback["close"]
        else:
            fallback["EMA9"] = 0.0
            fallback["EMA20"] = 0.0
        return fallback

# =========================================================
# DISCRETE VOLUME TRACKING
# =========================================================

def calculate_volume_ema(history, current_volume, period=20):
    try:
        if not history:
            return current_volume
        previous_ema = history[-1]
        multiplier = 2 / (period + 1)
        ema = (current_volume * multiplier) + (previous_ema * (1 - multiplier))
        return float(ema)
    except Exception as e:
        SafetyLogger.log_error_with_context(
            "Indicators", "calculate_volume_ema", e,
            {"history_len": len(history), "current_volume": current_volume}
        )
        return float(current_volume)

def parse_discrete_1m_volume(symbol, cumulative_volume):
    try:
        if symbol not in CONTRACT_VOLUME_HISTORY:
            CONTRACT_VOLUME_HISTORY[symbol] = {
                "last_cumulative": cumulative_volume,
                "ema_history": []
            }
            return 0, 0

        previous = CONTRACT_VOLUME_HISTORY[symbol]["last_cumulative"]
        discrete_volume = cumulative_volume - previous
        CONTRACT_VOLUME_HISTORY[symbol]["last_cumulative"] = cumulative_volume

        ema_history = CONTRACT_VOLUME_HISTORY[symbol]["ema_history"]
        volume_ema = calculate_volume_ema(ema_history, discrete_volume, VOLUME_EMA_PERIOD)
        
        ema_history.append(volume_ema)
        if len(ema_history) > 50:
            ema_history.pop(0)

        return discrete_volume, volume_ema
    except Exception as e:
        SafetyLogger.log_error_with_context(
            "Indicators", "parse_discrete_1m_volume", e,
            {"symbol": symbol, "cumulative_volume": cumulative_volume}
        )
        return 0, 0
