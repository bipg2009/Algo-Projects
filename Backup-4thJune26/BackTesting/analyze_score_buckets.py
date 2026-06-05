import pandas as pd
import glob
import os

def categorize_score(score):
    if pd.isna(score):
        return 'Unknown'
    score = float(score)
    if score >= 115:
        return '115+'
    elif score >= 100:
        return '100-114'
    elif score >= 85:
        return '85-99'
    elif score >= 70:
        return '70-84'
    else:
        return '<70'

def analyze_buckets():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # Read from local Reports folder, including subfolders like May-Runs recursively
    search_path_1 = os.path.join(base_dir, 'Reports', '**', 'backtest_trades_*.csv')
    search_path_2 = os.path.join(base_dir, '..', 'Dependencies', 'backtest_results', 'backtest_trades_*.csv')
    
    files = glob.glob(search_path_1, recursive=True)
    files += glob.glob(search_path_2)
    
    valid_dfs = []
    for f in set(files):
        if os.path.getsize(f) > 10:
            try: 
                df = pd.read_csv(f)
                if not df.empty:
                    valid_dfs.append(df)
            except Exception:
                pass

    if not valid_dfs:
        print("No backtest trades found.")
        return

    df = pd.concat(valid_dfs)
    
    # Allow both 'score' and 'score_pct' column names
    score_col = 'score' if 'score' in df.columns else 'score_pct'
    pnl_col = 'pnl' if 'pnl' in df.columns else 'pnl_pct'
    
    if score_col not in df.columns:
        print(f"No score column found in the trade reports.")
        return

    df['score_bucket'] = df[score_col].apply(categorize_score)
    df['is_win'] = df['outcome'].astype(str).str.contains('Success', case=False, na=False)
    
    # Identify index: NSE (NIFTY/BANKNIFTY/FINNIFTY/MIDCPNIFTY) vs BSE (SENSEX/BANKEX)
    def get_index(sym):
        sym = str(sym).upper()
        if sym.startswith('SENSEX') or sym.startswith('BANKEX'):
            return 'BSE'
        else:
            return 'NSE'
            
    df['exchange'] = df['symbol'].apply(get_index)
    
    bucket_order = ['70-84', '85-99', '100-114', '115+', 'Unknown', '<70']
    
    reports_dir = os.path.join(base_dir, 'Reports')
    os.makedirs(reports_dir, exist_ok=True)
    
    for exch in ['NSE', 'BSE']:
        exch_df = df[df['exchange'] == exch]
        
        if exch_df.empty:
            continue
            
        summary = []
        for bucket in bucket_order:
            b_df = exch_df[exch_df['score_bucket'] == bucket]
            if b_df.empty:
                summary.append({'Score Range': bucket, 'Trades': 0, 'Win %': '0.00%', 'Avg PnL': 0.0})
                continue
                
            trades = len(b_df)
            win_pct = (b_df['is_win'].sum() / trades) * 100
            avg_pnl = b_df[pnl_col].mean() if pnl_col in b_df.columns else 0.0
            
            summary.append({
                'Score Range': bucket,
                'Trades': trades,
                'Win %': f"{win_pct:.2f}%",
                'Avg PnL': round(avg_pnl, 2)
            })
            
        res_df = pd.DataFrame(summary)
        out_file = os.path.join(reports_dir, f"{exch}_Score_Buckets.csv")
        res_df.to_csv(out_file, index=False)
        print(f"\n--- {exch} Score Buckets ---")
        print(res_df.to_string(index=False))
        print(f"Saved to {out_file}")

if __name__ == '__main__':
    analyze_buckets()
