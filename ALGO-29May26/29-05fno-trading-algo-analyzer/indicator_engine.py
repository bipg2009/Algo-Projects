import pandas as pd
import numpy as np
import SafetyLogger

EMA_FAST = 9
EMA_SLOW = 20
VOLUME_EMA_PERIOD = 20
CONTRACT_VOLUME_HISTORY = {}

def init():
    pass

def start():
    pass

def stop():
    pass

def health_check():
    return True

def calculate_rsi_series(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Optimized NumPy-based RSI calculation to minimize pandas overhead in tick execution."""
    try:
        if df is None or df.empty or "close" not in df.columns:
            return pd.Series(50.0, index=df.index if df is not None else [0])
            
        # Fast-path for backtesting
        if "RSI" in df.columns and "RSI_14" in df.columns:
            return df["RSI"]
            
        close_prices = pd.to_numeric(df["close"], errors='coerce').fillna(0.0).values
        diffs = np.diff(close_prices)
        
        gains = np.where(diffs > 0, diffs, 0)
        losses = np.where(diffs < 0, -diffs, 0)
        
        # Pre-allocate array for RSI
        rsi_vals = np.zeros_like(close_prices, dtype=float)
        rsi_vals[:period] = 50.0
        
        if len(close_prices) > period:
            avg_gain = np.mean(gains[:period])
            avg_loss = np.mean(losses[:period])
            
            rs = avg_gain / (avg_loss + 1e-9)
            rsi_vals[period] = 100 - (100 / (1 + rs))
            
            for i in range(period + 1, len(close_prices)):
                avg_gain = (avg_gain * (period - 1) + gains[i - 1]) / period
                avg_loss = (avg_loss * (period - 1) + losses[i - 1]) / period
                rs = avg_gain / (avg_loss + 1e-9)
                rsi_vals[i] = 100 - (100 / (1 + rs))
                
        return pd.Series(rsi_vals, index=df.index)
    except Exception as e:
        SafetyLogger.log_error_with_context("indicator_engine", "calculate_rsi_series", e, {"period": period})
        length = len(df) if df is not None else 1
        return pd.Series(50.0, index=range(length))

def calculate_rsi(df: pd.DataFrame, period: int = 14) -> float:
    try:
        rsi_series = calculate_rsi_series(df, period)
        if len(rsi_series) < 2:
            return 50.0
        val = rsi_series.iloc[-2]
        return 50.0 if pd.isna(val) else float(val)
    except Exception as e:
        SafetyLogger.log_error_with_context("indicator_engine", "calculate_rsi", e, {"period": period})
        return 50.0

def add_vwap(df: pd.DataFrame) -> pd.DataFrame:
    try:
        if df is None or df.empty:
            return df
        # Fast-path optimization: skip recalculation if already present and valid (like in backtesting)
        if "VWAP" in df.columns and not pd.isna(df["VWAP"].iloc[-1]):
            return df
            
        work = df.copy()
        if not all(col in work.columns for col in ["high", "low", "close", "volume"]):
            if "close" in work.columns: work["VWAP"] = work["close"]
            else: work["VWAP"] = 0.0
            return work
            
        h = pd.to_numeric(work["high"], errors='coerce').values
        l = pd.to_numeric(work["low"], errors='coerce').values
        c = pd.to_numeric(work["close"], errors='coerce').values
        v = pd.to_numeric(work["volume"], errors='coerce').values
        tp = (h + l + c) / 3
        cum_tpv = np.cumsum(tp * v)
        cum_v = np.cumsum(v)
        
        vwap_vals = cum_tpv / (cum_v + 1e-9)
        work["VWAP"] = vwap_vals
        return work
    except Exception as e:
        SafetyLogger.log_error_with_context("indicator_engine", "add_vwap", e)
        fallback = df.copy() if df is not None else pd.DataFrame()
        fallback["VWAP"] = fallback["close"] if "close" in fallback.columns else 0.0
        return fallback

def add_ema(df: pd.DataFrame) -> pd.DataFrame:
    try:
        if df is None or df.empty or "close" not in df.columns:
            return df
        # Fast-path optimization: skip recalculation if already present and valid (like in backtesting)
        if "EMA9" in df.columns and "EMA20" in df.columns and not pd.isna(df["EMA9"].iloc[-1]):
            return df
            
        work = df.copy()
        
        close_series = pd.to_numeric(work["close"], errors='coerce')
        # EWM using pandas is optimized in Cython, safe for column ops
        work["EMA9"] = close_series.ewm(span=EMA_FAST, adjust=False).mean()
        work["EMA20"] = close_series.ewm(span=EMA_SLOW, adjust=False).mean()
        return work
    except Exception as e:
        SafetyLogger.log_error_with_context("indicator_engine", "add_ema", e)
        fallback = df.copy() if df is not None else pd.DataFrame()
        fallback["EMA9"] = fallback.get("close", 0.0)
        fallback["EMA20"] = fallback.get("close", 0.0)
        return fallback

def calculate_volume_ema(history: list, current_volume: float, period: int = 20) -> float:
    try:
        if not history: return current_volume
        prev_ema = history[-1]
        mult = 2 / (period + 1)
        return float((current_volume * mult) + (prev_ema * (1 - mult)))
    except Exception as e:
        SafetyLogger.log_error_with_context("indicator_engine", "calc_vol_ema", e)
        return float(current_volume)

def parse_discrete_1m_volume(symbol: str, cumulative_volume: int) -> tuple:
    try:
        if symbol not in CONTRACT_VOLUME_HISTORY:
            CONTRACT_VOLUME_HISTORY[symbol] = {"last_cumulative": cumulative_volume, "ema_history": []}
            return 0, 0

        prev = CONTRACT_VOLUME_HISTORY[symbol]["last_cumulative"]
        disc_vol = cumulative_volume - prev
        CONTRACT_VOLUME_HISTORY[symbol]["last_cumulative"] = cumulative_volume

        ema_hist = CONTRACT_VOLUME_HISTORY[symbol]["ema_history"]
        v_ema = calculate_volume_ema(ema_hist, disc_vol, VOLUME_EMA_PERIOD)
        
        ema_hist.append(v_ema)
        if len(ema_hist) > 50: ema_hist.pop(0)

        return disc_vol, v_ema
    except Exception as e:
        SafetyLogger.log_error_with_context("indicator_engine", "parse_disc_vol", e)
        return 0, 0

def add_supertrend(df: pd.DataFrame, period=10, multiplier=3) -> pd.DataFrame:
    try:
        if df is None or df.empty or not all(col in df.columns for col in ["high", "low", "close"]):
            if df is not None:
                df["supertrend"] = df.get("close", 0.0)
                df["st_color"] = "GREEN"
            return df
            
        # Fast-path optimization
        if "supertrend" in df.columns and "st_color" in df.columns and not pd.isna(df["supertrend"].iloc[-1]):
            return df
            
        df = df.copy()
        high = pd.to_numeric(df['high'], errors='coerce')
        low = pd.to_numeric(df['low'], errors='coerce')
        close = pd.to_numeric(df['close'], errors='coerce')
        
        # Calculate ATR
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)
        atr = tr.ewm(alpha=1/period, adjust=False).mean()
        
        # Calculate Supertrend
        hl2 = (high + low) / 2
        final_upperband = hl2 + (multiplier * atr)
        final_lowerband = hl2 - (multiplier * atr)
        
        supertrend = [True] * len(df)
        
        for i in range(1, len(df.index)):
            curr, prev = i, i-1
            
            if close.iloc[curr] > final_upperband.iloc[prev]:
                supertrend[curr] = True
            elif close.iloc[curr] < final_lowerband.iloc[prev]:
                supertrend[curr] = False
            else:
                supertrend[curr] = supertrend[prev]
                if supertrend[curr] == True and final_lowerband.iloc[curr] < final_lowerband.iloc[prev]:
                    final_lowerband.iloc[curr] = final_lowerband.iloc[prev]
                if supertrend[curr] == False and final_upperband.iloc[curr] > final_upperband.iloc[prev]:
                    final_upperband.iloc[curr] = final_upperband.iloc[prev]
            
            if supertrend[curr] == True:
                final_upperband.iloc[curr] = np.nan
            else:
                final_lowerband.iloc[curr] = np.nan
                
        st = pd.DataFrame({
            'Supertrend': np.where(supertrend, final_lowerband, final_upperband),
            'Color': np.where(supertrend, 'GREEN', 'RED')
        }, index=df.index)
        
        df['supertrend'] = st['Supertrend']
        df['st_color'] = st['Color']
        
        return df
    except Exception as e:
        SafetyLogger.log_error_with_context("indicator_engine", "add_supertrend", e)
        df["supertrend"] = df.get("close", 0.0)
        df["st_color"] = "GREEN"
        return df

def display_atr_details(tsl):
    print("[i] Fetching historical data to calculate ATR...", flush=True)
    try:
        import pandas as pd
        df = None
        # Tradehull's get_historical_data will raise and print an unsightly IndexError for index tracking.
        # Bypass it entirely and use get_intraday_data which is explicitly index-aware for NIFTY.
        try:
            df = tsl.get_intraday_data("NIFTY", "NSE", 60)
            if df is not None and not df.empty:
                # Group by day to make pseudo-daily data for ATR
                df['date'] = pd.to_datetime(df['timestamp']).dt.date if 'timestamp' in df.columns else pd.to_datetime(df['start_Time']).dt.date
                df['high'] = pd.to_numeric(df['high'])
                df['low'] = pd.to_numeric(df['low'])
                df['close'] = pd.to_numeric(df['close'])
                df = df.groupby('date').agg({'high': 'max', 'low': 'min', 'close': 'last'}).reset_index()
        except Exception:
            pass
        
        if df is None or df.empty:
            print("[!] Could not fetch historical data for NIFTY to calculate ATR.", flush=True)
            return
        
        df['high'] = pd.to_numeric(df['high'])
        df['low'] = pd.to_numeric(df['low'])
        df['close'] = pd.to_numeric(df['close'])
        
        # True Range Calculation
        df['prev_close'] = df['close'].shift(1)
        df['tr1'] = df['high'] - df['low']
        df['tr2'] = (df['high'] - df['prev_close']).abs()
        df['tr3'] = (df['low'] - df['prev_close']).abs()
        df['tr'] = pd.DataFrame({'tr1': df['tr1'], 'tr2': df['tr2'], 'tr3': df['tr3']}).max(axis=1)
        
        # 14-day ATR using RMA/EWMA
        period = 14
        df['atr'] = df['tr'].ewm(alpha=1/period, adjust=False).mean()
        
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        
        latest_atr = float(latest['atr'])
        latest_close = float(latest['close'])
        prev_atr = float(prev['atr'])
        
        pct = (latest_atr / latest_close) * 100.0 if latest_close > 0 else 0.0
        direction = "UP (Expanding Volatility)" if latest_atr > prev_atr else "DOWN (Contracting Volatility)"
        
        print("\n" + "="*45)
        print(" 📊 NIFTY 14-DAY ATR DETAILS ")
        print("="*45)
        print(f" Current ATR   : {latest_atr:.2f} points")
        print(f" Index Price   : {latest_close:.2f}")
        print(f" ATR % of Price: {pct:.2f}%")
        print(f" ATR Trend     : {direction}")
        print("="*45 + "\n", flush=True)
        
    except Exception as e:
        print(f"[!] Error calculating ATR: {e}", flush=True)
        import SafetyLogger
        SafetyLogger.log_error_with_context("indicator_engine", "display_atr_details", e)
