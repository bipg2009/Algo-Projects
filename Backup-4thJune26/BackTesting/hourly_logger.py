import threading
import time
import datetime
import csv
import os

class HourlyTradeLogger:
    """
    Asynchronous Hourly Trade Logger for SEDA.
    Tracks paper trade execution metrics in-memory and flushes to a CSV file 
    at the exact top of every hour without blocking the main trading engine.
    """
    def __init__(self, output_dir="Reports", mock_mode=False):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.mock_mode = mock_mode
        self.lock = threading.Lock()
        
        # In-memory tracking
        self.signals_generated = 0
        self.trades_executed = 0
        self.cumulative_score = 0.0
        self.cumulative_pnl = 0.0
        self.closed_trades_count = 0
        self.symbols = set()
        
        # In production mode, start the daemon thread
        if not self.mock_mode:
            self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
            self.thread.start()

    def log_signal(self):
        """Called whenever a SEDA signal is triggered, even if not executed."""
        with self.lock:
            self.signals_generated += 1

    def log_execution(self, symbol, score):
        """Called when a paper trade is actually executed."""
        with self.lock:
            self.trades_executed += 1
            self.cumulative_score += score
            self.symbols.add(symbol)

    def log_closed_trade(self, pnl_pct):
        """
        Called when a paper trade is closed. 
        Logs the realised PnL into the current hourly bucket.
        """
        with self.lock:
            self.closed_trades_count += 1
            self.cumulative_pnl += pnl_pct

    def flush_hour(self, specific_time=None):
        """Flushes the current hour's data to CSV and resets counters instantly."""
        with self.lock:
            dt = specific_time if specific_time else datetime.datetime.now()
            
            # If called precisely at the top of the hour (e.g., 10:00:00), 
            # the data technically belongs to the 09:00-10:00 bucket.
            bucket_dt = dt - datetime.timedelta(seconds=1)
            hour_start = bucket_dt.replace(minute=0, second=0, microsecond=0)
            hour_end = hour_start + datetime.timedelta(hours=1)
            
            hour_str = f"{hour_start.strftime('%H:%M')}-{hour_end.strftime('%H:%M')}"
            date_str = bucket_dt.strftime("%Y-%m-%d")
            
            filename = os.path.join(self.output_dir, f"seda_hourly_paper_trades_{date_str}.csv")
            
            avg_score = round(self.cumulative_score / self.trades_executed, 2) if self.trades_executed > 0 else 0.0
            pnl_total = round(self.cumulative_pnl, 2)
            
            symbols_str = " | ".join(sorted(self.symbols)) if self.symbols else "NONE"
            signals_str = f"{self.signals_generated}/{self.trades_executed}"
            
            row = {
                "Timestamp_Hour": hour_str,
                "Symbol": symbols_str,
                "Total_Trades_Executed": self.trades_executed,
                "SEDA_Average_Score": avg_score,
                "Hourly_Buy_Signals_Generated_vs_Executed": signals_str,
                "Net_Paper_PnL_Pct": pnl_total
            }
            
            # Instantly reset counters for the next hour to ensure zero latency
            self.signals_generated = 0
            self.trades_executed = 0
            self.cumulative_score = 0.0
            self.cumulative_pnl = 0.0
            self.closed_trades_count = 0
            self.symbols.clear()
            
        # Perform disk I/O outside the lock (but technically still in the daemon thread)
        # to ensure we don't accidentally block the main thread if it tries to log a trade 
        # exactly when the disk write is happening.
        file_exists = os.path.exists(filename)
        try:
            with open(filename, 'a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=row.keys())
                if not file_exists:
                    writer.writeheader()
                writer.writerow(row)
        except Exception as e:
            try:
                from scanner_excel import hourly_log
                hourly_log.log("ERROR", option_type="LOGGER", rsi=0, trend="N/A", reject_reason=f"CSV Write Failed: {e}", notes="")
            except Exception:
                pass
            print(f"[HourlyLogger] Failed to write CSV: {e}", flush=True)

    def _run_scheduler(self):
        """Background thread loop that sleeps until the exact top of the next hour."""
        while True:
            now = datetime.datetime.now()
            next_hour = (now + datetime.timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
            sleep_sec = (next_hour - now).total_seconds()
            
            # Failsafe: Prevent instant tight looping if microsecond precision causes a glitch
            if sleep_sec <= 0:
                sleep_sec = 3600
                
            time.sleep(sleep_sec)
            self.flush_hour(datetime.datetime.now())

# Global singleton for easy import across modules
hourly_logger = HourlyTradeLogger(mock_mode=False)
