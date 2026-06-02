import time
import datetime
import os
import json
import sys
import traceback
import pandas as pd
from dotenv import load_dotenv
from event_bus import signal_queue, dashboard_queue

def log_dashboard(message, level="info"):
    dashboard_queue.put({"type": "LOG", "payload": {"source": "Scanner", "message": message, "level": level}})

_last_atr_fetch_time = 0
_cached_atr_payload = "WAITING"

def push_atr_to_dashboard(tsl):
    global _last_atr_fetch_time, _cached_atr_payload
    now = time.time()
    if now - _last_atr_fetch_time > 3600: # 1 hour cache
        try:
            df = tsl.get_intraday_data("NIFTY", "NSE", 60)
            if df is not None and not df.empty:
                df['date'] = pd.to_datetime(df['timestamp']).dt.date if 'timestamp' in df.columns else pd.to_datetime(df['start_Time']).dt.date
                df['high'] = pd.to_numeric(df['high'])
                df['low'] = pd.to_numeric(df['low'])
                df['close'] = pd.to_numeric(df['close'])
                df = df.groupby('date').agg({'high': 'max', 'low': 'min', 'close': 'last'}).reset_index()
                df['prev_close'] = df['close'].shift(1)
                tr = pd.DataFrame({'tr1': df['high'] - df['low'], 'tr2': (df['high'] - df['prev_close']).abs(), 'tr3': (df['low'] - df['prev_close']).abs()}).max(axis=1)
                atr = tr.ewm(alpha=1/14, adjust=False).mean()
                latest_atr = float(atr.iloc[-1])
                _cached_atr_payload = f"{latest_atr:.1f} pts"
                _last_atr_fetch_time = now
        except Exception:
            pass
            
    dashboard_queue.put({"type": "MARKET_ATR", "payload": _cached_atr_payload})

def push_ticker_to_dashboard(chain_data):
    if not chain_data or not isinstance(chain_data, dict) or not chain_data.get("options"):
        return
    atm = chain_data.get("atm")
    if not atm: return
    step = 50
    target_strikes = [atm - step, atm, atm + step]
    
    ticker_data = []
    for opt in chain_data["options"]:
        if float(opt.get("strike", 0)) in target_strikes:
            prev_oi = opt.get("previous_oi") or 1
            oi_change = opt.get("oi_change", 0)
            oi_pct = (oi_change / prev_oi * 100) if prev_oi > 0 else 0
            prev_close = float(opt.get("previous_close") or opt.get("close") or 0.0)
            ltp = float(opt.get("ltp") or 0.0)
            premium_pct = ((ltp - prev_close) / prev_close * 100) if prev_close > 0 else 0.0
            
            eff_premium_dir = premium_pct
            if eff_premium_dir == 0.0:
                opt_vwap = float(opt.get("option_vwap") or 0.0)
                if opt_vwap > 0:
                    eff_premium_dir = 1 if ltp > opt_vwap else -1
                    
            oi_structure = "-"
            if eff_premium_dir >= 0 and oi_pct > 0:
                oi_structure = "Long Buildup"
            elif eff_premium_dir < 0 and oi_pct > 0:
                oi_structure = "Fresh Writing"
            elif eff_premium_dir > 0 and oi_pct <= 0:
                oi_structure = "Short Covering"
            elif eff_premium_dir <= 0 and oi_pct <= 0:
                oi_structure = "Long Unwinding"

            ticker_data.append({
                "symbol": opt.get("symbol", ""),
                "type": opt.get("option_type", ""),
                "strike": opt.get("strike", 0),
                "ltp": ltp,
                "volume": opt.get("volume", 0),
                "oi_change_pct": oi_pct,
                "oi_change": oi_change,
                "premium_change_pct": premium_pct,
                "oi_structure": oi_structure,
                "option_vwap": opt.get("option_vwap", 0.0)
            })
            
    ticker_data = sorted(ticker_data, key=lambda x: (x["type"] == "PE", x["strike"]))
    payload = {
        "spot": chain_data.get("spot", 0.0),
        "underlying": chain_data.get("underlying", "NIFTY"),
        "options": ticker_data
    }
    dashboard_queue.put({"type": "CHAIN_TICKER", "payload": payload})

import Option_strategy_core as core
import Chain_Analyzer
import Theta_Dodge
import Order_Book_Imbalance
from Dhan_Tradehull import Tradehull
from indicator_engine import calculate_rsi, calculate_rsi_series, add_adx
from System_Config import (
    UNDERLYING, STRIKE_RANGE, SENSEX_CHAIN_ENABLED, SENSEX_UNDERLYING,
    SENSEX_STRIKE_RANGE, MIN_BARS, STRONG_BUY_THRESHOLD, MUTE_RELEASE_SEC,
    ADX_CHOP_THRESHOLD
)
from scanner_excel import hourly_log, oi_volume_log, play_alert_sound, print_alert_sound_help, run_oi_volume_monitor

