import pandas as pd

class CandleAggregator:
    """
    Takes 1m OHLCV data and reliably downsamples it to 3m and 5m timeframe groupings.
    This prevents needing multiple API/WebSocket calls for different timeframes
    and guarantees they are mathematically synchronized.
    """
    def __init__(self):
        pass
        
    @staticmethod
    def resample_1m_to_multi(df_1m: pd.DataFrame) -> dict:
        """
        Expects a pandas DataFrame with a datetime index or 'timestamp' column,
        and columns: open, high, low, close, volume.
        Returns a dictionary of dataframes for '1m', '3m', and '5m'.
        """
        if df_1m.empty:
            return {"1m": df_1m, "3m": pd.DataFrame(), "5m": pd.DataFrame()}

        # Protect original dataframe
        df = df_1m.copy()
        
        # Ensure we have a datetime index for the pandas resample function
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            time_col = 'timestamp'
        elif 'start_Time' in df.columns:
            df['start_Time'] = pd.to_datetime(df['start_Time'])
            df.set_index('start_Time', inplace=True)
            time_col = 'start_Time'
        elif not isinstance(df.index, pd.DatetimeIndex):
            try:
                df.index = pd.to_datetime(df.index)
            except Exception as e:
                print(f"Warning: Could not convert index to datetime. Resampling may fail. {e}")
                time_col = None
        else:
            time_col = None

        # Define how each column combines during an aggregation
        agg_dict = {
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }
        
        # If open interest is in the dataframe, take the latest reading
        if 'oi' in df.columns:
            agg_dict['oi'] = 'last'
        
        # Fallback for any other columns (e.g. metadata, symbol names)
        for col in df.columns:
            if col not in agg_dict:
                agg_dict[col] = 'last'

        try:
            # Re-group by 3-minute, 5-minute, and 10-minute boundaries
            # closed='left' and label='left' are standard conventions for financial time series
            df_3m = df.resample('3T', closed='left', label='left').agg(agg_dict).dropna()
            df_5m = df.resample('5T', closed='left', label='left').agg(agg_dict).dropna()
            df_10m = df.resample('10T', closed='left', label='left').agg(agg_dict).dropna()
        except Exception as e:
            print(f"Error resampling timeframe: {e}")
            df_3m, df_5m, df_10m = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

        # Reset the index back to a column if it started as one
        if time_col is not None:
            df.reset_index(inplace=True)
            df_3m.reset_index(inplace=True)
            df_5m.reset_index(inplace=True)
            df_10m.reset_index(inplace=True)

        return {
            "1m": df,
            "3m": df_3m,
            "5m": df_5m,
            "10m": df_10m
        }
