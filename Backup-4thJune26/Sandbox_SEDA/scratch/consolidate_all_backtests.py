import os
import glob
import re
import pandas as pd
import datetime

RESULTS_DIR = r"c:\Biplab\ALGO-Projects\Option-Scanner\Dependencies\backtest_results"

def parse_date(date_str):
    """Parses date string of format DD-MM-YY or DD-MM-YYYY."""
    for fmt in ("%d-%m-%y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None

def get_quarter(dt):
    """Returns Q1, Q2, Q3, or Q4 based on date month."""
    if dt.month in (1, 2, 3):
        return "Q1"
    elif dt.month in (4, 5, 6):
        return "Q2"
    elif dt.month in (7, 8, 9):
        return "Q3"
    else:
        return "Q4"

def main():
    print("=" * 60)
    print("CONSOLIDATING BACKTEST REPORTS")
    print("=" * 60)
    
    pattern = os.path.join(RESULTS_DIR, "backtest_trades_*.csv")
    files = glob.glob(pattern)
    print(f"Found {len(files)} trade CSV files in results directory.")
    
    all_trades = []
    seen_trade_signatures = set()
    duplicate_count = 0
    
    for f in files:
        # Extract date from filename, e.g., backtest_trades_06-11-25.csv
        filename = os.path.basename(f)
        match = re.search(r"backtest_trades_([\d\-]+)", filename)
        if not match:
            continue
            
        date_str = match.group(1)
        dt = parse_date(date_str)
        if not dt:
            continue
            
        # Ignore years outside 2025 to keep report focused on 2025 Q1, Q2, Q3
        if dt.year != 2025:
            continue
            
        try:
            df = pd.read_csv(f)
            if df.empty:
                continue
                
            for _, row in df.iterrows():
                # Extract key fields
                symbol = row.get("symbol", "")
                option_type = row.get("option_type", "")
                entry_time = row.get("entry_time_ist", "")
                pnl = row.get("pnl_pct", 0.0)
                outcome = row.get("outcome", "")
                
                # Coerce numeric outcome or string
                outcome_str = str(outcome).strip().lower()
                if "success" in outcome_str:
                    clean_outcome = "Success"
                elif "failure" in outcome_str:
                    clean_outcome = "Failure"
                else:
                    clean_outcome = "Success" if float(pnl) > 0 else "Failure"
                
                # Check for duplicate trade of the same date, symbol, entry_time
                sig = (dt.strftime("%Y-%m-%d"), str(symbol), str(entry_time))
                if sig in seen_trade_signatures:
                    duplicate_count += 1
                    continue
                    
                seen_trade_signatures.add(sig)
                
                trade_dict = {
                    "date": dt.strftime("%Y-%m-%d"),
                    "quarter": get_quarter(dt),
                    "symbol": symbol,
                    "option_type": option_type,
                    "strike": row.get("strike", ""),
                    "score_pct": row.get("score_pct", 0.0),
                    "entry_time_ist": entry_time,
                    "exit_time_ist": row.get("exit_time_ist", ""),
                    "entry_ltp": row.get("entry_ltp", 0.0),
                    "exit_ltp": row.get("exit_ltp", 0.0),
                    "pnl_pct": float(pnl),
                    "outcome": clean_outcome,
                    "exit_reason": row.get("exit_reason", "")
                }
                all_trades.append(trade_dict)
        except Exception as e:
            print(f"Error parsing {filename}: {e}")
            
    print(f"Successfully loaded {len(all_trades)} unique trades.")
    print(f"Removed {duplicate_count} duplicate trade rows.")
    
    if not all_trades:
        print("No unique trades found for 2025.")
        return
        
    df_master = pd.DataFrame(all_trades)
    master_path = os.path.join(RESULTS_DIR, "Consolidated_All_Trades_Master.csv")
    df_master.to_csv(master_path, index=False)
    print(f"\nSaved consolidated duplicate-free master trade sheet to: {master_path}")
    
    # Calculate performance metrics overall and by quarter
    quarters = ["Q1", "Q2", "Q3", "All together"]
    summary_rows = []
    
    for q in quarters:
        if q == "All together":
            df_q = df_master
        else:
            df_q = df_master[df_master["quarter"] == q]
            
        if df_q.empty:
            summary_rows.append({
                "Period": q, "Total_Trades": 0, "Wins": 0, "Losses": 0,
                "Win_Rate_Pct": 0.0, "Avg_PnL_Pct": 0.0
            })
            continue
            
        total = len(df_q)
        wins = len(df_q[df_q["outcome"] == "Success"])
        losses = len(df_q[df_q["outcome"] == "Failure"])
        win_rate = round((wins / total) * 100, 2)
        avg_pnl = round(df_q["pnl_pct"].mean(), 2)
        
        summary_rows.append({
            "Period": q,
            "Total_Trades": total,
            "Wins": wins,
            "Losses": losses,
            "Win_Rate_Pct": win_rate,
            "Avg_PnL_Pct": avg_pnl
        })
        
    df_summary = pd.DataFrame(summary_rows)
    summary_path = os.path.join(RESULTS_DIR, "Consolidated_Quarters_Summary.csv")
    df_summary.to_csv(summary_path, index=False)
    print(f"Saved consolidated quarters summary to: {summary_path}")
    
    print("\n" + "=" * 60)
    print("         CONSOLIDATED PERFORMANCE SUMMARY (2025)")
    print("=" * 60)
    print(df_summary.to_string(index=False))
    print("=" * 60)

if __name__ == "__main__":
    main()
