import os
import sys
import pandas as pd
import numpy as np
import datetime
import traceback

# Force parent path inclusion for system modules
PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)
BACKTEST_DIR = os.path.join(PARENT_DIR, "BackTesting")
if BACKTEST_DIR not in sys.path:
    sys.path.insert(0, BACKTEST_DIR)

import System_Config as sc
import Option_strategy_core as core
import indicator_engine as ie
import Downtrend_Sell
import Uptrend_Buy

# Custom results output dir
RESULTS_DIR = os.path.join(PARENT_DIR, "Antigravity_Research", "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

# Centralized date helper
import backtest_helpers as bh

def option_bar_idx(nifty_1m_idx):
    return nifty_1m_idx // 5

def format_option_label(underlying, strike, option_type, test_date):
    dt = pd.to_datetime(test_date)
    day = dt.day
    months = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
    month = months[dt.month - 1]
    yr = str(dt.year)[-2:]
    return f"{underlying} {day} {month} {yr} {int(strike)} {option_type}"

import sys
# Import standard cache-aware methods from primary backtest engine
sys.path.insert(0, PARENT_DIR)
import importlib.util
spec = importlib.util.spec_from_file_location("main_backtest", os.path.join(PARENT_DIR, "NSE-Option-Scanner-Backtest.py"))
main_backtest = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main_backtest)

fetch_nifty_bars = main_backtest.fetch_nifty_bars
fetch_option_legs = main_backtest.fetch_option_legs
align_legs = main_backtest.align_legs

def get_option_snapshot(legs, pick, bar_opt_idx):
    for item in legs:
        if item["option_type"] != pick["option_type"]:
            continue
        s = item["series"]
        if bar_opt_idx >= len(s["close"]):
            continue
        if int(float(s["strike"][bar_opt_idx])) == int(pick["strike"]):
            return {
                "ltp": float(s["close"][bar_opt_idx]),
                "oi": int(s["oi"][bar_opt_idx]),
                "oi_change": int(s["oi"][bar_opt_idx]) - (int(s["oi"][bar_opt_idx - 1]) if bar_opt_idx > 0 else int(s["oi"][bar_opt_idx])),
                "volume": int(s["volume"][bar_opt_idx]),
                "prev_volume": int(s["volume"][bar_opt_idx - 1]) if bar_opt_idx > 0 else 0
            }
    return {"ltp": 0.0, "oi": 0, "oi_change": 0, "volume": 0, "prev_volume": 0}

def build_chain_at_bar(legs, bar_opt_idx, ref_date, underlying):
    options = []
    for item in legs:
        s = item["series"]
        if bar_opt_idx >= len(s["close"]):
            continue
        strike = float(s["strike"][bar_opt_idx])
        spot = float(s["spot"][bar_opt_idx])
        oi = int(s["oi"][bar_opt_idx])
        prev_oi = int(s["oi"][bar_opt_idx - 1]) if bar_opt_idx > 0 else oi
        volume = int(s["volume"][bar_opt_idx])
        ltp = float(s["close"][bar_opt_idx])
        iv = float(s["iv"][bar_opt_idx] or 0)
        if volume <= 0 and ltp <= 0:
            continue
        label = format_option_label(underlying, strike, item["option_type"], ref_date)
        options.append({
            "strike": strike, "option_type": item["option_type"],
            "symbol": label, "display_symbol": label,
            "ltp": ltp, "iv": iv, "oi": oi,
            "oi_change": oi - prev_oi, "volume": volume,
            "spot": spot,
        })
    if not options:
        return None
    spot = options[0]["spot"]
    atm = round(spot / 50) * 50
    return {"spot": spot, "atm": atm, "options": options}

def _book_row(test_date, time_val, trade_id, event, pick, price, sl, rsi, oi, entry_price=None):
    pnl = 0.0
    outcome = ""
    if entry_price is not None and entry_price > 0:
        pnl = round(((price - entry_price) / entry_price) * 100, 2)
        outcome = "Success" if pnl > 0 else "Failure"
    return {
        "date": test_date,
        "trade id": trade_id,
        "time ist": bh.format_ist_time(time_val),
        "event": event,
        "symbol": pick["display_symbol"],
        "option_type": pick["option_type"],
        "price": price,
        "trailing_sl": sl,
        "rsi": round(rsi, 1),
        "oi": oi,
        "outcome": outcome
    }