from scanner_state import set_shared_state, get_shared_state, maybe_release_stale_mute, await_915_market_open
from market_data_engine import get_nifty_1m_cached, calculate_live_pcr, fetch_chain, fetch_sensex_chain, chains_for_excel
from excel_sync_engine import sync_excel_ltp, xw
from logging_engine import log_rsi_trend_mismatch, log_rsi_band_alerts, print_heartbeat

from broker_client import get_live_client

_tsl = None
_candle_none_streak = 0


def _ensure_tsl():
    global _tsl
    if _tsl is None:
        _tsl = get_live_client()
        if not _tsl:
            raise RuntimeError(
                "Dhan auth failed (likely expired token). Update `cred.env` with a fresh "
                "DHAN_TOKEN_ID and restart."
            )
    return _tsl

def process_options_chain(chain_df, spot, underlying):
    if chain_df is not None and not chain_df.empty:
        Chain_Analyzer.process_and_analyze_chain(chain_df, spot, core, underlying=underlying)

def build_and_evaluate_candidate(tsl, candidate, target_type, df_1m, pcr_val, chain, nifty_spot, previous_close, today_open, st_color):
    score, _ = core.build_and_score_contract(candidate, target_type, df_1m, pcr_val)
    
    if score < core.WATCHLIST_THRESHOLD:
        return False
        
    action_label = "Watchlist"
    if score >= core.STRONG_BUY_THRESHOLD:
        action_label = "Strong Buy"
    elif score >= core.BUY_THRESHOLD:
        action_label = "Buy"

    chain_df = pd.DataFrame(chain.get("options", [])) if chain else None
    passed, reason, _ = core.explain_trigger_failure(df_1m, target_type, candidate, nifty_spot, previous_close, today_open, pcr_val, chain_df)
    
    # Log rejections for actionable scores
    if not passed and score >= core.BUY_THRESHOLD:
        log_dashboard(f"[scan] {candidate.get('symbol')} score={score} ({action_label}) reject: {reason}")
        print(f"[scan] {candidate.get('symbol')} score={score} ({action_label}) reject: {reason}", flush=True)
        hourly_log.log("REJECT", symbol=candidate.get("symbol"), option_type=target_type, score=score, reject_reason=reason, rsi=round(calculate_rsi(df_1m), 1), trend=st_color, pcr=pcr_val, nifty_spot=nifty_spot)
    elif score >= core.WATCHLIST_THRESHOLD and score < core.BUY_THRESHOLD:
        log_dashboard(f"[*] {candidate.get('symbol')} on Watchlist (Score: {score})", level="info")
        print(f"[*] {candidate.get('symbol')} on Watchlist (Score: {score})", flush=True)
    
    # 1. CORE STRATEGY (Momentum Breakout)
    if score >= core.BUY_THRESHOLD:
        if core.detect_trigger_1m(df_1m, target_type, candidate, nifty_spot, previous_close, today_open, pcr_val, chain_df):
            log_dashboard(f"🔥 SIGNAL VERIFIED! Score: {score} on {candidate['symbol']} ({action_label}). Handing off to Main Engine.", level="success")
            print(f"\n🔥 SIGNAL VERIFIED! Score: {score} on {candidate['symbol']} ({action_label}). Handing off to Main Engine.", flush=True)
            hourly_log.log("SIGNAL_VERIFIED", symbol=candidate.get("symbol"), option_type=target_type, score=score, rsi=round(calculate_rsi(df_1m), 1), trend=st_color, pcr=pcr_val, nifty_spot=nifty_spot)
            play_alert_sound("buy")
            set_shared_state("MUTE")
            dashboard_queue.put({"type": "SCANNER_STATE", "payload": {"status": get_shared_state(), "mute_seconds_left": 0}})
            
            strategy_name = "core"
            if candidate.get("strategy_suffix") == "(U)":
                strategy_name = "Uptrend"
            elif candidate.get("strategy_suffix") == "(D)":
                strategy_name = "Downtrend"
            signal_data = {
                "symbol": str(candidate["symbol"]),
                "option_type": str(candidate["option_type"]),
                "score": int(score),
                "strategy": strategy_name,
                "strategy_suffix": candidate.get("strategy_suffix", "")
            }
            signal_queue.put(signal_data)
            dashboard_queue.put({"type": "NEW_SIGNAL", "payload": {"symbol": candidate["symbol"], "type": target_type, "action": "BUY", "time": datetime.datetime.now().strftime("%H:%M:%S"), "strategy": strategy_name}})
            log_dashboard(f"[+] Signal passed to Main Engine for {candidate['symbol']} (score {score}) via signal_queue")
            print(f"[+] Signal passed to Main Engine for {candidate['symbol']} (score {score}) via signal_queue", flush=True)
            return True

    # 2. THETA-DODGE STRATEGY
    td_signal = Theta_Dodge.detect_scalp_signal(df_1m, tsl, candidate["symbol"])
    if td_signal and td_signal.get("option_type") == target_type:
        log_dashboard(f"🛡️ THETA-DODGE SIGNAL! Scalping {candidate['symbol']}.", level="success")
        print(f"\n🛡️ THETA-DODGE SIGNAL! Scalping {candidate['symbol']}.", flush=True)
        play_alert_sound("buy")
        set_shared_state("MUTE")
        dashboard_queue.put({"type": "SCANNER_STATE", "payload": {"status": get_shared_state(), "mute_seconds_left": 0}})
        
        signal_data = td_signal
        signal_data["symbol"] = str(candidate["symbol"])
        signal_data["score"] = int(score)
        signal_queue.put(signal_data)
        dashboard_queue.put({"type": "NEW_SIGNAL", "payload": {"symbol": candidate["symbol"], "type": target_type, "action": "BUY (Dodge)", "time": datetime.datetime.now().strftime("%H:%M:%S"), "strategy": "Theta_Dodge"}})
        return True

    # 3. ORDER BOOK IMBALANCE (OBI) STRATEGY
    obi_signal = Order_Book_Imbalance.detect_obi_signal(candidate, df_1m)
    if obi_signal and obi_signal.get("option_type") == target_type:
        log_dashboard(f"🌊 OBI SIGNAL! Imbalance detected on {candidate['symbol']}.", level="success")
        print(f"\n🌊 OBI SIGNAL! Imbalance detected on {candidate['symbol']}.", flush=True)
        play_alert_sound("buy")
        set_shared_state("MUTE")
        dashboard_queue.put({"type": "SCANNER_STATE", "payload": {"status": get_shared_state(), "mute_seconds_left": 0}})
        
        signal_data = obi_signal
        signal_data["symbol"] = str(candidate["symbol"])
        signal_data["score"] = int(score)
        signal_queue.put(signal_data)
        dashboard_queue.put({"type": "NEW_SIGNAL", "payload": {"symbol": candidate["symbol"], "type": target_type, "action": "BUY (OBI)", "time": datetime.datetime.now().strftime("%H:%M:%S"), "strategy": "Order_Book_Imbalance"}})
        return True

    return False

