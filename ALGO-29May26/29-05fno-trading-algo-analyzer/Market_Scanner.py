import time
import datetime
import os
import json
import sys
import traceback
import pandas as pd
from dotenv import load_dotenv

import Option_strategy_core as core
import Chain_Analyzer
from Dhan_Tradehull import Tradehull
from indicator_engine import calculate_rsi, calculate_rsi_series
from System_Config import *
from scanner_excel import hourly_log, oi_volume_log, play_alert_sound, print_alert_sound_help, run_oi_volume_monitor

from scanner_state import set_shared_state, get_shared_state, maybe_release_stale_mute, await_915_market_open
from market_data_engine import get_nifty_1m_cached, calculate_live_pcr, fetch_chain, fetch_sensex_chain, chains_for_excel
from excel_sync_engine import sync_excel_ltp, xw
from logging_engine import log_rsi_trend_mismatch, log_rsi_band_alerts, print_heartbeat

# Core indicator hook
core.calculate_rsi = calculate_rsi
core.calculate_rsi_series = calculate_rsi_series

load_dotenv("cred.env")
tsl = Tradehull(os.getenv("DHAN_CLIENT_CODE"), os.getenv("DHAN_TOKEN_ID"))

def process_options_chain(chain_df, spot, underlying):
    if chain_df is not None and not chain_df.empty:
        Chain_Analyzer.process_and_analyze_chain(chain_df, spot, core, underlying=underlying)

def build_and_evaluate_candidate(candidate, target_type, df_1m, pcr_val, chain, nifty_spot, previous_close, today_open, st_color):
    score, _ = core.build_and_score_contract(candidate, target_type, df_1m, pcr_val)
    if score >= 70:
        chain_df = pd.DataFrame(chain.get("options", [])) if chain else None
        passed, reason, _ = core.explain_trigger_failure(df_1m, None, target_type, candidate, nifty_spot, previous_close, today_open, pcr_val, chain_df)
        if not passed and score >= core.STRONG_BUY_THRESHOLD:
            print(f"[scan] {candidate.get('symbol')} score={score} reject: {reason}", flush=True)
            hourly_log.log("REJECT", symbol=candidate.get("symbol"), option_type=target_type, score=score, reject_reason=reason, rsi=round(calculate_rsi(df_1m), 1), trend=st_color, pcr=pcr_val, nifty_spot=nifty_spot)
    
    if score >= core.STRONG_BUY_THRESHOLD:
        chain_df = pd.DataFrame(chain.get("options", [])) if chain else None
        if core.detect_trigger_1m(df_1m, None, target_type, candidate, nifty_spot, previous_close, today_open, pcr_val, chain_df):
            print(f"\n🔥 SIGNAL VERIFIED! Score: {score} on {candidate['symbol']}. Handing off to Main Engine.", flush=True)
            hourly_log.log("SIGNAL_VERIFIED", symbol=candidate.get("symbol"), option_type=target_type, score=score, rsi=round(calculate_rsi(df_1m), 1), trend=st_color, pcr=pcr_val, nifty_spot=nifty_spot)
            play_alert_sound("buy")
            set_shared_state("MUTE")
            
            signal_data = {"symbol": str(candidate["symbol"]), "option_type": str(candidate["option_type"]), "score": int(score)}
            signal_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "signal.json")
            try:
                with open(signal_path, "w") as f: json.dump(signal_data, f)
                print(f"[+] Signal passed to Main Engine for {candidate['symbol']} (score {score}) via signal.json", flush=True)
            except Exception as e:
                print(f"[-] Error writing signal.json: {e}", flush=True)
                set_shared_state("SCAN")
            return True
    return False

def market_scan_iteration():
    hourly_log.tick(scanner_state=get_shared_state())
    maybe_release_stale_mute()
    
    if datetime.datetime.now().time() > datetime.time(15, 30):
        print("[─] Market closing hours reached. Scanner shutting down cleanly.", flush=True)
        sys.exit(0)

    if get_shared_state() == "MUTE":
        if SENSEX_CHAIN_ENABLED: fetch_sensex_chain(tsl)
        sync_excel_ltp(tsl, chains_for_excel())
        combined = chains_for_excel()
        if combined: run_oi_volume_monitor(combined)
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Scanner Status: MUTE (trade engine active. Sleeping...)", flush=True)
        time.sleep(5.0)
        return

    df_1m = get_nifty_1m_cached(tsl)
    if df_1m is None or df_1m.empty or len(df_1m) < MIN_BARS:
        if SENSEX_CHAIN_ENABLED: fetch_sensex_chain(tsl)
        sync_excel_ltp(tsl, chains_for_excel())
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

    st_color = str(df_1m.iloc[-2]["st_color"]).upper() if "st_color" in df_1m.columns else ("GREEN" if ("supertrend" in df_1m.columns and df_1m.iloc[-2]["close"] >= df_1m.iloc[-2]["supertrend"]) else "?")
    if st_color == "?":
        time.sleep(2.0); return

    target_type = "CE" if st_color == "GREEN" else "PE"
    log_rsi_band_alerts(df_1m, target_type, st_color)

    options_list = chain.get("options", [])
    valid_options = [o for o in options_list if isinstance(o, dict) and o.get("option_type") == target_type]
    
    if options_list:
        process_options_chain(pd.DataFrame(options_list), nifty_spot, UNDERLYING)
    if SENSEX_CHAIN_ENABLED and sensex_chain:
        sx_opts = sensex_chain.get("options", [])
        if sx_opts:
            process_options_chain(pd.DataFrame(sx_opts), float(sensex_chain.get("spot") or 0), SENSEX_UNDERLYING)

    trigger_found = False
    for candidate in valid_options:
        if build_and_evaluate_candidate(candidate, target_type, df_1m, pcr_val, chain, nifty_spot, previous_close, today_open, st_color):
            trigger_found = True
            break

    print_heartbeat(df_1m, chain, target_type, valid_options, trigger_found, pcr_val)
    time.sleep(3.0)

def main():
    set_shared_state("SCAN")
    await_915_market_open()
    print("[+] Continuous Market Signal Monitoring Active...", flush=True)
    hourly_log.print_startup_info()
    oi_volume_log.print_startup_info()
    print_alert_sound_help()
    
    while True:
        try:
            market_scan_iteration()
        except Exception as e:
            print(f"[-] Scanner Runtime Error Alert: {e}", flush=True)
            traceback.print_exc()
            time.sleep(5.0)

if __name__ == "__main__":
    main()
