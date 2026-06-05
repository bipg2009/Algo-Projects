"""
Backtest: 1m SETUP + 1m TRIGGER + post-entry MONITOR.
Exports CSV with IST times, Trade Book (BUY/SELL rows), SUCCESS/FAILURE.

Run:
    py NSE-Option-Scanner-Backtest.py
    py NSE-Option-Scanner-Backtest.py 2026-05-22
"""

import importlib.util
import json
import os
import sys
import time
import traceback

import pandas as pd

# Set IS_BACKTEST environment variable to avoid live API queries during backtesting
os.environ["IS_BACKTEST"] = "1"

import Option_strategy_TEST as core

print("NSE Option Scanner BACKTEST — starting...", flush=True)

TEST_DATE = "2026-05-22"
EXPIRY_CODE = 1
API_PAUSE_SEC = 1.2
NIFTY_SECURITY_ID = 13
OPTION_BAR_TF = 5  # Dhan option history bars (LTP only; NIFTY setup/trigger use 1m)
CACHE_DIR = os.path.join("Dependencies", "backtest_cache")
RESULTS_DIR = os.path.join("Dependencies", "backtest_results")
STRIKE_RANGE = 10

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKTEST_DIR = os.path.join(SCRIPT_DIR, "BackTesting")
if BACKTEST_DIR not in sys.path:
    sys.path.insert(0, BACKTEST_DIR)

import backtest_helpers as bh
import backtest_dhan_client
import ExcelGeneration as excel_gen
import Monitor_Engine as mon_engine
import Risk_Engine as risk_engine


def load_scanner_module():
    """Backtest API client without xlwings / Market_Scanner."""
    return backtest_dhan_client.get_scanner_module()


def format_option_label(underlying, strike, option_type, ref_date):
    dt = pd.to_datetime(ref_date)
    return f"{underlying} {dt.day} {dt.strftime('%b').upper()} {int(strike)} {option_type}"


def cache_path(name):
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, name)


