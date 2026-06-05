import time
import os
import sys

LOG_FILE = "live_alerts.log"

def main():
    if os.name == 'nt':
        os.system('title ALERTS AND VOLUME MONITOR')
    print("="*60)
    print("            LIVE ALERTS AND VOLUME MONITOR")
    print("="*60)
    print("Waiting for alerts...\n")

    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'w') as f:
            pass
            
    with open(LOG_FILE, 'r') as f:
        # Start trailing from the beginning
        while True:
            line = f.readline()
            if line:
                sys.stdout.write(line)
                sys.stdout.flush()
            else:
                time.sleep(0.5)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass

