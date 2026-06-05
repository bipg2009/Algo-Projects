import pandas as pd
import glob
import os

files = glob.glob('Dependencies/backtest_results/backtest_trades_*.csv')
valid_dfs = []
for f in files:
    if os.path.getsize(f) > 10:
        try: 
            df = pd.read_csv(f)
            if not df.empty:
                valid_dfs.append(df)
        except Exception as e:
            pass

if valid_dfs:
    df = pd.concat(valid_dfs)
    print('Total trades:', len(df))
    print('Win rate:', (df['outcome']=='Success').mean() * 100, '%')
    print('\nExit Reasons:')
    print(df['exit_reason'].value_counts())
    
    print('\nOutcome by Type:')
    print(df.groupby('option_type')['outcome'].value_counts())
else:
    print('No trades found')
