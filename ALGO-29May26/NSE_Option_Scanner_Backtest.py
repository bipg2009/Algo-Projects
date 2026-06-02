import pandas as pd
import datetime
import sys
import os
import time

import Risk_Engine as risk_engine
import RiseFall_sub as rise_fall
import indicator_engine as Indicators
import Option_strategy_core as core
import Chop_Mode

# Configuration for Backtest
STRONG_BUY_THRESHOLD = 85
TACTICAL_LOOKBACK = 15
EXHAUSTION_WINDOW = 30
PE_EXHAUSTION_WINDOW = 15
MAX_NIFTY_DROP = 100.0       
NIFTY_DROP_WINDOW = 30       
PCR_BULLISH = 1.15
PCR_BEARISH = 0.85
NORMAL_ITM_DISTANCE = 100
GAP_ITM_DISTANCE = 150
OI_CHANGE_ALERT_PCT = 20.0

def generate_mock_1m_data(spot_price, total_bars=100):
    start_time = datetime.datetime.now().replace(hour=9, minute=15, second=0, microsecond=0)
    data = []
    
    current_price = spot_price
    
    from random import randrange, random
    
    for i in range(total_bars):
        current_time = start_time + datetime.timedelta(minutes=i)
        
        # Simple random walk
        change = (random() - 0.5) * 5 
        open_p = current_price
        close_p = current_price + change
        high_p = max(open_p, close_p) + random() * 2
        low_p = min(open_p, close_p) - random() * 2
        
        current_price = close_p
        
        # Random volume
        volume = randrange(100, 10000)
        
        data.append({
            'start_Time': current_time.strftime('%Y-%m-%d %H:%M:%S'),
            'open': open_p,
            'high': high_p,
            'low': low_p,
            'close': close_p,
            'volume': volume
        })
        
    df = pd.DataFrame(data)
    df['datetime'] = pd.to_datetime(df['start_Time'])
    df.set_index('start_Time', inplace=True)
    return df

def generate_mock_option_chain():
    return pd.DataFrame({
        'strike': [24000, 24100, 24200, 24300, 24400, 24500],
        'option_type': ['CE']*3 + ['PE']*3,
        'symbol': ['NIFTY 24000 CE', 'NIFTY 24100 CE', 'NIFTY 24200 CE', 'NIFTY 24300 PE', 'NIFTY 24400 PE', 'NIFTY 24500 PE'],
        'ltp': [150, 100, 50, 50, 100, 150],
        'oi': [1000, 2000, 5000, 1000, 3000, 6000],
        'volume': [5000, 10000, 20000, 5000, 15000, 25000],
        'previous_oi': [900, 1800, 4800, 950, 2900, 5800],
    })

def get_historical_data_from_dhan(symbol, exchange, timeframe, days):
    from dotenv import load_dotenv
    load_dotenv('cred.env')
    client_code = os.getenv('CLIENT_CODE')
    token = os.getenv('TOKEN_ID')
    
    if not client_code or not token:
        print("[-] Dhan API credentials not found in environment variables.")
        return None
        
    print(f"Connecting to Dhan to fetch historical data for {symbol}...")
    import Dhan_Tradehull as dth
    try:
        tradehull = dth.Tradehull(client_code, token)
        # timeframe is an int like 1, 5, 15 etc.
        df = tradehull.get_intraday_data(symbol, exchange, timeframe)
        if df is not None and not df.empty:
            print(f"[+] Successfully fetched {len(df)} historical bars for {symbol}.")
            return df
        else:
            print(f"[-] No historical data returned for {symbol}.")
            return None
    except Exception as e:
        print(f"[-] Error fetching historical data from Dhan API: {e}")
        return None

