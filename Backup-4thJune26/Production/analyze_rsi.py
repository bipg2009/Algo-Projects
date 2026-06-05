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

max_profits = []
for idx, row in trades.iterrows():
    date = row['date']
    sym = row['symbol']
    entry_p = row['entry_ltp']
    monitor_file = f'Dependencies/backtest_results/backtest_monitor_{date}.csv'
    
    if os.path.exists(monitor_file) and os.path.getsize(monitor_file) > 10:
        try:
            mon_df = pd.read_csv(monitor_file)
            trade_mon = mon_df[mon_df['symbol'] == sym]
            if not trade_mon.empty and 'option_ltp' in trade_mon.columns and 'rsi_1m' in trade_mon.columns:
                max_ltp = trade_mon['option_ltp'].max()
                max_p = ((max_ltp - entry_p) / entry_p) * 100.0
                entry_rsi = trade_mon.iloc[0]['rsi_1m']
                
                max_profits.append({
                    'symbol': sym, 'date': date, 'outcome': row['outcome'],
                    'max_profit': max_p, 'final_pnl': row['pnl_pct'], 
                    'entry_rsi': entry_rsi, 'option_type': row['option_type']
                })
        except:
            pass

if max_profits:
    res = pd.DataFrame(max_profits)
    failures = res[res['outcome'] == 'Failure']
    
    print("=== FAILURES ===")
    print("CE Failures average entry RSI:", failures[failures['option_type']=='CE']['entry_rsi'].mean())
    print("PE Failures average entry RSI:", failures[failures['option_type']=='PE']['entry_rsi'].mean())
    print("\nPE Failures with RSI < 30:")
    print(failures[(failures['option_type']=='PE') & (failures['entry_rsi'] < 30)][['symbol', 'entry_rsi', 'max_profit', 'final_pnl']])
    
    print("\nCE Failures with RSI > 70:")
    print(failures[(failures['option_type']=='CE') & (failures['entry_rsi'] > 70)][['symbol', 'entry_rsi', 'max_profit', 'final_pnl']])

    print("\n=== SUCCESSES ===")
    successes = res[res['outcome'] == 'Success']
    print("CE Successes average entry RSI:", successes[successes['option_type']=='CE']['entry_rsi'].mean())
    print("PE Successes average entry RSI:", successes[successes['option_type']=='PE']['entry_rsi'].mean())
