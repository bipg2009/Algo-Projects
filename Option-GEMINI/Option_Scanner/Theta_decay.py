import pandas as pd
import numpy as np
import os
import json

def calculate_adx(df, period=14):
    """
    Calculates Average Directional Index (ADX) to determine Market Regime.
    < 22 = CHOP / Sideways
    > 25 = Trending
    """
    if df is None or len(df) < period + 1 or not all(col in df.columns for col in ['high', 'low', 'close']):
        return pd.Series(0.0, index=df.index if df is not None else [0])
        
    df = df.copy()
    
    # +DM and -DM Calculations
    df['up_move'] = df['high'].diff()
    df['down_move'] = df['low'].diff()
    
    df['plus_dm'] = np.where((df['up_move'] > df['down_move']) & (df['up_move'] > 0), df['up_move'], 0.0)
    df['minus_dm'] = np.where((df['down_move'] > df['up_move']) & (df['down_move'] > 0), df['down_move'], 0.0)
    
    # True Range
    tr1 = df['high'] - df['low']
    tr2 = (df['high'] - df['close'].shift(1)).abs()
    tr3 = (df['low'] - df['close'].shift(1)).abs()
    df['tr'] = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)
    
    # Smoothed using Wilder's Smoothing method
    tr_smooth = df['tr'].ewm(alpha=1/period, adjust=False).mean()
    plus_di = 100 * (df['plus_dm'].ewm(alpha=1/period, adjust=False).mean() / tr_smooth)
    minus_di = 100 * (df['minus_dm'].ewm(alpha=1/period, adjust=False).mean() / tr_smooth)
    
    dx = 100 * (abs(plus_di - minus_di) / (plus_di + minus_di + 1e-9))
    adx = dx.ewm(alpha=1/period, adjust=False).mean()
    
    return adx

def calculate_bollinger_bands(df, period=20, std_dev=2):
    """Calculates 20-period, 2-SD Bollinger Bands for Mean Reversion targeting."""
    if df is None or len(df) < period or 'close' not in df.columns:
        return df
        
    df = df.copy()
    df['SMA20'] = df['close'].rolling(window=period).mean()
    df['STD20'] = df['close'].rolling(window=period).std()
    
    df['Upper_BB'] = df['SMA20'] + (df['STD20'] * std_dev)
    df['Lower_BB'] = df['SMA20'] - (df['STD20'] * std_dev)
    
    return df

def check_for_chop_reversion(df_1m, chain_df):
    """
    Called from Market_Scanner.py. Returns a signal dict if we should trade reversion.
    Returns: None if no signal, or dict with keys {'symbol', 'option_type', 'score', 'strategy'}
    """
    if df_1m is None or df_1m.empty or chain_df is None or chain_df.empty:
        return None
        
    adx_series = calculate_adx(df_1m)
    current_adx = adx_series.iloc[-1] if not adx_series.empty and pd.notna(adx_series.iloc[-1]) else 0.0
    
    if current_adx >= 22:
        return None # Not in chop mode
        
    # We are in CHOP mode. Disable standard signals, use reversion.
    df_1m = calculate_bollinger_bands(df_1m)
    last_row = df_1m.iloc[-1]
    
    close_price = last_row.get('close', 0)
    upper_bb = last_row.get('Upper_BB', 0)
    lower_bb = last_row.get('Lower_BB', 0)
    
    # Needs RSI from Indicators
    from Indicators import calculate_rsi
    rsi = calculate_rsi(df_1m)
    
    signal_type = None
    if close_price < lower_bb and rsi < 30:
        signal_type = "CE" # Bounce from bottom
    elif close_price > upper_bb and rsi > 70:
        signal_type = "PE" # Reject from top
        
    if not signal_type:
        return None
        
    # Find a Deep ITM option (Delta ~0.70) as per Theta-Dodge plan
    valid_opts = chain_df[chain_df['option_type'] == signal_type]
    if valid_opts.empty:
        return None
        
    # Sort by nearest to 0.7 delta if available. As fallback, max volume deep ITM.
    if 'delta' in valid_opts.columns:
        valid_opts['delta_diff'] = (valid_opts['delta'].abs() - 0.70).abs()
        best_opt = valid_opts.loc[valid_opts['delta_diff'].idxmin()]
    else:
        # Fallback: Just sort by volume and pick a decent one
        best_opt = valid_opts.sort_values(by="volume", ascending=False).iloc[0]
        
    return {
        "symbol": str(best_opt.get("symbol", "")),
        "option_type": signal_type,
        "score": 99, 
        "strategy": "THETA_DODGE"
    }

def commit_theta_dodge_signal(signal_data):
    """Writes the signal json precisely for the Theta-Dodge."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    signal_path = os.path.join(script_dir, "signal.json")
    try:
        with open(signal_path, "w") as f:
            json.dump(signal_data, f)
        print(f"[\033[93mCHOP-MODE\033[0m] Theta-Dodge signal generated for {signal_data['symbol']}. Handing off to MainEngine.", flush=True)
        return True
    except Exception as e:
        print(f"[-] Error writing Theta-Dodge signal: {e}", flush=True)
        return False
