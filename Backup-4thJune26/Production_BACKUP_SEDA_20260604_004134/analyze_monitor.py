import pandas as pd
import glob
import os

trades_files = glob.glob('Dependencies/backtest_results/backtest_trades_*.csv')
valid_dfs = []
for f in trades_files:
    if os.path.getsize(f) > 10:
        try: 
            df = pd.read_csv(f)
            if not df.empty:
                df['date'] = f.split('_')[-1].replace('.csv', '')
                valid_dfs.append(df)
        except Exception as e:
            pass

if not valid_dfs:
    print("No trades")
    exit()
    
trades = pd.concat(valid_dfs)
failures = trades[trades['outcome'] == 'Failure']

print(f"Analyzing {len(failures)} failures...")

max_profits = []
for idx, row in failures.iterrows():
    date = row['date']
    sym = row['symbol']
    entry_p = row['entry_ltp']
    monitor_file = f'Dependencies/backtest_results/backtest_monitor_{date}.csv'
    
    if os.path.exists(monitor_file) and os.path.getsize(monitor_file) > 10:
        try:
            mon_df = pd.read_csv(monitor_file)
            trade_mon = mon_df[mon_df['symbol'] == sym]
            if not trade_mon.empty and 'option_ltp' in trade_mon.columns:
                max_ltp = trade_mon['option_ltp'].max()
                max_p = ((max_ltp - entry_p) / entry_p) * 100.0
                max_profits.append({'symbol': sym, 'date': date, 'max_profit': max_p, 'final_pnl': row['pnl_pct'], 'entry': entry_p, 'max_ltp': max_ltp})
        except:
            pass

if max_profits:
    res = pd.DataFrame(max_profits)
    print("\nDid the failures ever go into profit before hitting stop loss?")
    print(res['max_profit'].describe())
    
    never_profit = res[res['max_profit'] <= 0]
    small_profit = res[(res['max_profit'] > 0) & (res['max_profit'] < 5)]
    med_profit = res[(res['max_profit'] >= 5) & (res['max_profit'] < 10)]
    high_profit = res[res['max_profit'] >= 10]
    
    print(f"\nNever went into profit: {len(never_profit)} trades")
    print(f"Went into small profit (<5%): {len(small_profit)} trades")
    print(f"Went into medium profit (5-10%): {len(med_profit)} trades")
    print(f"Went into high profit (>10%): {len(high_profit)} trades")
    
    if not high_profit.empty:
        print("\nThese went >10% in profit but still ended as Failures:")
        print(high_profit)
