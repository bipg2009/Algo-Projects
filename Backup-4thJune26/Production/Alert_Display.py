import time
import os
import sys
import datetime

def get_today_log_file():
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    return os.path.join("Dependencies", f"oi_volume_alerts_{today}.csv")

def main():
    if os.name == 'nt':
        os.system('title ALERTS AND VOLUME MONITOR')
    print("="*60)
    print("            LIVE ALERTS AND VOLUME MONITOR")
    print("="*60)
    
    log_file = get_today_log_file()
    print(f"Waiting for alerts on: {log_file}\n")

    while not os.path.exists(log_file):
        time.sleep(1)
            
    with open(log_file, 'r') as f:
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

