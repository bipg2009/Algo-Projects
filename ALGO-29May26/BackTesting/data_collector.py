import sys
import os
import datetime
import pandas as pd
from dotenv import load_dotenv

# Add parent directory to path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import Dhan_Tradehull as tradehull

def load_client():
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cred.env"))
    client_code = os.getenv("DHAN_CLIENT_CODE")
    token_id = os.getenv("DHAN_TOKEN_ID")
    if not client_code or not token_id:
        print("DHAN_CLIENT_CODE or DHAN_TOKEN_ID not found in environment.")
        return None
    try:
        return tradehull.Tradehull(client_code, token_id)
    except Exception as e:
        print(f"Error initializing Tradehull client: {e}")
        return None

def fetch_intraday_data(client, tradingsymbol, exchange, timeframe, total_days=90):
    try:
        # direct access to dhanhq
        dhan = client.Dhan
        df_instr = client.instrument_df
        
        script_exchange = {"NSE": dhan.NSE, "BSE": dhan.BSE}
        instrument_exchange = {'NSE': "NSE", 'BSE': "BSE"}
        
        rows = df_instr[
            ((df_instr['SEM_TRADING_SYMBOL'] == tradingsymbol) | (df_instr['SEM_CUSTOM_SYMBOL'] == tradingsymbol))
            & (df_instr['SEM_EXM_EXCH_ID'] == instrument_exchange.get(exchange, exchange))
        ]
        
        if "SEM_SERIES" in rows.columns and exchange in ("NSE", "BSE"):
            eq = rows[rows["SEM_SERIES"] == "EQ"]
            if not eq.empty:
                rows = eq
                
        if rows.empty:
            print(f"Symbol {tradingsymbol} not found in instrument mapping.")
            return None
            
        row = rows.iloc[-1]
        security_id = str(row['SEM_SMST_SECURITY_ID'])
        instrument_type = row['SEM_INSTRUMENT_NAME']
        
        if str(row.get("SEM_SEGMENT", "")) == "I" or instrument_type == "INDEX":
            exchangeSegment = dhan.INDEX
        else:
            exchangeSegment = script_exchange.get(exchange, dhan.NSE)
            
        all_dfs = []
        end_date = datetime.datetime.now()
        
        # Dhan intraday API has a limit, so fetch in chunks of 30 days
        for i in range(total_days, 0, -30):
            chunk_days = min(30, i)
            start_date = end_date - datetime.timedelta(days=chunk_days)
            
            to_date_str = end_date.strftime('%Y-%m-%d')
            from_date_str = start_date.strftime('%Y-%m-%d')
            
            print(f"Fetching chunk from {from_date_str} to {to_date_str}...")
            
            # Calling Dhan HQ intraday API
            ohlc = dhan.intraday_minute_data(security_id, exchangeSegment, instrument_type, from_date_str, to_date_str)
            
            data = ohlc.get('data') if isinstance(ohlc, dict) else None
            if data and isinstance(data, dict) and (data.get('timestamp') or data.get('start_Time')):
                df_chunk = pd.DataFrame(data)
                
                time_col = 'timestamp' if 'timestamp' in df_chunk.columns else 'start_Time'
                
                # Proper dhan time conversion
                if pd.api.types.is_numeric_dtype(df_chunk[time_col]):
                    df_chunk[time_col] = df_chunk[time_col].apply(lambda x: dhan.convert_to_date_time(x))
                    
                df_chunk[time_col] = pd.to_datetime(df_chunk[time_col])
                df_chunk.set_index(time_col, inplace=True)
                all_dfs.append(df_chunk)
            
            # Move end_date back for the next chunk
            end_date = start_date - datetime.timedelta(days=1)
            
        if not all_dfs:
            print(f"No intraday data returned for {tradingsymbol}.")
            return None
            
        df = pd.concat(all_dfs).sort_index().drop_duplicates()
        
        resample_str = f'{timeframe}min'
        df_resampled = df.resample(resample_str).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        
        df_resampled.reset_index(inplace=True)
        print(f"Total rows fetched for {tradingsymbol}: {len(df_resampled)}")
        return df_resampled
    except Exception as e:
        print(f"Error fetching intraday data via DhanHQ: {e}")
        return None

def fetch_historical_data(client, tradingsymbol, exchange, days):
    try:
        dhan = client.Dhan
        df_instr = client.instrument_df
        
        from_date = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime('%Y-%m-%d')
        to_date = datetime.datetime.now().strftime('%Y-%m-%d') 
        
        script_exchange = {"NSE": dhan.NSE, "BSE": dhan.BSE}
        instrument_exchange = {'NSE': "NSE", 'BSE': "BSE"}
        
        rows = df_instr[
            ((df_instr['SEM_TRADING_SYMBOL'] == tradingsymbol) | (df_instr['SEM_CUSTOM_SYMBOL'] == tradingsymbol))
            & (df_instr['SEM_EXM_EXCH_ID'] == instrument_exchange.get(exchange, exchange))
        ]
        
        if "SEM_SERIES" in rows.columns and exchange in ("NSE", "BSE"):
            eq = rows[rows["SEM_SERIES"] == "EQ"]
            if not eq.empty:
                rows = eq
                
        if rows.empty:
            print(f"Symbol {tradingsymbol} not found in instrument mapping.")
            return None
            
        row = rows.iloc[-1]
        security_id = str(row['SEM_SMST_SECURITY_ID'])
        Symbol = row['SEM_TRADING_SYMBOL']
        instrument_type = row['SEM_INSTRUMENT_NAME']
        expiry_code = str(row['SEM_EXPIRY_CODE']) # IMPORTANT: Must cast to string to avoid 'int upper' error in API
        if expiry_code == "0" or expiry_code == "0.0":
            if str(row.get("SEM_SEGMENT", "")) == "I" or instrument_type == "INDEX":
                expiry_code = "" # Or whatever the API expects, typically empty or 0 doesn't have an upper method, but Dhan accepts '0' string sometimes
        
        
        if str(row.get("SEM_SEGMENT", "")) == "I" or instrument_type == "INDEX":
            exchangeSegment = dhan.INDEX
        else:
            exchangeSegment = script_exchange.get(exchange, dhan.NSE)
            
        ohlc = dhan.historical_daily_data(Symbol, exchangeSegment, instrument_type, expiry_code, from_date, to_date)
        
        data = ohlc.get('data') if isinstance(ohlc, dict) else None
        if not data or not isinstance(data, dict):
            print(f"No historical data returned for {tradingsymbol}.")
            return None
            
        df = pd.DataFrame(data)
        
        # Proper dhan time conversion
        if 'start_Time' in df.columns:
            time_col = 'start_Time'
        elif 'timestamp' in df.columns:
            time_col = 'timestamp'
        else:
            time_col = None
            
        if time_col and pd.api.types.is_numeric_dtype(df[time_col]):
            df[time_col] = df[time_col].apply(lambda x: dhan.convert_to_date_time(x))
            
        return df
    except Exception as e:
        print(f"Error fetching historical data via DhanHQ: {e}")
        return None

def collect_data(client, symbol, exchange="NSE", days=100, timeframe=None):
    if not client:
        return None
    print(f"Fetching data for {symbol} on {exchange}...")
    try:
        if timeframe:
            df = fetch_intraday_data(client, symbol, exchange, timeframe, total_days=days)
        else:
            df = fetch_historical_data(client, symbol, exchange, days)
            
        if df is not None and not df.empty:
            output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
            os.makedirs(output_dir, exist_ok=True)
            res_str = f"_{timeframe}min" if timeframe else f"_daily"
            filename = f"{symbol}_{exchange}{res_str}.csv"
            filepath = os.path.join(output_dir, filename)
            df.to_csv(filepath, index=False)
            print(f"Saved {len(df)} rows to {filepath}")
            return df
        else:
            print(f"No data retrieved for {symbol}.")
            return None
    except Exception as e:
        print(f"Failed to fetch data for {symbol}: {e}")
        return None

def main():
    client = load_client()
    if not client:
        print("Exiting due to missing client configuration.")
        return

    symbols_to_fetch = [
        {"symbol": "NIFTY", "exchange": "NSE"},
        {"symbol": "BANKNIFTY", "exchange": "NSE"},
        {"symbol": "SENSEX", "exchange": "BSE"},
    ]

    for item in symbols_to_fetch:
        collect_data(client, item["symbol"], item["exchange"], days=100)
        collect_data(client, item["symbol"], item["exchange"], timeframe=5)
        collect_data(client, item["symbol"], item["exchange"], timeframe=1) 

if __name__ == "__main__":
    main()
