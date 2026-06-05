import sys

path = 'NSE-Option-Scanner-Backtest.py'
with open(path, 'r') as f:
    c = f.read()

c = c.replace(
    'OPTION_BAR_TF = 5  # Dhan option history bars (LTP only; NIFTY setup/trigger use 1m)',
    'OPTION_BAR_TF = 5\nNIFTY_BAR_TF = 3'
)
c = c.replace(
    'def option_bar_idx(minute_idx):\n    """Map 1m index to option bar index (option data is 5m)."""\n    return minute_idx // OPTION_BAR_TF',
    'def option_bar_idx(minute_idx):\n    return (minute_idx * NIFTY_BAR_TF) // OPTION_BAR_TF'
)
c = c.replace(
    '    nifty_1m = fetch_nifty_bars(sc.tsl, test_date, 1)',
    '''    nifty_1m = fetch_nifty_bars(sc.tsl, test_date, 1)
    
    # Resample to NIFTY_BAR_TF
    import pandas as pd
    nifty_1m["start_Time"] = pd.to_datetime(nifty_1m["start_Time"])
    nifty_1m.set_index("start_Time", inplace=True)
    nifty_1m = nifty_1m.resample(f"{NIFTY_BAR_TF}min").agg({
        "open": "first", "high": "max", "low": "min", "close": "last", 
        "volume": "sum", "start_Time_ist": "first"
    }).dropna()
    nifty_1m.reset_index(inplace=True)'''
)
c = c.replace(
    'legs = align_legs(fetch_option_legs(sc.tsl, test_date, expiry_code), len(nifty_1m) // OPTION_BAR_TF + 1)',
    'legs = align_legs(fetch_option_legs(sc.tsl, test_date, expiry_code), (len(nifty_1m) * NIFTY_BAR_TF) // OPTION_BAR_TF + 1)'
)

with open(path, 'w') as f:
    f.write(c)
print('Patched successfully with local resampling!')
