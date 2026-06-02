import time
import datetime

class SystemHealthMonitor:
    def __init__(self, stale_timeout=60.0, startup_warmup=60.0):
        self.stale_timeout = stale_timeout
        self.startup_warmup = startup_warmup
        self.start_time = time.time()
        self.last_candle_time_val = None
        self.last_candle_update_ts = time.time()
        self.last_warn_time = 0.0

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
            
            # If the candle timestamp changed, we update our freshness tracker
            if current_time_val != self.last_candle_time_val:
                self.last_candle_time_val = current_time_val
                self.last_candle_update_ts = now
            
            stale_seconds = now - self.last_candle_update_ts
            if stale_seconds > self.stale_timeout:
                if now - self.last_warn_time > 30:
                    print(f"[!] HEARTBEAT ALERT: Data stale for {int(stale_seconds)}s! Check Broker/Connection. Triggers disabled.", flush=True)
                    try:
                        from live_alert_logger import write_live_alert
                        write_live_alert("WARN", f"Data stale for {int(stale_seconds)}s! Triggers blocked.")
                    except: pass
                    self.last_warn_time = now
                return False
                
        except Exception:
            pass

        return True

    def get_health_status(self):
        now = time.time()
        if now - self.start_time < self.startup_warmup:
            return f"Warming up ({int(self.startup_warmup - (now - self.start_time))}s left)"
            
        stale_seconds = now - self.last_candle_update_ts
        if stale_seconds > self.stale_timeout:
            return f"STALE DATA ({int(stale_seconds)}s)"
            
        return "Healthy"

system_health = SystemHealthMonitor(stale_timeout=60.0, startup_warmup=60.0)
