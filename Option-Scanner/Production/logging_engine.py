import time
import datetime
import pandas as pd
import sys
from System_Config import (
    CE_RSI_MIN, CE_RSI_MAX,
    PE_RSI_MIN, PE_RSI_MAX
)
from indicator_engine import calculate_rsi
from scanner_excel import hourly_log, play_alert_sound

_rsi_mismatch_last_log = 0.0
_rsi_band_alert_last = 0.0
_rsi_prev_value = None
_heartbeat_last_print = 0.0
_HEARTBEAT_INTERVAL = 30.0

# Prevent Windows console cp1252 UnicodeEncodeError (emojis/box-drawing chars).
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

def log_rsi_trend_mismatch(df_1m: pd.DataFrame) -> None:
    global _rsi_mismatch_last_log
    if df_1m is None or df_1m.empty or len(df_1m) < 2: return
    now = time.time()
    if now - _rsi_mismatch_last_log < 30: return
    
    if "st_color" in df_1m.columns: st_color = str(df_1m.iloc[-2]["st_color"]).upper()
    elif "supertrend" in df_1m.columns: st_color = "GREEN" if df_1m.iloc[-2]["close"] >= df_1m.iloc[-2]["supertrend"] else "RED"
    else: return
    
    rsi = calculate_rsi(df_1m)
    msg = None
    if CE_RSI_MIN <= rsi <= CE_RSI_MAX and st_color == "RED":
        msg = f"[i] RSI {rsi:.1f} in CE band ({CE_RSI_MIN}-{CE_RSI_MAX}) but trend RED — scanning PE only (PE needs RSI {PE_RSI_MIN}-{PE_RSI_MAX})"
    elif PE_RSI_MIN <= rsi <= PE_RSI_MAX and st_color == "GREEN":
        msg = f"[i] RSI {rsi:.1f} in PE band ({PE_RSI_MIN}-{PE_RSI_MAX}) but trend GREEN — scanning CE only (CE needs RSI {CE_RSI_MIN}-{CE_RSI_MAX})"
    
    if msg:
        _rsi_mismatch_last_log = now
        print(msg, flush=True)

def log_rsi_band_alerts(df_1m: pd.DataFrame, target_type: str, st_color: str) -> None:
    global _rsi_band_alert_last, _rsi_prev_value
    if df_1m is None or df_1m.empty or len(df_1m) < 15: return
    now = time.time()
    if now - _rsi_band_alert_last < 30: return
    
    rsi = calculate_rsi(df_1m)
    prev = _rsi_prev_value
    _rsi_prev_value = rsi
    msg, cross = None, None
    
    if target_type == "CE":
        band = f"{CE_RSI_MIN}-{CE_RSI_MAX}"
        if rsi < CE_RSI_MIN:
            msg = f"NIFTY 1m RSI {rsi:.1f} below CE band ({band}) — CE buy signals blocked"
            if prev is not None and prev >= CE_RSI_MIN: cross = f"dropped from {prev:.1f} (left CE band)"
        elif rsi > CE_RSI_MAX:
            msg = f"NIFTY 1m RSI {rsi:.1f} above CE band ({band}) — CE buy signals blocked (overbought)"
            if prev is not None and prev <= CE_RSI_MAX: cross = f"rose from {prev:.1f} (left CE band)"
    else:
        band = f"{PE_RSI_MIN}-{PE_RSI_MAX}"
        if rsi < PE_RSI_MIN:
            msg = f"NIFTY 1m RSI {rsi:.1f} below PE band ({band}) — PE buy signals blocked"
            if prev is not None and prev >= PE_RSI_MIN: cross = f"dropped from {prev:.1f} (left PE band)"
        elif rsi > PE_RSI_MAX:
            msg = f"NIFTY 1m RSI {rsi:.1f} above PE band ({band}) — PE buy signals blocked"
            if prev is not None and prev <= PE_RSI_MAX: cross = f"rose from {prev:.1f} (left PE band)"
            
    if not msg: return
    _rsi_band_alert_last = now
    full = f"{msg}" + (f" [{cross}]" if cross else "")
    try:
        from live_alert_logger import write_live_alert
        write_live_alert("RSI", full)
    except Exception:
        pass
    play_alert_sound("indicator")
    try: hourly_log.log("RSI_BAND", option_type=target_type, rsi=round(rsi, 1), trend=st_color, reject_reason=cross or "outside_band", notes=full)
    except Exception: pass