def simulate_trade(pick, entry_1m_idx, nifty_1m, legs, test_date):
    # N+1 entry delay
    if entry_1m_idx + 1 < len(nifty_1m):
        entry_1m_idx += 1
    bar_opt_entry = option_bar_idx(entry_1m_idx)
    opt = get_option_snapshot(legs, pick, bar_opt_entry)
    
    # 1.0% Realistic slippage
    entry_ltp = round(opt["ltp"] * 1.01, 2)
    entry_spot = float(nifty_1m.iloc[entry_1m_idx]["close"])
    spot_sl = (entry_spot - 20.0) if pick["option_type"] == "CE" else (entry_spot + 20.0)
    
    position = {
        "symbol": pick["display_symbol"],
        "option_type": pick["option_type"],
        "entry_ltp": entry_ltp,
        "target": round(entry_ltp + 60.0, 2),
        "sl": round(entry_ltp - 20.0, 2), # Step 1: Loosened 20-point initial premium SL
        "initial_sl": round(entry_ltp - 20.0, 2),
        "max_ltp": entry_ltp,
        "prev_volume": opt["prev_volume"],
        "entry_spot": entry_spot,
        "spot_sl": spot_sl,
        "breakeven_triggered": False
    }
    
    monitor_log = []
    trade_book = []
    exit_ltp = entry_ltp
    exit_reason = "EOD"
    exit_1m_idx = entry_1m_idx
    trade_id = f"{test_date}_{entry_1m_idx}"
    
    entry_time = nifty_1m.iloc[entry_1m_idx]["start_Time"]
    entry_rsi = core.calculate_rsi(bh.prepare_nifty_1m(nifty_1m.iloc[: entry_1m_idx + 1]))
    entry_oi = opt.get("oi", pick.get("oi", ""))
    
    trade_book.append(_book_row(
        test_date, entry_time, trade_id, f"BUY {pick['option_type']}",
        pick, entry_ltp, position["sl"], entry_rsi, entry_oi
    ))
    
    for i in range(entry_1m_idx + 1, len(nifty_1m)):
        row_1m = nifty_1m.iloc[i]
        bar_time = row_1m["start_Time"]
        
        # EOD exit at 15:12
        if bh.bar_time_ist(bar_time) >= bh.MARKET_EXIT_TIME:
            exit_ltp = get_option_snapshot(legs, pick, option_bar_idx(i))["ltp"]
            exit_reason = "TIME_DECAY"
            exit_1m_idx = i
            exit_rsi = core.calculate_rsi(bh.prepare_nifty_1m(nifty_1m.iloc[: i + 1]))
            exit_oi = get_option_snapshot(legs, pick, option_bar_idx(i)).get("oi", "")
            trade_book.append(_book_row(
                test_date, bar_time, trade_id, "SELL",
                pick, exit_ltp, position["sl"], exit_rsi, exit_oi,
                entry_price=entry_ltp
            ))
            break
            
        df_slice = bh.prepare_nifty_1m(nifty_1m.iloc[: i + 1])
        opt = get_option_snapshot(legs, pick, option_bar_idx(i))
        current_ltp = opt["ltp"]
        
        # 1. Check Target Hit
        if current_ltp >= position["target"]:
            exit_ltp = position["target"]
            exit_reason = "target_hit"
            exit_1m_idx = i
            trade_book.append(_book_row(
                test_date, bar_time, trade_id, "SELL",
                pick, exit_ltp, position["sl"], core.calculate_rsi(df_slice), opt.get("oi", ""),
                entry_price=entry_ltp
            ))
            break
            
        # 2. Check 20-Point Nifty Spot SL
        spot_hit = False
        if position["option_type"] == "CE" and row_1m["low"] <= position["spot_sl"]:
            spot_hit = True
        elif position["option_type"] == "PE" and row_1m["high"] >= position["spot_sl"]:
            spot_hit = True
            
        if spot_hit:
            exit_ltp = current_ltp if current_ltp > position["sl"] else position["sl"]
            exit_reason = "stop_loss_hit"
            exit_1m_idx = i
            trade_book.append(_book_row(
                test_date, bar_time, trade_id, "SELL",
                pick, exit_ltp, position["sl"], core.calculate_rsi(df_slice), opt.get("oi", ""),
                entry_price=entry_ltp
            ))
            break
            
        # 3. Check Premium SL
        if current_ltp <= position["sl"]:
            exit_ltp = position["sl"]
            exit_reason = "stop_loss_hit"
            exit_1m_idx = i
            trade_book.append(_book_row(
                test_date, bar_time, trade_id, "SELL",
                pick, exit_ltp, position["sl"], core.calculate_rsi(df_slice), opt.get("oi", ""),
                entry_price=entry_ltp
            ))
            break
            
        # 4. 12-Minute Momentum Cutoff
        elapsed = i - entry_1m_idx
        if elapsed == 12:
            if current_ltp < (entry_ltp + 5.0):
                exit_ltp = current_ltp
                exit_reason = "TIME_DECAY"
                exit_1m_idx = i
                trade_book.append(_book_row(
                    test_date, bar_time, trade_id, "SELL",
                    pick, exit_ltp, position["sl"], core.calculate_rsi(df_slice), opt.get("oi", ""),
                    entry_price=entry_ltp
                ))
                break
                
        # 5. Trailing / Breakeven Rules
        peak = max(position["max_ltp"], current_ltp)
        position["max_ltp"] = peak
        
        # Step 2: Trail to Breakeven (+1 point buffer) at +15 points
        if not position["breakeven_triggered"] and peak >= (entry_ltp + 15.0):
            position["sl"] = round(entry_ltp + 1.0, 2)
            position["breakeven_triggered"] = True
            
        # Step 3: Trailing SL of 15 premium points once peak exceeds entry + 20
        if peak >= (entry_ltp + 20.0):
            new_sl = round(peak - 15.0, 2)
            if new_sl > position["sl"]:
                position["sl"] = new_sl
                
    exit_time = nifty_1m.iloc[exit_1m_idx]["start_Time"]
    pnl_pct = round(((exit_ltp - entry_ltp) / entry_ltp) * 100, 2) if entry_ltp else 0
    outcome = "Success" if pnl_pct > 0 else "Failure"
    
    return {
        "test_date": test_date,
        "symbol": f"{pick['display_symbol']} {pick.get('strategy_suffix', '')}".strip(),
        "option_type": pick["option_type"],
        "strike": int(pick["strike"]),
        "score_pct": pick.get("score_pct", 0),
        "entry_time_ist": bh.format_ist_time(entry_time),
        "exit_time_ist": bh.format_ist_time(exit_time),
        "entry_ltp": entry_ltp,
        "exit_ltp": exit_ltp,
        "trailing_sl": position["sl"],
        "pnl_pct": pnl_pct,
        "outcome": outcome,
        "exit_reason": exit_reason,
        "monitor_log": monitor_log,
        "trade_book": trade_book
    }

