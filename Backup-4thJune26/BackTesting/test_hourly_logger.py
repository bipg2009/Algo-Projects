from hourly_logger import HourlyTradeLogger
import datetime
import os

print("--- INITIALIZING SANDBOX MOCK LOGGER ---")
# Initialise in mock mode so it doesn't actually block/sleep on background thread
logger = HourlyTradeLogger(output_dir="Reports", mock_mode=True)

print("\n[Simulating trades between 09:15 and 10:00...]")

# 1. Signal generated but not executed (e.g. failed execution hurdle)
logger.log_signal() 

# 2. Signal generated and executed
logger.log_signal()
logger.log_execution("NIFTY 24 JAN 21500 CE", 130)

# 3. Another signal and execution, closed for profit
logger.log_signal()
logger.log_execution("NIFTY 24 JAN 21600 CE", 145)
logger.log_closed_trade(15.5)  # +15.5% profit

# 4. Another signal and execution, closed for loss
logger.log_signal()
logger.log_execution("NIFTY 24 JAN 21400 PE", 110)
logger.log_closed_trade(-5.2)  # -5.2% loss

print("\n[Simulating exact 10:00:00 rollover trigger...]")
# Pass the exact rollover time
mock_time = datetime.datetime(2026, 5, 10, 10, 0, 0)
logger.flush_hour(specific_time=mock_time)

print("\n[Simulating flat hour between 10:00 and 11:00 (Zero Trades)...]")
# Simulating a completely flat hour where no trades happened
mock_time_2 = datetime.datetime(2026, 5, 10, 11, 0, 0)
logger.flush_hour(specific_time=mock_time_2)

# Verify the CSV
date_str = mock_time.strftime("%Y-%m-%d")
filename = os.path.join("Reports", f"seda_hourly_paper_trades_{date_str}.csv")
print(f"\n--- VERIFYING GENERATED CSV: {filename} ---")

if os.path.exists(filename):
    with open(filename, 'r') as f:
        print(f.read())
else:
    print(f"[!] ERROR: File {filename} not found.")

# Clean up test file so it doesn't pollute the real Reports dir
try:
    os.remove(filename)
    print("\n[Cleanup] Test file removed successfully.")
except Exception:
    pass
