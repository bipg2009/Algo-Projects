import os
import sys
import pandas as pd
import datetime

# Add research path to path
RESEARCH_DIR = os.path.dirname(os.path.abspath(__file__))
if RESEARCH_DIR not in sys.path:
    sys.path.insert(0, RESEARCH_DIR)

import Antigravity_Backtest as ab

def main():
    print("=" * 60)
    print("  ANTIGRAVITY OPTIMIZATION BACKTESTING RUNNER (JULY 2025)  ")
    print("=" * 60)
    
    # Generate July 2025 business days
    dates = pd.bdate_range(start="2025-07-01", end="2025-07-31")
    print(f"Generated {len(dates)} business days for July 2025.")
    
    all_trades = []
    summaries = []
    
    for i, date_obj in enumerate(dates):
        date_str = date_obj.strftime("%Y-%m-%d")
        print(f"\n[{i+1}/{len(dates)}] Processing Date: {date_str}...")
        try:
            trades, summary = ab.run_backtest(date_str, expiry_code=1, candle_mode="VOLUME")
            all_trades.extend(trades)
            summaries.append(summary)
        except Exception as e:
            print(f"Skipping {date_str} due to: {e}")
            
    print("\n" + "=" * 60)
    print("         ANTIGRAVITY STRATEGY CONSOLIDATED REPORT (JULY 2025)")
    print("=" * 60)
    
    if not all_trades:
        print("No trades triggered during July 2025.")
        return
        
    df_trades = pd.DataFrame(all_trades)
    df_trades.to_csv(os.path.join(RESEARCH_DIR, "Antigravity_July_Trades.csv"), index=False)
    print(f"Detailed trades saved to: {os.path.join(RESEARCH_DIR, 'Antigravity_July_Trades.csv')}")
    
    total = len(df_trades)
    wins = len(df_trades[df_trades["outcome"] == "Success"])
    losses = len(df_trades[df_trades["outcome"] == "Failure"])
    win_rate = round((wins / total) * 100, 2)
    avg_pnl = round(df_trades["pnl_pct"].mean(), 2)
    
    ce_trades = df_trades[df_trades["option_type"] == "CE"]
    pe_trades = df_trades[df_trades["option_type"] == "PE"]
    
    ce_total = len(ce_trades)
    ce_wins = len(ce_trades[ce_trades["outcome"] == "Success"])
    ce_win_rate = round((ce_wins / ce_total) * 100, 2) if ce_total else 0.0
    
    pe_total = len(pe_trades)
    pe_wins = len(pe_trades[pe_trades["outcome"] == "Success"])
    pe_win_rate = round((pe_wins / pe_total) * 100, 2) if pe_total else 0.0
    
    print(f"Total Trades        : {total}")
    print(f"Wins                : {wins}")
    print(f"Losses              : {losses}")
    print(f"Win Rate            : {win_rate}%")
    print(f"Average P&L         : {avg_pnl}%")
    print("-" * 40)
    print(f"Call (CE) Trades    : {ce_total} (Wins: {ce_wins}, Win Rate: {ce_win_rate}%)")
    print(f"Put (PE) Trades     : {pe_total} (Wins: {pe_wins}, Win Rate: {pe_win_rate}%)")
    print("=" * 60)

if __name__ == "__main__":
    main()
