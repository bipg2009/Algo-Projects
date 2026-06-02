import sys
import os
import pandas as pd
import numpy as np
import datetime

# Add root folder to Path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT_DIR)

import Option_strategy_core as core
import Risk_Engine as risk_engine
import Trade_Calculator as calc
import indicator_engine as Indicators

class VirtualOMS:
    """
    Simulates Order Executions and PnL Tracking.
    """
    def __init__(self, initial_capital=100000.0):
        self.capital = initial_capital
        self.active_position = None
        self.trade_log = []

    def place_buy_order(self, symbol, option_type, ltp, time_stamp, score, underlying_spot):
        # Calculate parameters exactly like Live
        margin_req_pc = 0.12
        calc_package = calc.calculate_trade_parameters(ltp, symbol, margin_req_pc)
        
        qty = calc_package["qty"]
        target = calc_package["target_price"]
        sl = calc_package["sl_price"]
        margin_used = calc_package["estimated_margin"]
        
        if self.capital < margin_used:
            print(f"[{time_stamp}] Insufficient Capital. Needed {margin_used}, Have {self.capital}")
            return False
            
        self.active_position = {
            "symbol": symbol,
            "type": option_type,
            "entry_price": ltp,
            "entry_time": time_stamp,
            "qty": qty,
            "target": target,
            "sl": sl,
            "margin_used": margin_used,
            "highest_price": ltp,
            "underlying_at_entry": underlying_spot
        }
        
        print(f"[{time_stamp}] [BUY] {qty}x {symbol} @ Rs {ltp} | Target: Rs {target} | SL: Rs {sl} | Score: {score}")
        return True
        
    def check_exit_conditions(self, current_time, current_opt_ltp):
        if not self.active_position:
            return None
            
        pos = self.active_position
        pos["highest_price"] = max(pos["highest_price"], current_opt_ltp)
        
        # Trail SL logic (Simple baseline trailing: every 10 pts move up, trail SL 5 pts)
        profit_pts = pos["highest_price"] - pos["entry_price"]
        if profit_pts >= 10:
            trail_amount = (profit_pts // 10) * 5
            new_sl = pos["entry_price"] - (pos["entry_price"] - pos["sl"]) + trail_amount
            if new_sl > pos["sl"]:
                pos["sl"] = new_sl
        
        # Check Hits
        reason = None
        if current_opt_ltp >= pos["target"]:
            reason = "TARGET_HIT"
        elif current_opt_ltp <= pos["sl"]:
            reason = "SL_HIT"
            
        if reason:
            sell_price = pos["target"] if reason == "TARGET_HIT" else pos["sl"]
            # Correct precise execution assumption to close
            if reason == "SL_HIT": 
                sell_price = current_opt_ltp # slippage factor incorporated in exact tick overlap
                
            pnl = (sell_price - pos["entry_price"]) * pos["qty"]
            self.capital += pnl
            
            trade_record = {
                "symbol": pos["symbol"],
                "type": pos["type"],
                "entry_time": pos["entry_time"],
                "exit_time": current_time,
                "entry_price": round(pos["entry_price"], 2),
                "exit_price": round(sell_price, 2),
                "qty": pos["qty"],
                "pnl": round(pnl, 2),
                "reason": reason,
                "capital_after": round(self.capital, 2)
            }
            self.trade_log.append(trade_record)
            print(f"[{current_time}] [SELL] {pos['qty']}x {pos['symbol']} @ Rs {sell_price} | PnL: Rs {round(pnl,2)} | {reason}")
            self.active_position = None
            return trade_record
            
        return None

def mock_option_chain_at_spot(spot_price, symbol_prefix="NIFTY"):
    """Generates a dynamic mock option chain based on the current spot price."""
    # Round to nearest 100
    atm_strike = round(spot_price / 100) * 100
    
    strikes = [atm_strike - 200, atm_strike - 100, atm_strike, atm_strike + 100, atm_strike + 200]
    data = []
    
    for st in strikes:
        # CE Data
        ce_itm_amount = max(0, spot_price - st)
        ce_premium = ce_itm_amount + 50 # Add 50 for extrinsic
        # PE Data
        pe_itm_amount = max(0, st - spot_price)
        pe_premium = pe_itm_amount + 50
        
        ce_vol = int(np.random.randint(10000, 30000))
        pe_vol = int(np.random.randint(10000, 30000))
        
        data.append({
            'strike': st,
            'option_type': 'CE',
            'symbol': f'{symbol_prefix} {st} CE',
            'ltp': ce_premium if ce_premium > 5 else 5,
            'oi': 5000 + (1000 if st == atm_strike else 0),
            'volume': ce_vol,
            'previous_oi': 4500,
            'oi_change': 11.1
        })
        
        data.append({
            'strike': st,
            'option_type': 'PE',
            'symbol': f'{symbol_prefix} {st} PE',
            'ltp': pe_premium if pe_premium > 5 else 5,
            'oi': 5000 + (1000 if st == atm_strike else 0),
            'volume': pe_vol,
            'previous_oi': 4500,
            'oi_change': 11.1
        })
        
    return pd.DataFrame(data)

def approximate_option_price(spot_price, strike, opt_type):
    if opt_type == 'CE':
        return max(5, spot_price - strike + 50)
    else:
        return max(5, strike - spot_price + 50)

def bt_add_supertrend(df: pd.DataFrame, period=10, multiplier=3) -> pd.DataFrame:
    if df is None or df.empty or not all(col in df.columns for col in ["high", "low", "close"]):
        return df
        
    df = df.copy()
    high = pd.to_numeric(df['high'], errors='coerce')
    low = pd.to_numeric(df['low'], errors='coerce')
    close = pd.to_numeric(df['close'], errors='coerce')
    
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/period, adjust=False).mean()
    
    hl2 = (high + low) / 2
    final_upperband = hl2 + (multiplier * atr)
    final_lowerband = hl2 - (multiplier * atr)
    
    close_arr = close.to_numpy()
    final_upperband_arr = np.array(final_upperband, copy=True)
    final_lowerband_arr = np.array(final_lowerband, copy=True)
    
    supertrend = [True] * len(df)
    supertrend_val = np.zeros(len(df))
    
    for i in range(1, len(df)):
        curr_close = close_arr[i]
        
        if curr_close > final_upperband_arr[i-1]:
            supertrend[i] = True
        elif curr_close < final_lowerband_arr[i-1]:
            supertrend[i] = False
        else:
            supertrend[i] = supertrend[i-1]
            if supertrend[i] and final_lowerband_arr[i] < final_lowerband_arr[i-1]:
                final_lowerband_arr[i] = final_lowerband_arr[i-1]
            if not supertrend[i] and final_upperband_arr[i] > final_upperband_arr[i-1]:
                final_upperband_arr[i] = final_upperband_arr[i-1]
        
        supertrend_val[i] = final_lowerband_arr[i] if supertrend[i] else final_upperband_arr[i]
            
    df['supertrend'] = supertrend_val
    df['st_color'] = ["GREEN" if s else "RED" for s in supertrend]
    
    return df

