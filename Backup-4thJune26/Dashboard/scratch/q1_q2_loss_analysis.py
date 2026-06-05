import os
import glob
import pandas as pd

def analyze_losses():
    results_dir = r"c:\Biplab\ALGO-Projects\Option-Scanner\Dependencies\backtest_results"
    trade_files = glob.glob(os.path.join(results_dir, "backtest_trades_*.csv"))
    
    all_trades = []
    
    for f in trade_files:
        try:
            df = pd.read_csv(f)
            if df.empty:
                continue
            all_trades.append(df)
        except Exception:
            continue
            
    if not all_trades:
        print("No trade files found.")
        return
        
    df_all = pd.concat(all_trades, ignore_index=True)
    
    # Ensure correct data types
    df_all["test_date"] = pd.to_datetime(df_all["test_date"], format="mixed")
    df_all["pnl_pct"] = pd.to_numeric(df_all["pnl_pct"], errors="coerce")
    df_all["entry_ltp"] = pd.to_numeric(df_all["entry_ltp"], errors="coerce")
    df_all["exit_ltp"] = pd.to_numeric(df_all["exit_ltp"], errors="coerce")
    
    # Filter for Q1 and Q2 2025 (Jan 1, 2025 to June 30, 2025)
    start_q1 = pd.to_datetime("2025-01-01")
    end_q2 = pd.to_datetime("2025-06-30")
    
    df_period = df_all[(df_all["test_date"] >= start_q1) & (df_all["test_date"] <= end_q2)].copy()
    
    # Calculate absolute rupee loss (assuming 1 lot = 75 qty for NIFTY)
    df_period["pnl_pts"] = df_period["exit_ltp"] - df_period["entry_ltp"]
    df_period["pnl_rupees"] = df_period["pnl_pts"] * 75
    
    # Filter for losing trades and sort by highest loss first (most negative pnl_pct or pnl_rupees)
    df_losses = df_period[df_period["pnl_pct"] < 0].copy()
    
    # Sort by pnl_pct ascending (so biggest negative percentage is first)
    df_losses_sorted = df_losses.sort_values(by="pnl_pct", ascending=True)
    
    print(f"Total Q1/Q2 Losing Trades Loaded: {len(df_losses_sorted)}")
    
    # Take top 15 biggest losses
    top_losses = df_losses_sorted.head(15)
    
    report_rows = []
    for idx, row in top_losses.iterrows():
        date_str = row["test_date"].strftime("%d-%b-%Y")
        
        # Determine likely cause / remark based on data
        reason = str(row.get("exit_reason", "STOP_LOSS")).upper()
        pnl_val = row["pnl_pct"]
        entry_ltp = row["entry_ltp"]
        exit_ltp = row["exit_ltp"]
        
        remark = ""
        if "TIME" in reason or "DECAY" in reason:
            remark = "EOD Time Decay cutoff hit; trade held to market close without catching a trend."
        elif "STOP_LOSS" in reason or "SL" in reason:
            if abs(pnl_val + 20.0) < 1.0 or abs(exit_ltp - (entry_ltp * 0.80)) < 2.0:
                remark = "Hit direct 20% Option Premium Stop Loss. Severe counter-trend market reversal."
            else:
                remark = "Hit dynamic Spot-ATR trailing stop loss after a brief trend pullback failed."
        else:
            remark = f"Exited due to {reason}."
            
        report_rows.append({
            "Instrument": f"{row['symbol']} {row['strike']} {row['option_type']}",
            "Date": date_str,
            "Entry_Time": row["entry_time_ist"],
            "Exit_Time": row["exit_time_ist"],
            "Entry_LTP": entry_ltp,
            "Exit_LTP": exit_ltp,
            "PnL_Pct": f"{pnl_val:.2f}%",
            "PnL_Rupees": f"INR {row['pnl_rupees']:.2f}",
            "Remark": remark
        })
        
    df_report = pd.DataFrame(report_rows)
    print("\nTOP 15 BIGGEST LOSERS IN Q1/Q2:")
    print(df_report.to_string(index=False))
    
    # Save report to csv and excel
    df_report.to_csv(os.path.join(results_dir, "Q1_Q2_Biggest_Losers_Report.csv"), index=False)
    print(f"\nReport saved to: {os.path.join(results_dir, 'Q1_Q2_Biggest_Losers_Report.csv')}")
    
    try:
        excel_filename = "Q1_Q2_Biggest_Losers_Report_DD_MMM_YYYY.xlsx"
        df_report.to_excel(os.path.join(results_dir, excel_filename), index=False)
        print(f"Excel report successfully saved to: {os.path.join(results_dir, excel_filename)}")
    except Exception as e:
        print(f"Could not save Excel file (openpyxl might be missing): {e}")

if __name__ == "__main__":
    analyze_losses()