def market_scan_iteration():
    global _candle_none_streak
    tsl = _ensure_tsl()
    hourly_log.tick(scanner_state=get_shared_state())
    prev_state = get_shared_state()
    maybe_release_stale_mute()
    if get_shared_state() != prev_state:
        dashboard_queue.put({"type": "SCANNER_STATE", "payload": {"status": get_shared_state(), "mute_seconds_left": 0}})
    
    if datetime.datetime.now().time() > datetime.time(15, 30):
        log_dashboard("[─] Market closing hours reached. Scanner shutting down cleanly.")
        print("[─] Market closing hours reached. Scanner shutting down cleanly.", flush=True)
        raise SystemExit("Market closing hours reached.")

    if get_shared_state() == "MUTE":
        if SENSEX_CHAIN_ENABLED: fetch_sensex_chain(tsl)
        sync_excel_ltp(tsl, chains_for_excel())
        combined = chains_for_excel()
        if combined: run_oi_volume_monitor(combined)
        log_dashboard(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Scanner Status: MUTE (trade engine active. Sleeping...)")
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Scanner Status: MUTE (trade engine active. Sleeping...)", flush=True)
        time.sleep(5.0)
        return

    df_1m = get_nifty_1m_cached(tsl)
    if df_1m is None or df_1m.empty or len(df_1m) < MIN_BARS:
        # If candles repeatedly come back None, refresh the client (token can be rotated mid-run)
        if df_1m is None:
            _candle_none_streak += 1
        else:
            _candle_none_streak = 0
        if _candle_none_streak >= 3:
            log_dashboard("[!] NIFTY candles None 3x — refreshing Dhan client.", level="warning")
            print("[!] NIFTY candles None 3x — refreshing Dhan client.", flush=True)
            try:
                global _tsl
                _tsl = None
                tsl = _ensure_tsl()
            except Exception as e:
                log_dashboard(f"[!] Dhan re-init failed: {type(e).__name__}: {e}", level="error")
                print(f"[!] Dhan re-init failed: {type(e).__name__}: {e}", flush=True)

        if SENSEX_CHAIN_ENABLED: fetch_sensex_chain(tsl)
        sync_excel_ltp(tsl, chains_for_excel())
        log_dashboard(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Waiting for NIFTY 1m candles...")
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Waiting for NIFTY 1m candles...", flush=True)
        time.sleep(2.0)
        return

    chain = fetch_chain(tsl)
    sensex_chain = fetch_sensex_chain(tsl) if SENSEX_CHAIN_ENABLED else None
    
    # Auto strike refresh on websocket could go here, but omitted for length since sync_excel handles core
    excel_chain = chains_for_excel(chain)
    sync_excel_ltp(tsl, excel_chain)
    log_rsi_trend_mismatch(df_1m)
    run_oi_volume_monitor(excel_chain)

    if not chain or not isinstance(chain, dict) or "options" not in chain:
        time.sleep(2.0)
        return

    push_ticker_to_dashboard(chain)

    pcr_val = calculate_live_pcr(chain)
    nifty_spot = float(chain.get("spot") or 0)
    
    # Calculate today open / prev close
    day_dates = pd.to_datetime(df_1m["start_Time"]).dt.date
    today = day_dates.max()
    day_df = df_1m[day_dates == today]
    today_open = float(day_df.iloc[0]["open"]) if not day_df.empty else float(df_1m.iloc[0]["open"])
    prior = day_dates[day_dates < today]
    prev_df = df_1m[day_dates == prior.max()] if len(prior) > 0 else day_df
    previous_close = float(prev_df.iloc[-1]["close"])

    df_1m = add_adx(df_1m)
    st_color = str(df_1m.iloc[-2]["st_color"]).upper() if "st_color" in df_1m.columns else ("GREEN" if ("supertrend" in df_1m.columns and df_1m.iloc[-2]["close"] >= df_1m.iloc[-2]["supertrend"]) else "?")
    if st_color == "?":
        time.sleep(2.0); return

    current_adx = float(df_1m.iloc[-2]["ADX"]) if "ADX" in df_1m.columns else 25.0
    if current_adx < ADX_CHOP_THRESHOLD:
        market_trend = "SIDEWAYS"
    else:
        market_trend = "UP" if st_color == "GREEN" else "DOWN"
    
    dashboard_queue.put({"type": "MARKET_TREND", "payload": market_trend})
    push_atr_to_dashboard(tsl)

    target_type = "CE" if st_color == "GREEN" else "PE"
    log_rsi_band_alerts(df_1m, target_type, st_color)

    options_list = chain.get("options", [])
    atm = round(nifty_spot / 50) * 50
    target_strike = (atm - 100) if target_type == "CE" else (atm + 100)
    valid_options = [
        o for o in options_list 
        if isinstance(o, dict) and o.get("option_type") == target_type and int(o.get("strike", 0)) == int(target_strike)
    ]
    
    if options_list:
        process_options_chain(pd.DataFrame(options_list), nifty_spot, UNDERLYING)
    if SENSEX_CHAIN_ENABLED and sensex_chain:
        sx_opts = sensex_chain.get("options", [])
        if sx_opts:
            process_options_chain(pd.DataFrame(sx_opts), float(sensex_chain.get("spot") or 0), SENSEX_UNDERLYING)

    trigger_found = False
    for candidate in valid_options:
        if build_and_evaluate_candidate(tsl, candidate, target_type, df_1m, pcr_val, chain, nifty_spot, previous_close, today_open, st_color):
            trigger_found = True
            break

    print_heartbeat(df_1m, chain, target_type, valid_options, trigger_found, pcr_val)
    time.sleep(3.0)

def main():
    set_shared_state("SCAN")
    dashboard_queue.put({"type": "SCANNER_STATE", "payload": {"status": get_shared_state(), "mute_seconds_left": 0}})
    await_915_market_open()
    log_dashboard("[+] Continuous Market Signal Monitoring Active...")
    print("[+] Continuous Market Signal Monitoring Active...", flush=True)
    hourly_log.print_startup_info()
    oi_volume_log.print_startup_info()
    print_alert_sound_help()
    
    while True:
        try:
            market_scan_iteration()
        except Exception as e:
            log_dashboard(f"[-] Scanner Runtime Error Alert: {e}", level="error")
            print(f"[-] Scanner Runtime Error Alert: {e}", flush=True)
            traceback.print_exc()
            time.sleep(5.0)

if __name__ == "__main__":
    main()