def run_backtest(csv_path: str, start_date_str=None, end_date_str=None):
    print("=" * 60)
    print("Execution-Realistic Backtester Initializing")
    print(f"Data File: {csv_path}")
    if start_date_str and end_date_str:
        print(f"Filtering Dates: {start_date_str} to {end_date_str}")
    print("=" * 60)
    
    if not os.path.exists(csv_path):
        print(f"Data file not found: {csv_path}")
        return
        
    df_full = pd.read_csv(csv_path)
    
    # Assuming standard dhanhq 1min csv format: start_Time, open, high, low, close, volume
    time_col = 'timestamp' if 'timestamp' in df_full.columns else 'start_Time'
    if time_col not in df_full.columns:
        print(f"Could not find time column. Columns found: {df_full.columns}")
        return
        
    df_full['datetime'] = pd.to_datetime(df_full[time_col])
    if df_full['datetime'].dt.tz is not None:
        df_full['datetime'] = df_full['datetime'].dt.tz_localize(None)
    
    if start_date_str:
        df_full = df_full[df_full['datetime'] >= pd.to_datetime(start_date_str)]
    if end_date_str:
        # Include the whole end date up to 23:59:59
        end_dt = pd.to_datetime(end_date_str) + pd.Timedelta(days=1, seconds=-1)
        df_full = df_full[df_full['datetime'] <= end_dt]
        
    if df_full.empty:
        print("No data available for the given date range.")
        return
        
    df_full.sort_values('datetime', inplace=True)
    df_full.set_index('datetime', inplace=True, drop=False)
    df_full = df_full[~df_full.index.duplicated(keep='first')]
    
    print(f"Loaded {len(df_full)} 1-minute bars.")
    
    oms = VirtualOMS(initial_capital=100000.0)
    
    # Precompute indicators across the entire dataset exactly ONCE to prevent O(N^2) lag
    print("Precomputing Indicators over the entire dataset...")
    df_full = Indicators.add_vwap(df_full)
    df_full = Indicators.add_ema(df_full)
    df_full = bt_add_supertrend(df_full)
    df_full["RSI"] = Indicators.calculate_rsi_series(df_full)
    df_full["RSI_14"] = True # Flag for fast path
    
    # Minimum bars required to calculate Supertrend, VWAP, EMA, RSI (typically 30)
    MIN_BARS = 30
    
    print("Starting bar-by-bar execution simulation...")
    for i in range(MIN_BARS, len(df_full)):
        current_minute_data = df_full.iloc[:i+1]
        
        current_row = current_minute_data.iloc[-1]
        current_time = current_row["datetime"]
        nifty_spot = current_row["close"]
        
        # Today Open / Prev Close tracking 
        # (For accurate daily limits, we should determine day bounds, but for simplicity taking absolute start for Prev Close)
        today_open = current_minute_data.iloc[-i]['open'] if i < 375 else current_minute_data.iloc[-375]['open'] # approx 1 day
        previous_close = current_minute_data.iloc[-(min(i, 375))]['close']
        
        if oms.active_position:
            # We are holding. We must track price exits.
            # Simulate option price based on underlying tracking
            current_opt_ltp = approximate_option_price(nifty_spot, oms.active_position["underlying_at_entry"], oms.active_position["type"])
            oms.check_exit_conditions(current_time, current_opt_ltp)
            continue
            
        # If not holding, scan for entry
        # Get chain proxy
        chain_df = mock_option_chain_at_spot(nifty_spot)
        
        # Pick deep ITM candidate for CE
        opt_types = chain_df['option_type'].values
        ce_mask = opt_types == 'CE'
        pe_mask = opt_types == 'PE'
        
        ce_opts = chain_df[ce_mask]
        pe_opts = chain_df[pe_mask]
        
        # Sort by furthest ITM
        ce_opts = ce_opts.sort_values(by='strike', ascending=True) 
        pe_opts = pe_opts.sort_values(by='strike', ascending=False)
        
        opt_ce_row = ce_opts.iloc[0].to_dict() if not ce_opts.empty else None
        opt_pe_row = pe_opts.iloc[0].to_dict() if not pe_opts.empty else None
        
        # Score and Evaluate
        if opt_ce_row:
            triggered_ce = core.detect_trigger_1m(
                df_1m=current_minute_data, 
                option_type="CE", 
                opt_row=opt_ce_row, 
                nifty_spot=nifty_spot, 
                previous_close=previous_close, 
                today_open=today_open, 
                pcr_value=1.2, 
                option_chain_df=chain_df
            )
            if triggered_ce:
                score, _ = core.build_and_score_contract(opt_ce_row, "CE", current_minute_data, 1.2)
                oms.place_buy_order(opt_ce_row["symbol"], "CE", opt_ce_row["ltp"], current_time, score, nifty_spot)
                continue
                
        if opt_pe_row:
            triggered_pe = core.detect_trigger_1m(
                df_1m=current_minute_data, 
                option_type="PE", 
                opt_row=opt_pe_row, 
                nifty_spot=nifty_spot, 
                previous_close=previous_close, 
                today_open=today_open, 
                pcr_value=0.8, 
                option_chain_df=chain_df
            )
            if triggered_pe:
                score, _ = core.build_and_score_contract(opt_pe_row, "PE", current_minute_data, 0.8)
                oms.place_buy_order(opt_pe_row["symbol"], "PE", opt_pe_row["ltp"], current_time, score, nifty_spot)

    # Wrap up active position at End of Data
    if oms.active_position:
        sell_ltp = approximate_option_price(df_full.iloc[-1]["close"], oms.active_position["underlying_at_entry"], oms.active_position["type"])
        oms.active_position["target"] = sell_ltp # Force exit at current price
        oms.check_exit_conditions(df_full.iloc[-1]["datetime"], sell_ltp)

    # Print Summary
    print("\n==================================")
    print("BACKTEST RESULTS")
    print("==================================")
    print(f"Total Trades : {len(oms.trade_log)}")
    
    if oms.trade_log:
        wins = [t for t in oms.trade_log if t["pnl"] > 0]
        losses = [t for t in oms.trade_log if t["pnl"] <= 0]
        
        print(f"Wins         : {len(wins)}")
        print(f"Losses       : {len(losses)}")
        print(f"Win Rate     : {(len(wins)/len(oms.trade_log))*100:.1f}%")
        
        total_pnl = sum(t["pnl"] for t in oms.trade_log)
        print(f"Net PnL      : Rs {total_pnl:.2f}")
        print(f"Capital End  : Rs {oms.capital:.2f}")
        
        print("\nTrade Log:")
        df_log = pd.DataFrame(oms.trade_log)
        print(df_log[['entry_time', 'exit_time', 'symbol', 'qty', 'entry_price', 'exit_price', 'pnl', 'reason']].to_string(index=False))
    else:
        print("No trades triggered based on core strategy parameters.")

if __name__ == "__main__":
    test_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "NIFTY_NSE_1min.csv")
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
    
    start_date = "2026-02-16" 
    end_date = "2026-05-27"
    
    # Run backtester on the available verified data range
    run_backtest(test_file, start_date_str=start_date, end_date_str=end_date)
