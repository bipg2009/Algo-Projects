import time
import datetime
import pandas as pd
import SafetyLogger

class SystemHealthMonitor:
    def __init__(self, stale_timeout=60.0, startup_warmup=60.0):
        self.stale_timeout = stale_timeout
        self.startup_warmup = startup_warmup
        self.start_time = time.time()
        self.last_warn_time = 0.0
        self.current_stale_seconds = 0.0

    def update_and_check(self, df_1m):
        """
        Updates the internal candle tracker and returns True if healthy (trade allowed).
        Prints an alert if stale or warming up.
        """
        if df_1m is None or df_1m.empty:
            return False

        now = time.time()

        # Startup warmup
        if now - self.start_time < self.startup_warmup:
            return False

        # Validate candle updates
        try:
            current_time_val = str(df_1m.iloc[-1].get("start_Time", ""))
            if current_time_val:
                candle_time = pd.to_datetime(current_time_val)
                ist_tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
                now_ist = datetime.datetime.now(ist_tz)
                if candle_time.tzinfo is None:
                    candle_time = candle_time.tz_localize(ist_tz)
                
                # Check how old the candle's start_Time is compared to current IST clock
                # Note: a 1-minute candle completes 60s after its start_Time.
                self.current_stale_seconds = (now_ist - candle_time).total_seconds()
                
                # Stale logic: If the candle is older than timeframe block + tolerance
                # e.g., for 1m candle, it is fresh for 60s + stale_timeout
                stale_seconds_adj = max(0, self.current_stale_seconds - 60)
                
                if stale_seconds_adj > self.stale_timeout:
                    if now - self.last_warn_time > 30:
                        print(f"[!] HEARTBEAT ALERT: Data stale for {int(stale_seconds_adj)}s! Check Broker/Connection. Triggers disabled.", flush=True)
                        try:
                            from live_alert_logger import write_live_alert
                            write_live_alert("WARN", f"Data stale for {int(stale_seconds_adj)}s! Triggers blocked.")
                        except Exception as e:
                            pass
                        self.last_warn_time = now
                    return False
        except Exception as e:
            SafetyLogger.log_error_with_context("system_health", "update_and_check", e)

        return True

    def get_health_status(self):
        now = time.time()
        if now - self.start_time < self.startup_warmup:
            return f"Warming up ({int(self.startup_warmup - (now - self.start_time))}s left)"
            
        stale_seconds_adj = max(0, self.current_stale_seconds - 60)
        if stale_seconds_adj > self.stale_timeout:
            return f"STALE DATA ({int(stale_seconds_adj)}s)"
            
        return "Healthy"

system_health = SystemHealthMonitor(stale_timeout=60.0, startup_warmup=60.0)
