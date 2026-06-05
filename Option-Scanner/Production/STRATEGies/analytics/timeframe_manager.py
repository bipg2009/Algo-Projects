import pandas as pd

class CandleAggregator:
    @staticmethod
    def resample_1m_to_multi(df_1m: pd.DataFrame) -> dict:
        if df_1m is None or df_1m.empty:
            return {"3m": pd.DataFrame(), "5m": pd.DataFrame(), "10m": pd.DataFrame()}
            
        df = df_1m.copy()
        if 'start_Time' in df.columns:
            df['datetime'] = pd.to_datetime(df['start_Time'])
            df.set_index('datetime', inplace=True)
        elif 'timestamp' in df.columns:
            df['datetime'] = pd.to_datetime(df['timestamp'])
            df.set_index('datetime', inplace=True)
        
        ohlcv_dict = {}
        if 'open' in df.columns: ohlcv_dict['open'] = 'first'
        if 'high' in df.columns: ohlcv_dict['high'] = 'max'
        if 'low' in df.columns: ohlcv_dict['low'] = 'min'
        if 'close' in df.columns: ohlcv_dict['close'] = 'last'
        if 'volume' in df.columns: ohlcv_dict['volume'] = 'sum'
        
        try:
            df_3m = df.resample('3min').agg(ohlcv_dict).dropna()
            df_5m = df.resample('5min').agg(ohlcv_dict).dropna()
            df_10m = df.resample('10min').agg(ohlcv_dict).dropna()
        except Exception as e:
            print(f"CandleAggregator Error: {e}", flush=True)
            return {"3m": pd.DataFrame(), "5m": pd.DataFrame(), "10m": pd.DataFrame()}

        return {"3m": df_3m, "5m": df_5m, "10m": df_10m}
