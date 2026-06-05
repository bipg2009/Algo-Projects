import os
import sys
import pandas as pd
import importlib.util
import traceback

# Force backtest environment flag
os.environ["IS_BACKTEST"] = "1"

def load_backtest_module():
    file_path = os.path.join(os.path.dirname(__file__), "NSE-Option-Scanner-Backtest.py")
    spec = importlib.util.spec_from_file_location("backtest_engine", file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["backtest_engine"] = module
    spec.loader.exec_module(module)
    return module

def run_multiday(start_date, end_date, expiry_code=1):
    print("=" * 60)
    print(f"MULTI-DAY BACKTEST RUNNER: {start_date} to {end_date}")
    print("=" * 60)
    
    # Generate business days (Mon-Fri)
    dates = pd.bdate_range(start=pd.to_datetime(start_date, dayfirst=True), 
                           end=pd.to_datetime(end_date, dayfirst=True))
    
    backtest_engine = load_backtest_module()
    
    modes = ["NORMAL", "HEIKIN_ASHI", "VOLUME"]
    
    # Initialize trackers
    mode_summaries = {m: [] for m in modes}
    mode_trades = {m: [] for m in modes}
    
    for i, date_obj in enumerate(dates):
        date_str = date_obj.strftime("%Y-%m-%d")
        print(f"\n[{i+1}/{len(dates)}] Synchronizing Date: {date_str}...")
        
        temp_summaries = {}
        temp_trades = {}
        day_failed = False
        
        # Test all modes for the date. If any mode raises an exception (Dhan API rate limit / no data),
        # we skip the day for all modes to ensure perfect date synchronization.
        for mode in modes:
            try:
                trades, summary = backtest_engine.run_backtest(date_str, expiry_code, candle_mode=mode)
                temp_summaries[mode] = summary
                temp_trades[mode] = trades
            except Exception as e:
                print(f"Skipping date {date_str} across all modes due to error in {mode}: {e}")
                day_failed = True
                break
                
        if not day_failed:
            for mode in modes:
                mode_summaries[mode].append(temp_summaries[mode])
                mode_trades[mode].extend(temp_trades[mode])

    comparative_results = []
    
    for mode in modes:
        all_summaries = mode_summaries[mode]
        all_trades = mode_trades[mode]
        
        if not all_summaries:
            print(f"\nNo successful backtest runs for mode {mode}.")
            continue

        # Aggregate results
        df_results = pd.DataFrame(all_summaries)
        
        total_days = len(df_results)
        total_trades = df_results['total_trades'].sum()
        total_success = df_results['success'].sum()
        total_failure = df_results['failure'].sum()
        
        win_rate = round((total_success / total_trades) * 100, 2) if total_trades > 0 else 0
        avg_pnl = round(df_results['avg_pnl_pct'].mean(), 2) if total_trades > 0 else 0
        
        # Calculate CE and PE breakdowns
        ce_trades = [t for t in all_trades if t.get("option_type") == "CE"]
        pe_trades = [t for t in all_trades if t.get("option_type") == "PE"]
        
        ce_total = len(ce_trades)
        ce_wins = len([t for t in ce_trades if t.get("outcome") == "Success"])
        ce_losses = len([t for t in ce_trades if t.get("outcome") == "Failure"])
        
        pe_total = len(pe_trades)
        pe_wins = len([t for t in pe_trades if t.get("outcome") == "Success"])
        pe_losses = len([t for t in pe_trades if t.get("outcome") == "Failure"])
        
        print("\n" + "=" * 60)
        print(f"               SUMMARY REPORT ({mode})")
        print("=" * 60)
        print(f"Total Days Scanned  : {total_days}")
        print(f"Total Trades        : {total_trades}")
        print(f"Total Wins          : {total_success}")
        print(f"Total Losses        : {total_failure}")
        print(f"Overall Win Rate    : {win_rate}%")
        print(f"Avg Daily P&L       : {avg_pnl}%")
        print(f"Call (CE) Breakdown : {ce_total} trades ({ce_wins} wins, {ce_losses} losses)")
        print(f"Put (PE) Breakdown  : {pe_total} trades ({pe_wins} wins, {pe_losses} losses)")
        
        ce_win_rate = round((ce_wins / ce_total) * 100, 2) if ce_total > 0 else 0.0
        pe_win_rate = round((pe_wins / pe_total) * 100, 2) if pe_total > 0 else 0.0
        
        mode_summary = {
            "Candle_Mode": mode,
            "Total_Days": total_days,
            "Total_Trades": total_trades,
            "Wins": total_success,
            "Losses": total_failure,
            "Win_Rate_Pct": win_rate,
            "Avg_Daily_PnL_Pct": avg_pnl,
            "BUY Total Trades": f"{ce_total} ({ce_wins} win {ce_losses} loss)",
            "BUY Success %": ce_win_rate,
            "PUT Total Trades": f"{pe_total} ({pe_wins} win {pe_losses} loss)",
            "PUT Success %": pe_win_rate
        }
        comparative_results.append(mode_summary)
        
        os.makedirs("Dependencies/backtest_results", exist_ok=True)
        mode_path = f"Dependencies/backtest_results/Aggregated_{mode}_Report.csv"
        df_results.to_csv(mode_path, index=False)
        print(f"\nFull day-by-day summary saved to: {mode_path}")
        
        # Save aggregated detailed trades
        if all_trades:
            df_trades = pd.DataFrame(all_trades)
            trades_agg_path = f"Dependencies/backtest_results/Aggregated_Trades_{mode}.csv"
            df_trades.to_csv(trades_agg_path, index=False)
            print(f"Aggregated detailed trades saved to: {trades_agg_path}")
        
    if comparative_results:
        df_compare = pd.DataFrame(comparative_results)
        comp_path = "Dependencies/backtest_results/Candle_Comparison_Report.csv"
        df_compare.to_csv(comp_path, index=False)
        
        print("\n" + "=" * 60)
        print("         FINAL CONSOLIDATED COMPARATIVE REPORT")
        print("=" * 60)
        print(df_compare.to_string(index=False))
        print(f"\nConsolidated comparison saved to: {comp_path}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python multi_day_backtest.py DD-MM-YYYY DD-MM-YYYY")
        print("Example: python multi_day_backtest.py 01-10-2025 31-12-2025")
        sys.exit(1)
        
    start = sys.argv[1]
    end = sys.argv[2]
    
    run_multiday(start, end)
