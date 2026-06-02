import pandas as pd
import datetime
import os
import time
from dotenv import load_dotenv
from Dhan_Tradehull import Tradehull

# Load credentials and initialize Dhan
load_dotenv("cred.env")
client_code = os.getenv("DHAN_CLIENT_CODE")
token_id = os.getenv("DHAN_TOKEN_ID")

if not client_code or not token_id:
    raise ValueError("Dhan API credentials missing in cred.env")

Dhan = Tradehull(client_code, token_id)

LARGE_CAP = ["RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "BHARTIARTL", "INFY", "ITC", "SBIN", "LT", "HINDUNILVR", "BAJFINANCE", "MARUTI", "KOTAKBANK", "AXISBANK", "ASIANPAINT", "TITAN", "SUNPHARMA", "TATASTEEL", "ULTRACEMCO", "BAJAJFINSV"]
MID_CAP = ["FEDERALBNK", "IDFCFIRSTB", "TRENT", "TVSMOTOR", "OBEROIRLTY", "PIIND", "POLYCAB", "AUBANK", "COFORGE", "ASHOKLEY", "M&MFIN", "CUMMINSIND", "VOLTAS", "DIXON", "LALPATHLAB", "SYNGENE", "BALKRISIND", "COROMANDEL", "BATAINDIA", "GODREJPROP"]
SMALL_CAP = ["CDSL", "ANGELONE", "BSE", "CAMS", "IEX", "HAPPSTMNDS", "ROUTE", "LATENTVIEW", "MTARTECH", "MAPMYINDIA", "CLEAN", "GRINFRA", "DEVYANI", "KPRMILL", "LUXIND", "VIPIND", "CENTURYPLY", "CERA", "KAJARIACER", "FINCABLES"]
FIN_CAP = ["HDFCBANK", "ICICIBANK", "KOTAKBANK", "AXISBANK", "SBIN", "BAJFINANCE", "BAJAJFINSV", "CHOLAFIN", "SHRIRAMFIN", "MUTHOOTFIN", "HDFCAMC", "NAM-INDIA", "HDFCLIFE", "SBILIFE", "ICICIPRULI", "ICICIGI", "STARHEALTH", "PAYTM", "PFC", "RECLTD"]

import yfinance as yf

def fetch_stock_data_dhan(tickers, timeframe="daily"):
    results = []
    
    for ticker in tickers:
        try:
            # Fetch 365 days of historical data for 52W High/Low calculation using Dhan
            df = Dhan.get_historical_data(ticker, "NSE", 365)
            
            if df is None or df.empty:
                print(f"Skipping {ticker}: No historical data")
                continue
                
            # Convert start_Time to datetime for resampling
            df['start_Time'] = pd.to_datetime(df['start_Time'])
            df.set_index('start_Time', inplace=True)
            
            if timeframe == "weekly":
                df = df.resample('W-FRI').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
                avg_vol_lookback = 4
            elif timeframe == "monthly":
                df = df.resample('M').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
                avg_vol_lookback = 6
            else:
                avg_vol_lookback = 20
                
            high_52w = df['high'].max()
            low_52w = df['low'].min()
            
            # Calculate Average Volume
            avg_vol_20d = df['volume'].tail(avg_vol_lookback).mean()
            
            # Fetch live current price via Dhan REST fallback (skipping xlwings)
            live_ltp = Dhan._get_ltp_via_rest([ticker])
            if not live_ltp or float(live_ltp) <= 0:
                current_price = df['close'].iloc[-1]
            else:
                current_price = float(live_ltp)
                
            prev_close = df['close'].iloc[-2] if len(df) > 1 else current_price
            current_vol = df['volume'].iloc[-1]
            
            results.append({
                "Symbol": ticker,
                "CMP": round(float(current_price), 2),
                "52W_High": round(float(max(high_52w, current_price)), 2),
                "52W_Low": round(float(min(low_52w, current_price)), 2),
                "Volume_Surge": round(float(current_vol / avg_vol_20d), 1) if avg_vol_20d > 0 else 0,
                "Close_GT_Prev": float(current_price) > float(prev_close),
                "Avg_Vol_20D": float(avg_vol_20d)
            })
            
            # Small delay to respect Dhan API rate limits
            time.sleep(0.1)
            
        except Exception as e:
            print(f"Error processing {ticker} via Dhan API: {e}")
            
    return pd.DataFrame(results)

def get_breakout_stocks(category, timeframe="daily"):
    if category == "Large Cap":
        tickers = LARGE_CAP
    elif category == "Mid Cap":
        tickers = MID_CAP
    elif category == "Small Cap":
        tickers = SMALL_CAP
    else:
        tickers = FIN_CAP
        
    df = fetch_stock_data_dhan(tickers, timeframe)
    if df.empty:
        return []
        
    # Breakout Conditions:
    # 1. CMP >= 52W High (or within 2% to capture near breakouts)
    # 2. Volume > 20 Day Average Volume
    # 3. Close > Previous Day Close
    
    breakout_df = df[
        (df['CMP'] >= df['52W_High'] * 0.98) & 
        (df['Volume_Surge'] > 1.0) &
        (df['Close_GT_Prev'] == True)
    ]
    
    breakout_df = breakout_df.sort_values(by="Volume_Surge", ascending=False).head(10)
    
    output = []
    for rank, (i, row) in enumerate(breakout_df.iterrows(), 1):
        output.append({
            "Rank": rank,
            "Symbol": row["Symbol"],
            "Sector": category,
            "CMP": f"Rs.{row['CMP']}",
            "52W_High": "New High" if row['CMP'] >= row['52W_High'] else f"Rs.{row['52W_High']}",
            "Volume_Surge": f"{row['Volume_Surge']}x"
        })
        
    return output

def get_value_stocks(category, timeframe="daily"):
    if category == "Large Cap":
        tickers = LARGE_CAP
    elif category == "Mid Cap":
        tickers = MID_CAP
    elif category == "Small Cap":
        tickers = SMALL_CAP
    else:
        tickers = FIN_CAP
        
    df = fetch_stock_data_dhan(tickers, timeframe)
    if df.empty:
        return []
        
    # Value Conditions:
    # CMP within +20% of 52W Low
    df['Distance_From_Low'] = (df['CMP'] - df['52W_Low']) / df['52W_Low']
    value_df = df[df['Distance_From_Low'] <= 0.20]
    
    value_df = value_df.sort_values(by="Distance_From_Low", ascending=True).head(10)
    
    output = []
    for rank, (i, row) in enumerate(value_df.iterrows(), 1):
        output.append({
            "Rank": rank,
            "Symbol": row["Symbol"],
            "Sector": category,
            "CMP": f"Rs.{row['CMP']}",
            "52W_Low": f"Rs.{row['52W_Low']}",
            "Distance": f"{round(row['Distance_From_Low'] * 100, 1)}%"
        })
        
    return output
