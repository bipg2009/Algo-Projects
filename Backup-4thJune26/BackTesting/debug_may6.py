import json
import pandas as pd
import sys
import os

# Append BackTesting to path so we can import modules
sys.path.insert(0, r'C:\Biplab\ALGO-Projects\Option-Scanner\BackTesting')
os.environ['IS_BACKTEST'] = '1'

import backtest_helpers as bh
import Option_strategy_core as core
import candle_transformer

# Load NIFTY 1m data for 2026-05-06
nifty_file = r'C:\Biplab\ALGO-Projects\Option-Scanner\BackTesting\Dependencies\backtest_cache\nifty_1m_2026-05-06.json'
try:
    nifty_1m = pd.read_json(nifty_file)
    print(f'Loaded Nifty: {len(nifty_1m)} rows')
except Exception as e:
    print('Failed to load Nifty', e)
    sys.exit(1)

# Just run a quick check on the bars
session_indices = [
    i for i in range(len(nifty_1m)) 
    if bh.is_within_session(nifty_1m.iloc[i]['start_Time'])
]
print(f'Session rows: {len(session_indices)}')

# We will just evaluate core.detect_trigger_1m using mock option row
for i in session_indices:
    df_slice = bh.prepare_nifty_1m(nifty_1m.iloc[: i + 1])
    # explain_trigger_failure requires (df_slice, 'CE')
    reason = core.explain_trigger_failure(df_slice, 'CE')
    if reason is None:
        print(f'Bar {i} ({bh.format_ist(nifty_1m.iloc[i]["start_Time"])}): SUCCESS! CE TRIGGER')
