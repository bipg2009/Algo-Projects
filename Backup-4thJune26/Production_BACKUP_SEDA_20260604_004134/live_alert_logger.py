import os
import datetime

LOG_FILE = "live_alerts.log"

def write_live_alert(tag, msg):
    """Writes an alert directly to the live_alerts.log file so the popup picks it up."""
    try:
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] [{tag.upper()}] {msg}\n"
        with open(LOG_FILE, 'a') as f:
            f.write(line)
    except Exception:
        pass
