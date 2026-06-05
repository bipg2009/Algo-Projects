import pandas as pd
import numpy as np
import datetime
import sys

try:
    from logging_engine import print_heartbeat
except Exception as e:
    print(f"Import Error: {e}")
    sys.exit(1)

# Mock Data
now = datetime.datetime.now()
dates = [now - datetime.timedelta(minutes=i) for i in range(100, 0, -1)]

# Create a sample 1m dataframe with required columns
df_1m = pd.DataFrame({
    'timestamp': dates,
    'open': np.linspace(23000, 23100, 100),
    'high': np.linspace(23010, 23110, 100),
    'low': np.linspace(22990, 23090, 100),
    'close': np.linspace(23005, 23105, 100),
    'volume': np.random.randint(1000, 5000, 100)
})

# Add indicator logic required for SEDA
# indicator_engine handles indicators, let's add mock columns
df_1m['st_color'] = 'GREEN'
df_1m['RSI'] = 65.0
df_1m['RSI_14'] = 65.0
df_1m['EMA9'] = df_1m['close']
df_1m['EMA20'] = df_1m['close'] - 10
df_1m['VWAP'] = df_1m['close'] - 5
df_1m['ADX'] = 25.0

chain = {'spot': 23100, 'atm': 23100, 'pcr': 1.2}
valid_options = [{'strike': 23100, 'symbol': 'NIFTY25JUN23100CE', 'ltp': 120}]

print("Running SEDA Test Heartbeat...")
try:
    print_heartbeat(df_1m, chain, "CE", valid_options, trigger_found=False, pcr_val=1.2)
    print("SEDA Heartbeat completed without crashing!")
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"SEDA Test Failed: {e}")