def fetch_nifty_bars(tsl, test_date, interval=1):
    cache = cache_path(f"nifty_{interval}m_{test_date}.json")
    if os.path.isfile(cache):
        return pd.read_json(cache)

    next_day = (pd.to_datetime(test_date) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    resp = tsl.Dhan.intraday_minute_data(
        str(NIFTY_SECURITY_ID), "IDX_I", "INDEX", test_date, next_day, interval=interval
    )
    data = resp.get("data") or {}
    if not data.get("timestamp"):
        raise RuntimeError(f"No NIFTY {interval}m data for {test_date}")

    df = pd.DataFrame(data)
    df["start_Time"] = df["timestamp"].apply(lambda x: tsl.convert_to_date_time(x))
    df["start_Time_ist"] = df["start_Time"].apply(bh.format_ist)
    df = df.drop(columns=["timestamp"])
    df.to_json(cache, orient="records", date_format="iso")
    return df


def fetch_one_option_leg(tsl, strike_offset, opt_type, test_date, expiry_code):
    next_day = (pd.to_datetime(test_date) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    fields = ["close", "iv", "volume", "oi", "spot", "strike"]
    resp = tsl.Dhan.expired_options_data(
        str(NIFTY_SECURITY_ID), "NSE_FNO", "OPTIDX", "WEEK", expiry_code,
        strike_offset, opt_type, fields, test_date, next_day, OPTION_BAR_TF,
    )
    if resp.get("status") != "success":
        raise RuntimeError(f"{strike_offset} {opt_type}: {resp.get('remarks')}")
    payload = resp.get("data") or {}
    if "data" in payload:
        payload = payload["data"]
    side = "ce" if opt_type == "CALL" else "pe"
    leg = payload.get(side) or {}
    if not leg.get("close"):
        raise RuntimeError(f"No candles for {strike_offset} {opt_type}")
    return leg


def fetch_option_legs(tsl, test_date, expiry_code):
    cache = cache_path(f"options_{OPTION_BAR_TF}m_{test_date}_ec{expiry_code}.json")
    if os.path.isfile(cache):
        with open(cache, "r", encoding="utf-8") as f:
            return json.load(f)

    legs = []
    for offset in range(-STRIKE_RANGE, STRIKE_RANGE + 1):
        strike_key = "ATM" if offset == 0 else f"ATM{offset:+d}"
        for opt_type, option_type in (("CALL", "CE"), ("PUT", "PE")):
            time.sleep(API_PAUSE_SEC)
            leg = fetch_one_option_leg(tsl, strike_key, opt_type, test_date, expiry_code)
            legs.append({"offset": offset, "option_type": option_type, "series": leg})
            print(f"  fetched {strike_key} {option_type} ({len(leg['close'])} bars)")
    with open(cache, "w", encoding="utf-8") as f:
        json.dump(legs, f)
    return legs


def align_legs(legs, session_len):
    aligned = []
    for item in legs:
        s = item["series"]
        n = len(s.get("close", []))
        if n > session_len:
            start = n - session_len
            trimmed = {k: (v[start:] if isinstance(v, list) else v) for k, v in s.items()}
            aligned.append({**item, "series": trimmed})
        else:
            aligned.append(item)
    return aligned


def option_bar_idx(minute_idx):
    """Map 1m index to option bar index (option data is 5m)."""
    return minute_idx // OPTION_BAR_TF


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
        oi_change = oi - prev_oi
        oi_pct = (oi_change / prev_oi * 100.0) if prev_oi > 0 else 0.0
        options.append({
            "strike": strike, "option_type": item["option_type"],
            "symbol": label, "display_symbol": label,
            "ltp": ltp, "iv": iv, "oi": oi,
            "oi_change": oi_change, "oi_change_pct": oi_pct, "volume": volume,
            "spot": spot,
        })
    if not options:
        return None
    spot = options[0]["spot"]
    atm = round(spot / 50) * 50
    
    total_ce_oi = sum(o["oi"] for o in options if o["option_type"] == "CE")
    total_pe_oi = sum(o["oi"] for o in options if o["option_type"] == "PE")
    total_ce_vol = sum(o["volume"] for o in options if o["option_type"] == "CE")
    total_pe_vol = sum(o["volume"] for o in options if o["option_type"] == "PE")
    
    return {
        "spot": spot, 
        "atm": atm, 
        "options": options,
        "total_ce_oi": total_ce_oi,
        "total_pe_oi": total_pe_oi,
        "total_ce_vol": total_ce_vol,
        "total_pe_vol": total_pe_vol
    }


def get_option_snapshot(legs, pick, bar_opt_idx):
    for item in legs:
        if item["option_type"] != pick["option_type"]:
            continue
        s = item["series"]
        if bar_opt_idx >= len(s["close"]):
            continue
        if int(float(s["strike"][bar_opt_idx])) == int(pick["strike"]):
            oi = int(s["oi"][bar_opt_idx])
            prev = int(s["oi"][bar_opt_idx - 1]) if bar_opt_idx > 0 else oi
            vol = int(s["volume"][bar_opt_idx])
            prev_vol = int(s["volume"][bar_opt_idx - 1]) if bar_opt_idx > 0 else vol
            oi_change = oi - prev
            oi_pct = (oi_change / prev * 100.0) if prev > 0 else 0.0
            return {
                "ltp": float(s["close"][bar_opt_idx]),
                "oi": oi,
                "oi_change": oi_change,
                "oi_change_pct": oi_pct,
                "volume": vol,
                "prev_volume": prev_vol,
            }
    return {
        "ltp": pick["ltp"],
        "oi": pick.get("oi", ""),
        "oi_change": pick.get("oi_change", 0),
        "oi_change_pct": pick.get("oi_change_pct", 0.0),
        "volume": pick.get("volume", 0),
        "prev_volume": pick.get("volume", 0),
    }


def _book_row(test_date, bar_time, trade_id, event, pick, price, sl, rsi="", oi="", entry_price=None):
    is_sell = "SELL" in (event or "").upper()
    comp_price = entry_price if (is_sell and entry_price is not None) else sl
    return {
        "date": bh.report_date_slug(test_date),
        "trade id": trade_id,
        "time ist": bh.format_ist_time(bar_time),
        "event": bh.normalize_event(event),
        "symbol": pick["display_symbol"],
        "option_type": pick["option_type"],
        "strategy": pick.get("strategy_suffix", "General Buy / Sell"),
        "price": price,
        "trailing_sl": sl,
        "rsi": rsi,
        "oi": oi,
        "outcome": bh.trade_outcome(price, comp_price, is_sell),
    }


def simulate_trade(pick, entry_1m_idx, nifty_1m, legs, test_date):
    import System_Config
    
    # N+1 Execution: Force entry on the NEXT candle to simulate realistic latency/open fill
    if entry_1m_idx + 1 < len(nifty_1m):
        entry_1m_idx += 1
    bar_opt_entry = option_bar_idx(entry_1m_idx)
    opt = get_option_snapshot(legs, pick, bar_opt_entry)
    
    # Apply realistic live execution latency/slippage penalty
    slippage = getattr(System_Config, 'BACKTEST_SLIPPAGE_PCT', 0.01)
    entry_ltp = round(opt["ltp"] * (1.0 + slippage), 2)
    
    # Extract Spot ATR dynamically from current bar (fallback to 15.0 if missing)
    current_atr = nifty_1m.iloc[entry_1m_idx].get("ATR", 15.0)
    levels = bh.entry_levels(entry_ltp, current_atr)
    position = {
        "symbol": pick["display_symbol"],
        "option_type": pick["option_type"],
        "entry_ltp": entry_ltp,
        "target": levels["target"],
        "sl": round(entry_ltp - 15.0, 2), # Strict 15-point initial premium SL
        "initial_sl": round(entry_ltp - 15.0, 2),
        "max_ltp": entry_ltp,
        "prev_volume": opt["prev_volume"],
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
        pick, entry_ltp, position["sl"], entry_rsi, entry_oi,
    ))

    for i in range(entry_1m_idx + 1, len(nifty_1m)):
        row_1m = nifty_1m.iloc[i]
        bar_time = row_1m["start_Time"]
        if bh.bar_time_ist(bar_time) >= bh.MARKET_EXIT_TIME:
            exit_ltp = get_option_snapshot(legs, pick, option_bar_idx(i))["ltp"]
            exit_reason = "TIME_DECAY"
            exit_1m_idx = i
            exit_rsi = core.calculate_rsi(bh.prepare_nifty_1m(nifty_1m.iloc[: i + 1]))
            exit_oi = get_option_snapshot(legs, pick, option_bar_idx(i)).get("oi", "")
            trade_book.append(_book_row(
                test_date, bar_time, trade_id, "SELL",
                pick, exit_ltp, position["sl"], exit_rsi, exit_oi,
                entry_price=position["entry_ltp"]
            ))
            break

        df_slice = bh.prepare_nifty_1m(nifty_1m.iloc[: i + 1])
        opt = get_option_snapshot(legs, pick, option_bar_idx(i))
        row_ind = df_slice.iloc[-2]
        snap = {
            "ltp": opt["ltp"],
            "oi_change": opt["oi_change"],
            "volume": opt["volume"],
            "prev_volume": position.get("prev_volume", opt["prev_volume"]),
            "ema9": float(row_ind["EMA9"]),
            "ema20": float(row_ind["EMA20"]),
            "supertrend_1m": str(row_ind["ST_COLOR"]),
        }
        position["max_ltp"] = max(position.get("max_ltp", snap["ltp"]), snap["ltp"])
        from models import TradePosition
        import datetime
        pos_obj = TradePosition(
            symbol="NIFTY", option_type=position["option_type"], qty=75,
            entry_ltp=position["entry_ltp"],
            target=position.get("target", position["entry_ltp"] + 60),
            sl=position["sl"],
            initial_sl=position.get("initial_sl", position["sl"]),
            margin_used=0.0,
            entry_time=position.get("entry_time", bar_time),
            entry_oi=position.get("entry_oi", opt.get("oi", 0)),
            peak_price=position.get("max_ltp", snap["ltp"])
        )
        opt_row = {"oi": opt.get("oi", 0)}
        action, reason, new_sl = mon_engine.execute_hypercare_monitoring(
            pos_obj, df_slice, opt_row, snap["ltp"], is_backtest=True
        )
        position["prev_volume"] = opt["volume"]

        monitor_log.append({
            "time_ist": bh.format_ist_time(bar_time),
            "datetime_ist": bh.format_ist(bar_time),
            "option_ltp": snap["ltp"],
            "rsi_1m": core.calculate_rsi(df_slice),
            "trailing_sl": position["sl"],
            "action": action,
            "reason": reason,
        })

        if action == "TRAIL":
            position["sl"] = new_sl
        elif action == "EXIT":
            exit_ltp = snap["ltp"]
            if reason == "stop_loss_hit":
                # Exit at the actual premium LTP (snap["ltp"]) if it is better than the premium SL threshold,
                # simulating immediate execution upon Nifty spot SL hit. Otherwise, exit at the premium SL.
                if snap["ltp"] > position["sl"]:
                    exit_ltp = snap["ltp"]
                else:
                    exit_ltp = position["sl"]
            elif reason == "target_hit":
                exit_ltp = position["target"]
            exit_reason = reason
            exit_1m_idx = i
            trade_book.append(_book_row(
                test_date, bar_time, trade_id, "SELL",
                pick, exit_ltp, position["sl"],
                core.calculate_rsi(df_slice), opt.get("oi", ""),
                entry_price=position["entry_ltp"]
            ))
            break
        exit_ltp = snap["ltp"]
        exit_1m_idx = i
 
    if exit_reason == "EOD":
        row_1m = nifty_1m.iloc[exit_1m_idx]
        trade_book.append(_book_row(
            test_date, row_1m["start_Time"], trade_id, "SELL",
            pick, exit_ltp, position["sl"],
            core.calculate_rsi(bh.prepare_nifty_1m(nifty_1m.iloc[: exit_1m_idx + 1])),
            get_option_snapshot(legs, pick, option_bar_idx(exit_1m_idx)).get("oi", ""),
            entry_price=position["entry_ltp"]
        ))

    exit_time = nifty_1m.iloc[exit_1m_idx]["start_Time"]
    pnl_pct = round(((exit_ltp - entry_ltp) / entry_ltp) * 100, 2) if entry_ltp else 0
    last_outcome = "Success" if pnl_pct > 0 else "Failure"

    return {
        "test_date": test_date,
        "symbol": pick["display_symbol"],
        "option_type": pick["option_type"],
        "strike": int(pick["strike"]),
        "strategy": pick.get("strategy_suffix", "General Buy / Sell"),
        "score_pct": pick.get("score_pct", 0),
        "entry_time_ist": bh.format_ist_time(entry_time),
        "exit_time_ist": bh.format_ist_time(exit_time),
        "entry_ltp": entry_ltp,
        "exit_ltp": exit_ltp,
        "trailing_sl": position["sl"],
        "pnl_pct": pnl_pct,
        "outcome": last_outcome,
        "exit_reason": exit_reason,
        "monitor_log": monitor_log,
        "trade_book": trade_book,
    }


def export_results(test_date, trades, monitor_rows, scan_log, trade_book, results_dir=None):
    out_dir = results_dir or RESULTS_DIR
    os.makedirs(out_dir, exist_ok=True)
    slug = bh.report_date_slug(test_date)

    trades_path = os.path.join(out_dir, f"backtest_trades_{slug}.csv")
    monitor_path = os.path.join(out_dir, f"backtest_monitor_{slug}.csv")
    scan_path = os.path.join(out_dir, f"backtest_scan_log_{slug}.csv")
    summary_path = os.path.join(out_dir, f"backtest_summary_{slug}.csv")

    pd.DataFrame(trades).to_csv(trades_path, index=False)
    pd.DataFrame(monitor_rows).to_csv(monitor_path, index=False)
    pd.DataFrame(scan_log).to_csv(scan_path, index=False)

    total = len(trades)
    success = sum(1 for t in trades if str(t.get("outcome", "")).lower() == "success")
    failure = sum(1 for t in trades if str(t.get("outcome", "")).lower() == "failure")
    breakeven = total - success - failure
    win_rate = round((success / total) * 100, 2) if total else 0
    failure_rate = round((failure / total) * 100, 2) if total else 0
    avg_pnl = round(sum(t["pnl_pct"] for t in trades) / total, 2) if total else 0

    book_path = excel_gen.write_trade_book_rows(test_date, trade_book, overwrite=True)

    summary = {
        "test_date": test_date,
        "total_trades": total,
        "success": success,
        "failure": failure,
        "breakeven": breakeven,
        "win_rate_pct": win_rate,
        "failure_rate_pct": failure_rate,
        "avg_pnl_pct": avg_pnl,
        "setup_timeframe": "1min",
        "trigger_timeframe": "1min",
        "setup_filter": "1m EMA+RSI+Supertrend",
        "trigger_filter": "1m Supertrend",
    }
    pd.DataFrame([summary]).to_csv(summary_path, index=False)
    return trades_path, monitor_path, scan_path, book_path, summary_path, summary


def run_backtest(test_date, expiry_code, results_dir=None, candle_mode="NORMAL"):
    sc = load_scanner_module()
    print(f"\nBACKTEST | {test_date} | 1m SETUP + 1m TRIGGER | expiry_code={expiry_code} | mode={candle_mode}\n")

    print("Loading NIFTY 1m...")
    nifty_1m = fetch_nifty_bars(sc.tsl, test_date, 1)

    test_day = pd.to_datetime(test_date).date()
    nifty_1m = nifty_1m[pd.to_datetime(nifty_1m["start_Time"]).dt.date == test_day].reset_index(drop=True)

    # Apply Candle Transformations
    import candle_transformer
    if candle_mode == "HEIKIN_ASHI":
        print("  Applying Heikin-Ashi candle transformation to NIFTY spot...")
        nifty_1m = candle_transformer.to_heikin_ashi(nifty_1m)
    elif candle_mode == "VOLUME":
        print("  Applying Volume candle transformation to NIFTY spot...")
        nifty_1m = candle_transformer.to_volume_candles(nifty_1m)

    print(f"  {len(nifty_1m)} x 1m candles")

    print(f"Loading options ({OPTION_BAR_TF}m LTP bars)...")
    legs = align_legs(fetch_option_legs(sc.tsl, test_date, expiry_code), len(nifty_1m) // OPTION_BAR_TF + 1)
    
    if candle_mode in ["HEIKIN_ASHI", "VOLUME"]:
        print(f"  Applying {candle_mode} candle transformation to options...")
        transformed_legs = []
        for leg in legs:
            series_dict = leg["series"]
            # Align array lengths (handles lists, numpy arrays, etc.) to prevent ValueError in DataFrame construction
            list_lengths = {k: len(v) for k, v in series_dict.items() if hasattr(v, "__len__") and not isinstance(v, (str, bytes, dict))}
            if list_lengths:
                common_len = max(list_lengths.values())
                cleaned_series = {}
                for k, v in series_dict.items():
                    if hasattr(v, "__len__") and not isinstance(v, (str, bytes, dict)):
                        v_list = list(v)
                        if len(v_list) == common_len:
                            cleaned_series[k] = v_list
                        elif len(v_list) < common_len:
                            cleaned_series[k] = v_list + [v_list[-1] if v_list else 0.0] * (common_len - len(v_list))
                        else:
                            cleaned_series[k] = v_list[:common_len]
                    else:
                        cleaned_series[k] = v
                df_leg = pd.DataFrame(cleaned_series)
            else:
                df_leg = pd.DataFrame(series_dict)

            if candle_mode == "HEIKIN_ASHI":
                df_leg = candle_transformer.to_heikin_ashi(df_leg)
            elif candle_mode == "VOLUME":
                df_leg = candle_transformer.to_volume_candles(df_leg)
            new_series = df_leg.to_dict(orient="list")
            transformed_legs.append({**leg, "series": new_series})
        legs = transformed_legs

    print(f"  {len(legs)} option series\n")

    trades = []
    monitor_rows = []
    scan_log = []
    trade_book = []
    in_trade_until = -1
    traded_symbols = set()

    session_indices = [
        i
        for i in range(len(nifty_1m))
        if bh.is_within_session(nifty_1m.iloc[i]["start_Time"])
    ]
    print(
        f"  Session scan: 09:15–15:30 IST | {len(session_indices)} x 1m bars "
        f"(hard exit {bh.MARKET_EXIT_TIME.strftime('%H:%M')})",
        flush=True
    )

    prev_close = float(nifty_1m.iloc[0]["close"])
    today_open = float(nifty_1m.iloc[session_indices[0]]["open"]) if session_indices else prev_close

    print("--- TRADES (1m trigger via Option_strategy_core) ---", flush=True)

    for i in session_indices:
        if i % 100 == 0:
            print(f"    [Scanning] bar {i}/{len(session_indices)} completed...", flush=True)

        if i <= in_trade_until:
            continue

        bar_time = nifty_1m.iloc[i]["start_Time"]
        chain = build_chain_at_bar(legs, option_bar_idx(i), test_date, "NIFTY")
        df_slice = bh.prepare_nifty_1m(nifty_1m.iloc[: i + 1]) if len(nifty_1m.iloc[: i + 1]) >= 30 else None
        pcr = bh.pcr_from_chain(chain) if chain else 1.0
        gap_mode = risk_engine.detect_gap_risk(prev_close, today_open)

        best_ce_score = best_pe_score = None
        trigger_ce = trigger_pe = False
        pick = None

        if chain and df_slice is not None:
            # FORCE REAL-TIME ACCURATE SPOT PRICE
            true_spot = df_slice.iloc[-1]["close"]
            atm = round(true_spot / 50) * 50
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
                ot = opt["option_type"]
                fired = core.detect_trigger_1m(
                    df_slice, ot, opt_row, true_spot,
                    prev_close, today_open, pcr, pd.DataFrame(chain["options"]) if chain else None
                )
                score = core.build_score(opt_row, ot, df_slice, pcr, gap_mode)
                if ot == "CE":
                    best_ce_score = score if best_ce_score is None else max(best_ce_score, score)
                    trigger_ce = trigger_ce or fired
                else:
                    best_pe_score = score if best_pe_score is None else max(best_pe_score, score)
                    trigger_pe = trigger_pe or fired
                if fired and score >= core.STRONG_BUY_THRESHOLD:
                    if pick is None or score > pick.get("score_pct", 0):
                        pick = {**opt, "score_pct": score, "strategy_suffix": opt_row.get("strategy_suffix", "")}

        scan_log.append({
            "datetime_ist": bh.format_ist(bar_time),
            "best_ce_score": best_ce_score if best_ce_score is not None else "",
            "best_pe_score": best_pe_score if best_pe_score is not None else "",
            "trigger_1m_ce": trigger_ce,
            "trigger_1m_pe": trigger_pe,
            "entry_allowed": bh.is_entry_time_allowed(bar_time),
        })

        if not chain or df_slice is None or not pick:
            continue

        if not bh.is_entry_time_allowed(bar_time):
            continue

        if pick["display_symbol"] in traded_symbols:
            continue

        trade = simulate_trade(pick, i, nifty_1m, legs, test_date)
        trades.append({k: v for k, v in trade.items() if k not in ("monitor_log", "trade_book")})
        for m in trade["monitor_log"]:
            monitor_rows.append({"symbol": trade["symbol"], **m})
        trade_book.extend(trade["trade_book"])

        traded_symbols.add(pick["display_symbol"])
        in_trade_until = i + len(trade["monitor_log"])

        ts = trade["entry_time_ist"]
        print(
            f"[{ts}] BUY {pick['display_symbol']} score={pick.get('score_pct')} "
            f"-> {trade['outcome']} ({trade['exit_reason']}) PnL {trade['pnl_pct']}%",
            flush=True,
        )

    paths = export_results(
        test_date, trades, monitor_rows, scan_log, trade_book, results_dir=results_dir
    )
    trades_path, monitor_path, scan_path, book_path, summary_path, summary = paths

    print("\n--- RESULTS SUMMARY ---")
    print(f"Date           : {test_date}")
    print(f"Total trades   : {summary['total_trades']}")
    print(f"SUCCESS        : {summary['success']}")
    print(f"FAILURE        : {summary['failure']}")
    print(f"Win rate       : {summary['win_rate_pct']}%")
    print(f"Failure rate   : {summary['failure_rate_pct']}%")
    print(f"Avg PnL        : {summary['avg_pnl_pct']}%")
    print("\nCSV files (IST):")
    print(f"  Trades      -> {trades_path}")
    print(f"  Trade Book  -> {book_path}  (BUY + SELL rows for P&L)")
    print(f"  Monitor     -> {monitor_path}")
    print(f"  Scan log    -> {scan_path}")
    print(f"  Summary     -> {summary_path}")

    print(f"\nScan log rows: {len(scan_log)} (expect ~375 for full 09:15–15:30 session)")

    if not trades:
        print("\nNo trades triggered. Try another date or EXPIRY_CODE (0-3).")

    return trades, summary


if __name__ == "__main__":
    date = sys.argv[1] if len(sys.argv) > 1 else TEST_DATE
    try:
        run_backtest(date, EXPIRY_CODE)
    except KeyboardInterrupt:
        print("\nStopped.", flush=True)
    except Exception as e:
        print(f"\nBACKTEST FAILED: {e}", flush=True)
        traceback.print_exc()
        raise SystemExit(1)