def backtest_strategy(target_date_str=None, live_data=False):
    from SafetyLogger import log_info, log_error_with_context
    
    print("=" * 60)
    print(f"Starting Backtest Simulator - Date: {target_date_str or datetime.datetime.now().date()}")
    print("=" * 60)
    
    df_1m = None
    option_chain_df = None
    
    # 1. Fetch Data
    print("[1] Fetching Data")
    if live_data:
        # Fetching historical 1m data for backtest
        df_1m = get_historical_data_from_dhan("NIFTY 50", "NSE", 1, 5)
        # Mocking option chain data since historical option chain is usually not provided via standard intraday APIs
        option_chain_df = generate_mock_option_chain()
    
    if df_1m is None or df_1m.empty:
        print("    -> Falling back to mock data...")
        nifty_spot = 24250.0
        df_1m = generate_mock_1m_data(nifty_spot)
        option_chain_df = generate_mock_option_chain()
    
    nifty_spot = df_1m.iloc[-1]['close']
    previous_close = df_1m.iloc[0]['close'] 
    today_open = df_1m.iloc[0]['open']
    
    print(f"Loaded {len(df_1m)} 1-minute bars.")
    
    # 2. Run Pre-Computations (Indicators etc)
    print("\n[2] Applying Indicators")
    df_1m = Indicators.add_vwap(df_1m)
    df_1m = Indicators.add_ema(df_1m)
    df_1m = Indicators.add_supertrend(df_1m)
    rsi_series = Indicators.calculate_rsi_series(df_1m)
    df_1m['RSI'] = rsi_series
    
    print(f"Latest 1m Supertrend: {df_1m.iloc[-1]['st_color']}, RSI: {df_1m.iloc[-1]['RSI']:.2f}")
    
    # 3. Test Core Strategy Logic
    print("\n[3] Testing Core Strategy Logic (CE/PE Triggers)")
    
    opt_row_ce = {
        'symbol': 'NIFTY 24100 CE',
        'strike': 24100,
        'ltp': 100,
        'volume': 15000,
        'oi_change': 15
    }
    
    opt_row_pe = {
        'symbol': 'NIFTY 24400 PE',
        'strike': 24400,
        'ltp': 100,
        'volume': 12000,
        'oi_change': 8
    }
    
    # Check CE
    trigger_ce = core.detect_trigger_1m(
        df_1m=df_1m, 
        option_type="CE", 
        opt_row=opt_row_ce, 
        nifty_spot=nifty_spot, 
        previous_close=previous_close, 
        today_open=today_open, 
        pcr_value=1.2, 
        option_chain_df=option_chain_df
    )
    
    print(f"CE Option ({opt_row_ce['symbol']}) Trigger Signal: {trigger_ce}")
    
    if not trigger_ce:
        _, reason_ce, details_ce = core.explain_trigger_failure(
            df_1m=df_1m, 
            option_type="CE", 
            opt_row=opt_row_ce, 
            nifty_spot=nifty_spot, 
            previous_close=previous_close, 
            today_open=today_open, 
            pcr_value=1.2, 
            option_chain_df=option_chain_df
        )
        print(f"-> CE failure reason: {reason_ce}")
        print(f"-> CE details: {details_ce}")
        
        
    print("-" * 30)
    
    # Check PE
    trigger_pe = core.detect_trigger_1m(
        df_1m=df_1m, 
        option_type="PE", 
        opt_row=opt_row_pe, 
        nifty_spot=nifty_spot, 
        previous_close=previous_close, 
        today_open=today_open, 
        pcr_value=0.8, 
        option_chain_df=option_chain_df
    )
    
    print(f"PE Option ({opt_row_pe['symbol']}) Trigger Signal: {trigger_pe}")
    
    if not trigger_pe:
        _, reason_pe, details_pe = core.explain_trigger_failure(
            df_1m=df_1m, 
            option_type="PE", 
            opt_row=opt_row_pe, 
            nifty_spot=nifty_spot, 
            previous_close=previous_close, 
            today_open=today_open, 
            pcr_value=0.8, 
            option_chain_df=option_chain_df
        )
        print(f"-> PE failure reason: {reason_pe}")
        print(f"-> PE details: {details_pe}")
        
    print("\n[4] Testing Risk Engine")
    try:
        gap_val = risk_engine.detect_gap_risk(previous_close, today_open)
        print(f"Gap Risk Detected: {gap_val}")
    except Exception as e:
        print(f"Risk Engine Error: {e}")

    print("\n==================================")
    print("Backtest Simulator Completed")
    print("==================================")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Run NSE Option strategy backtest.')
    parser.add_argument('date', nargs='?', default=None, help='Target date in YYYY-MM-DD format')
    parser.add_argument('--live-data', action='store_true', help='Fetch historical data from Dhan API')
    args = parser.parse_args()
    
    target_date = args.date
    live_data = args.live_data
    
    try:
        if target_date:
            datetime.datetime.strptime(target_date, "%Y-%m-%d")
    except ValueError:
        print("Invalid date format. Using current date. Ex: YYYY-MM-DD")
        target_date = None
        
    backtest_strategy(target_date, live_data=live_data)

if __name__ == "__main__":
    main()
