import os
import sys

# Append root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from BackTesting.csv_data_feed import CSVDataFeed
from indicator_engine import IndicatorEngine

class BacktestEngine:
    def __init__(self, data_file: str, symbol: str):
        self.data_file = data_file
        self.symbol = symbol
        self.feed = CSVDataFeed(filepath=data_file, symbol=symbol, interval_sec=0)
        self.indicator_engine = IndicatorEngine()
        
    def start(self):
        print("========================")
        print(f"Starting Backtest on {self.symbol}")
        print("========================")
        
        replay_gen = self.feed.replay()
        row_count = 0
        for tick in replay_gen:
            row_count += 1
            ltp = tick.get("LTP")
            ts = tick.get("timestamp")
            
            # Feed LTP to indicator engine
            self.indicator_engine.update_price(self.symbol, ltp)
            
            # We can run Chop_Mode, Price_Check etc here at the end of each tick
            # Check conditions periodically
            if row_count % 50 == 0:
                print(f"[{ts}] {self.symbol} LTP: {ltp} | Analyzing...")
                
        print("========================")
        print(f"Backtest Completed. Processed {row_count} ticks.")
        print("========================")

if __name__ == "__main__":
    # Example usage
    sample_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "NIFTY_NSE_5min.csv")
    if os.path.exists(sample_file):
        engine = BacktestEngine(sample_file, "NIFTY")
        engine.start()
    else:
        print("No sample data found. Please run data_collector.py first.")