def run_backtest(test_date, expiry_code, candle_mode="VOLUME", results_dir=None):
    from broker_client import get_live_client
    tsl = get_live_client()
    
    print(f"\nANTIGRAVITY RESEARCH RUN | {test_date} | mode={candle_mode}")
    nifty_1m = fetch_nifty_bars(tsl, test_date, 1)
    
    if candle_mode == "HEIKIN_ASHI":
        import candle_transformer
        nifty_1m = candle_transformer.to_heikin_ashi(nifty_1m)
    elif candle_mode == "VOLUME":
        import candle_transformer
        nifty_1m = candle_transformer.to_volume_candles(nifty_1m)
        
    legs = fetch_option_legs(tsl, test_date, expiry_code)
    
    trades = []
    traded_symbols = set()
    in_trade_until = -1
    
    for i in range(30, len(nifty_1m)):
        if i <= in_trade_until:
            continue
            
        bar_time = nifty_1m.iloc[i]["start_Time"]
        chain = build_chain_at_bar(legs, option_bar_idx(i), test_date, "NIFTY")
        df_slice = bh.prepare_nifty_1m(nifty_1m.iloc[: i + 1]) if len(nifty_1m.iloc[: i + 1]) >= 30 else None
        pcr = bh.pcr_from_chain(chain) if chain else 1.0
        gap_mode = False
        
        pick = None
        best_score = 0
        
        if chain and df_slice is not None:
            spot = chain["spot"]
            atm = round(spot / 50) * 50
            target_ce_strike = atm - 100
            target_pe_strike = atm + 100
            
            for opt in chain["options"]:
                ot = opt["option_type"]
                if ot == "CE" and int(opt["strike"]) != int(target_ce_strike):
                    continue
                if ot == "PE" and int(opt["strike"]) != int(target_pe_strike):
                    continue
                    
                opt_row = {
                    "symbol": opt["display_symbol"],
                    "strike": opt["strike"],
                    "volume": opt.get("volume", 0),
                    "oi_change": opt.get("oi_change", 0),
                }
                
                fired = core.detect_trigger_1m(
                    df_slice, ot, opt_row, chain["spot"],
                    spot, spot, pcr
                )
                score = core.build_score(opt_row, ot, df_slice, pcr, gap_mode)
                
                if fired and score >= core.STRONG_BUY_THRESHOLD:
                    if score > best_score:
                        best_score = score
                        pick = {**opt, "score_pct": score, "strategy_suffix": opt_row.get("strategy_suffix", "")}
                        
        if not chain or df_slice is None or not pick:
            continue
            
        if not bh.is_entry_time_allowed(bar_time):
            continue
            
        if pick["display_symbol"] in traded_symbols:
            continue
            
        # Simulate trade
        trade = simulate_trade(pick, i, nifty_1m, legs, test_date)
        trades.append(trade)
        traded_symbols.add(pick["display_symbol"])
        print(f"   [Trade Fired] {trade['entry_time_ist']} BUY {trade['symbol']} @ Rs {trade['entry_ltp']} -> {trade['outcome']} PnL {trade['pnl_pct']}% ({trade['exit_reason']})", flush=True)
        
    # Calculate stats
    total = len(trades)
    wins = len([t for t in trades if t["outcome"] == "Success"])
    losses = total - wins
    win_rate = round((wins / total) * 100, 2) if total else 0.0
    avg_pnl = round(sum(t["pnl_pct"] for t in trades) / total, 2) if total else 0.0
    
    summary = {
        "test_date": test_date,
        "total_trades": total,
        "success": wins,
        "failure": losses,
        "win_rate_pct": win_rate,
        "avg_pnl_pct": avg_pnl
    }
    
    return trades, summary