def print_heartbeat(df_1m: pd.DataFrame, chain: dict, target_type: str, valid_options: list, trigger_found: bool, pcr_val: float) -> None:
    global _heartbeat_last_print
    if trigger_found: return
    now = time.time()
    if now - _heartbeat_last_print < _HEARTBEAT_INTERVAL: return
    _heartbeat_last_print = now
    
    nifty_spot = float(chain.get("spot") or 0)
    nifty_close = float(df_1m.iloc[-2]["close"]) if len(df_1m) >= 2 else 0
    st_color = str(df_1m.iloc[-2]["st_color"]).upper() if "st_color" in df_1m.columns else ("GREEN" if ("supertrend" in df_1m.columns and df_1m.iloc[-2]["close"] >= df_1m.iloc[-2]["supertrend"]) else "?")
    current_rsi = calculate_rsi(df_1m)
    atm_strike = chain.get("atm")
    atm_leg = next((o for o in valid_options if isinstance(o, dict) and o.get("strike") == atm_strike), valid_options[0] if valid_options else None)
    atm_ltp = atm_leg.get("ltp", 0) if isinstance(atm_leg, dict) else 0
    atm_sym = atm_leg.get("symbol", "-") if isinstance(atm_leg, dict) else "-"
    
    state_str = ""
    try:
        from analytics.timeframe_manager import CandleAggregator
        from analytics.state_engine import StateClassifier
        import indicator_engine as Indicators
        multi_dfs = CandleAggregator.resample_1m_to_multi(df_1m)
        df_3m, df_5m, df_10m = multi_dfs.get("3m", pd.DataFrame()), multi_dfs.get("5m", pd.DataFrame()), multi_dfs.get("10m", pd.DataFrame())
        if not df_10m.empty: df_10m = Indicators.add_ema(df_10m) 
        if not df_5m.empty: df_5m = Indicators.add_ema(df_5m)
        if not df_3m.empty: df_3m = Indicators.add_vwap(df_3m)
        if "EMA9" in df_10m.columns: df_10m["ema_9"] = df_10m["EMA9"]
        if "EMA9" in df_5m.columns: df_5m["ema_9"] = df_5m["EMA9"]
        if "EMA20" in df_5m.columns: df_5m["ema_21"] = df_5m["EMA20"]
        if "VWAP" in df_3m.columns: df_3m["vwap"] = df_3m["VWAP"]
        
        regime = StateClassifier.classify_10m_regime(df_10m)
        structure = StateClassifier.classify_5m_structure(df_5m)
        confirmation = StateClassifier.classify_3m_confirmation(df_3m)
        execution = StateClassifier.classify_1m_execution(df_1m)
        state_str = f"   └── [SEDA] 10m:{regime.market_regime} | 5m:{structure.trend_structure} | 3m:{confirmation.vwap_state} | 1m:{execution.momentum_velocity}"
    except Exception as e:
        state_str = f"   └── [SEDA Error] {str(e)}"

    try:
        from system_health import system_health
        health_status = system_health.get_health_status()
    except Exception:
        health_status = "Unknown"

    try:
        print(
            f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [Health: {health_status}] "
            f"NIFTY 1m: {nifty_close} | Spot: {nifty_spot} | ATM {target_type} {atm_sym} @ {atm_ltp} | "
            f"RSI: {round(current_rsi, 1)} | Trend: {st_color} | PCR: {pcr_val}\n"
            f"{state_str}",
            flush=True,
        )
    except UnicodeEncodeError:
        print(
            f"[{datetime.datetime.now().strftime('%H:%M:%S')}] [Health: {health_status}] "
            f"NIFTY 1m: {nifty_close} | Spot: {nifty_spot} | ATM {target_type} {atm_sym} @ {atm_ltp} | "
            f"RSI: {round(current_rsi, 1)} | Trend: {st_color} | PCR: {pcr_val}\n"
            f"{state_str}".encode('ascii', 'replace').decode('ascii'),
            flush=True,
        )
