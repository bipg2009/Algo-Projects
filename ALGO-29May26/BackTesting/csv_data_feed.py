import pandas as pd
import time
from typing import Generator, Dict, Any

class CSVDataFeed:
    """
    Simulates a live market data feed by replaying historical CSV data.
    """
    def __init__(self, filepath: str, symbol: str, interval_sec: float = 0.0):
        self.filepath = filepath
        self.symbol = symbol
        self.interval_sec = interval_sec  # Sleep time between ticks during replay
        
    def load_data(self) -> pd.DataFrame:
        try:
            df = pd.read_csv(self.filepath)
            # Ensure index or 'timestamp' columns are handled correctly
            if 'timestamp' in df.columns or 'start_Time' in df.columns:
                time_col = 'timestamp' if 'timestamp' in df.columns else 'start_Time'
                df[time_col] = pd.to_datetime(df[time_col])
                df.sort_values(by=time_col, inplace=True)
            return df
        except Exception as e:
            print(f"Failed to load CSV data for {self.symbol}: {e}")
            return pd.DataFrame()

    def replay(self) -> Generator[Dict[str, Any], None, None]:
        """
        Yields row by row like a tick feed, formatted similarly to Dhan WebSocket quotes.
        """
        df = self.load_data()
        for idx, row in df.iterrows():
            if self.interval_sec > 0:
                time.sleep(self.interval_sec)
                
            # Simulated Quote/Tick structure
            tick = {
                "type": "Quote",
                "symbol": self.symbol,
                "LTP": row.get("close", 0.0),
                "open": row.get("open", 0.0),
                "high": row.get("high", 0.0),
                "low": row.get("low", 0.0),
                "volume": row.get("volume", 0),
                "timestamp": row.get("timestamp", row.get("start_Time", ""))
            }
            yield tick
