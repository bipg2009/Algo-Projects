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
    fails = df[df['outcome'] == 'Failure'].copy()
    print('Total Failures:', len(fails))
    
    # Calculate P&L if available
    if 'pnl_pct' in fails.columns:
        print("\nFailure P&L % stats:")
        print(fails['pnl_pct'].describe())
    
    if 'max_profit_pct' in fails.columns:
        print("\nFailure Max Profit % reached before SL:")
        print(fails['max_profit_pct'].describe())
        
    print("\nFailure durations (minutes):")
    if 'duration_min' in fails.columns:
        print(fails['duration_min'].describe())
        
    # Check if there's any trend in exit_reason for failures specifically
    print("\nFailure Exit Reasons:")
    print(fails['exit_reason'].value_counts())
    
    # Show the 5 worst failures
    print("\nWorst 5 failures by PNL:")
    if 'pnl_pct' in fails.columns:
        worst = fails.sort_values('pnl_pct').head(5)
        cols = [c for c in ['test_date', 'symbol', 'entry_time', 'exit_time', 'entry_price', 'exit_price', 'pnl_pct', 'max_profit_pct'] if c in worst.columns]
        print(worst[cols])
