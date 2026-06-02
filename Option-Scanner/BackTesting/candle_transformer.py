import pandas as pd
import numpy as np

def to_heikin_ashi(df: pd.DataFrame) -> pd.DataFrame:
    """Transforms a standard OHLC DataFrame into Heikin-Ashi representation."""
    if df is None or len(df) == 0:
        return df
    
    df = df.copy()
    
    # Align case-sensitive column names
    cols = ['open', 'high', 'low', 'close']
    for c in cols:
        if c not in df.columns:
            if c.upper() in df.columns:
                df[c] = df[c.upper()]
            else:
                return df
                
    ha_close = (df['open'] + df['high'] + df['low'] + df['close']) / 4.0
    
    # HA_Open calculation (needs iterative reference)
    ha_open = np.zeros(len(df))
    ha_open[0] = (df['open'].iloc[0] + df['close'].iloc[0]) / 2.0
    
    for i in range(1, len(df)):
        ha_open[i] = (ha_open[i-1] + ha_close.iloc[i-1]) / 2.0
        
    df['open'] = ha_open
    df['close'] = ha_close
    df['high'] = np.maximum(df['high'], np.maximum(df['open'], df['close']))
    df['low'] = np.minimum(df['low'], np.minimum(df['open'], df['close']))
    
    return df

def to_volume_candles(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """Groups consecutive time-based bars into equal-volume bars based on a dynamic EMA20 volume threshold."""
    if df is None or len(df) == 0 or 'volume' not in df.columns:
        return df
        
    df = df.copy()
    df['volume'] = pd.to_numeric(df['volume'], errors='coerce').fillna(0.0)
    
    # If there is no volume data (e.g. Spot Nifty Index), return the original time bars unmodified
    if df['volume'].sum() == 0:
        return df
        
    # Dynamically calculate volume EMA20 (or rolling average) as the threshold
    if len(df) >= period:
        threshold = df['volume'].ewm(span=period, adjust=False).mean().iloc[-1]
    else:
        threshold = df['volume'].mean()
        
    # Safety fallback for low-activity sessions
    if threshold <= 0:
        threshold = 1000.0
    
    volume_bars = []
    accum_vol = 0.0
    bar_open = None
    bar_high = -np.inf
    bar_low = np.inf
    bar_close = None
    bar_start_time = None
    
    for idx, row in df.iterrows():
        vol = float(row['volume'])
        if bar_open is None:
            bar_open = float(row['open'])
            bar_start_time = row.get('start_Time')
            
        bar_high = max(bar_high, float(row['high']))
        bar_low = min(bar_low, float(row['low']))
        bar_close = float(row['close'])
        accum_vol += vol
        
        # Check if threshold met or it's the last row in the set
        if accum_vol >= threshold or idx == len(df) - 1:
            new_bar = {
                'start_Time': bar_start_time,
                'open': bar_open,
                'high': bar_high,
                'low': bar_low,
                'close': bar_close,
                'volume': accum_vol
            }
            # Carry over metadata columns if present
            for col in df.columns:
                if col not in new_bar and col not in ['open', 'high', 'low', 'close', 'volume', 'start_Time']:
                    new_bar[col] = row[col]
            
            volume_bars.append(new_bar)
            
            accum_vol = 0.0
            bar_open = None
            bar_high = -np.inf
            bar_low = np.inf
            bar_close = None
            bar_start_time = None
            
    if not volume_bars:
        return df
        
    return pd.DataFrame(volume_bars)
