import time
import datetime
import os
import json
import subprocess
import sys
import threading
import SafetyLogger
from dotenv import load_dotenv
from Dhan_Tradehull import Tradehull
from System_Config import MUTE_RELEASE_SEC

import pandas as pd
import Indicators
from Indicators import calculate_rsi, calculate_rsi_series

import Option_strategy_core as core
import RiseFall_sub as rise_fall

CE_RSI_MIN = rise_fall.CE_RSI_LOWER_BAND
CE_RSI_MAX = 74.0
PE_RSI_MIN = 26.0
PE_RSI_MAX = rise_fall.PE_RSI_UPPER_BAND

# Legacy paths use core.calculate_rsi — always bind to Indicators
core.calculate_rsi = calculate_rsi
core.calculate_rsi_series = calculate_rsi_series

from scanner_excel import (
    build_chain_maps,
    build_combined_chain,
    build_quote_map_from_chain,
    clean_rows,
    ensure_sheet_quote_headers,
    fetch_active_expiries,
    filter_chain_strike_window,
    hourly_log,
    merge_quote_rows,
    oi_volume_log,
    run_oi_volume_monitor,
    play_alert_sound,
    print_alert_sound_help,
    quote_row_from_chain_option,
    refresh_strike_window_on_websocket,
    is_fno_symbol,
    strike_window_symbols,
)

try:
    import xlwings as xw
except ImportError:
    xw = None

load_dotenv("cred.env")
client_code = os.getenv("DHAN_CLIENT_CODE")
token_id = os.getenv("DHAN_TOKEN_ID")

tsl = Tradehull(client_code, token_id)

from System_Config import *

_EXCEL_STATUS_INTERVAL = 30.0
_HEARTBEAT_INTERVAL = 30.0
_WATCHLIST_PRINT_INTERVAL = 15.0
_excel_sync_last_status = 0.0
_heartbeat_last_print = 0.0
_watchlist_last_print = 0.0
_rsi_mismatch_last_log = 0.0
_rsi_band_alert_last = 0.0
_rsi_prev_value = None
_chain_fail_last_log = 0.0
_last_chain = None
_last_expiry = None
_last_sensex_chain = None
_last_sensex_expiry = None
_sensex_chain_fail_last_log = 0.0
_intraday_cache = {"t": 0.0, "df": None}
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_WEBSOCKET_XLSX = os.path.join(_SCRIPT_DIR, "Websocket.xlsx")


def set_shared_state(status_str):
    try:
        with open(STATE_FILE, "w") as f:
            json.dump({"status": status_str, "updated_at": time.time()}, f)
    except Exception as e:
        print(f"[-] Shared state write failure: {e}", flush=True)


def get_shared_state():
    try:
        with open(STATE_FILE, "r") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data.get("status", "SCAN")
            return "SCAN"
    except Exception:
        return "SCAN"


def maybe_release_stale_mute():
    if not os.path.exists(STATE_FILE):
        return
    try:
        with open(STATE_FILE, "r") as f:
            data = json.load(f)
        if data.get("status") != "MUTE":
            return
        updated = float(data.get("updated_at", 0))
        if time.time() - updated > MUTE_RELEASE_SEC:
            set_shared_state("SCAN")
    except Exception:
        pass


def _log_excel_sync(updated, total, message=None):
    global _excel_sync_last_status
    now = time.time()
    if now - _excel_sync_last_status < _EXCEL_STATUS_INTERVAL:
        return
    _excel_sync_last_status = now
    if message:
        print(f"[!] Excel LTP sync: {message}", flush=True)
    elif total == 0:
        print("[!] Excel LTP sync: sheet empty (no rows in column A).", flush=True)
    elif updated == 0:
        print(
            f"[!] Excel LTP sync: 0/{total} rows updated "
            "(open Websocket.xlsx in Excel or check symbols/REST).",
            flush=True,
        )
    elif updated < total:
        print(
            f"[i] Excel LTP sync: {updated}/{total} rows "
            f"({total - updated} still unmatched).",
            flush=True,
        )


def _websocket_workbook():
    if not xw:
        return None
    for opener in (
        lambda: xw.books["Websocket.xlsx"],
        lambda: xw.Book("Websocket.xlsx"),
        lambda: xw.Book(_WEBSOCKET_XLSX),
    ):
        try:
            wb = opener()
            if wb is not None:
                return wb
        except Exception:
            pass
    return None


def _sheet_last_data_row(sheet, max_scan=500):
    """Last row with a symbol in column A (handles gaps; avoids .end('down') stopping early)."""
    try:
        vals = sheet.range(f"A1:A{max_scan}").value
    except Exception:
        return 1
    if not isinstance(vals, list):
        vals = [vals]
    last = 1
    for i, v in enumerate(vals, start=1):
        if v is None:
            continue
        sym = str(v).strip()
        if not sym or sym.lower() == "nan":
            continue
        if i == 1 and sym.lower() in ("script name", "symbol", "script"):
            continue
        last = i
    return last


def _normalize_sheet_exchange(sym, exch):
    exch = str(exch or "NSE").strip().upper()
    alias = {
        "NSE_FNO": "NFO",
        "NSE FNO": "NFO",
        "NSE_EQ": "NSE",
        "EQ": "NSE",
        "BSE_FNO": "BFO",
        "IDX_I": "NSE_IDX",
    }
    exch = alias.get(exch, exch)
    if is_fno_symbol(sym) and exch in ("NSE", "NSE_EQ", ""):
        exch = "NFO"
    return exch


def print_watchlist_scan(watchlist_rows, ltps_by_row):
    global _watchlist_last_print
    if not watchlist_rows:
        return
    now = time.time()
    if now - _watchlist_last_print < _WATCHLIST_PRINT_INTERVAL:
        return
    _watchlist_last_print = now
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] ── Watchlist scan ({len(watchlist_rows)} rows, top → bottom) ──", flush=True)
    for idx, (sym, exch) in enumerate(watchlist_rows, start=1):
        ltp = ltps_by_row.get(idx)
        if ltp is not None and float(ltp) > 0:
            print(f"  {idx:2}. {sym:<28} {exch:<8} {float(ltp):.2f}", flush=True)
        else:
            print(f"  {idx:2}. {sym:<28} {exch:<8} —", flush=True)
    print(flush=True)


def sync_excel_ltp(tsl, chain=None):
    watchlist_rows = []
    ltps_by_row = {}
    if not SYNC_EXCEL_LTP or not xw:
        return watchlist_rows, ltps_by_row
    wb = _websocket_workbook()
    if wb is None:
        _log_excel_sync(
            0,
            0,
            "Websocket.xlsx not open — start Excel with file in Option Scanner folder",
        )
        return watchlist_rows, ltps_by_row
    try:
        sheet = wb.sheets["LTP"]
        ensure_sheet_quote_headers(sheet)
        last_row = _sheet_last_data_row(sheet)
        df = sheet.range(f"A1:B{last_row}").options(pd.DataFrame, header=1, index=False).value
        if df is None or df.empty:
            _log_excel_sync(0, 0)
            return watchlist_rows, ltps_by_row
        name_col = "Script Name" if "Script Name" in df.columns else df.columns[0]
        exch_col = (
            "Exchange"
            if "Exchange" in df.columns
            else (df.columns[1] if len(df.columns) > 1 else None)
        )
        chain_for_ltp = chains_for_excel(chain if isinstance(chain, dict) else None)
        quote_map, oi_map = build_chain_maps(chain_for_ltp)
        for i in range(len(df)):
            sym = str(df[name_col].iloc[i]).strip()
            if not sym or sym.lower() == "nan":
                continue
            exch = "NSE"
            if exch_col is not None:
                exch = str(df[exch_col].iloc[i] or "NSE").strip()
            watchlist_rows.append((sym, _normalize_sheet_exchange(sym, exch)))
        rest_quotes = (
            tsl.get_rest_quotes_for_watchlist(watchlist_rows, quiet=True)
            if watchlist_rows
            else {}
        )
        col_values = []
        oi_values = []
        updated = 0
        row_num = 0
        for i in range(len(df)):
            sym = str(df[name_col].iloc[i]).strip()
            if not sym or sym.lower() == "nan":
                col_values.append([None] * 8)
                oi_values.append([None, None])
                continue
            row_num += 1
            chain_row = quote_map.get(sym) or quote_map.get(sym.upper())
            opt_match = None
            if chain_row is None:
                for o in (chain_for_ltp or {}).get("options") or []:
                    if isinstance(o, dict) and str(o.get("symbol", "")).strip() == sym:
                        opt_match = o
                        chain_row = quote_row_from_chain_option(o)
                        break
            rest_row = rest_quotes.get(sym) or rest_quotes.get(sym.upper())
            row = merge_quote_rows(rest_row, chain_row)
            oi_row = oi_map.get(sym) or oi_map.get(sym.upper())
            if oi_row is None and opt_match:
                oi = int(opt_match.get("oi") or 0)
                prev = int(opt_match.get("previous_oi") or 0)
                oi_row = [oi, int(opt_match.get("oi_change") or (oi - prev))]
            if row[0] is not None:
                try:
                    if float(row[0]) > 0:
                        updated += 1
                        ltps_by_row[row_num] = float(row[0])
                except (TypeError, ValueError):
                    pass
            col_values.append(row)
            oi_values.append(oi_row if oi_row else [None, None])
        end_row = len(col_values) + 1
        if col_values:
            sheet.range(f"C2:J{end_row}").value = col_values
            sheet.range(f"K2:L{end_row}").value = oi_values
        _log_excel_sync(updated, len(watchlist_rows))
        print_watchlist_scan(watchlist_rows, ltps_by_row)
    except Exception as exc:
        _log_excel_sync(0, 0, str(exc))
    return watchlist_rows, ltps_by_row


def log_rsi_trend_mismatch(df_1m):
    global _rsi_mismatch_last_log
    if df_1m is None or df_1m.empty or len(df_1m) < 2:
        return
    now = time.time()
    if now - _rsi_mismatch_last_log < 30:
        return
    if "st_color" in df_1m.columns:
        st_color = str(df_1m.iloc[-2]["st_color"]).upper()
    elif "supertrend" in df_1m.columns:
        st_color = (
            "GREEN"
            if df_1m.iloc[-2]["close"] >= df_1m.iloc[-2]["supertrend"]
            else "RED"
        )
    else:
        return
    rsi = calculate_rsi(df_1m)
    msg = None
    if CE_RSI_MIN <= rsi <= CE_RSI_MAX and st_color == "RED":
        msg = (
            f"[i] RSI {rsi:.1f} in CE band ({CE_RSI_MIN}-{CE_RSI_MAX}) "
            f"but trend RED — scanning PE only (PE needs RSI {PE_RSI_MIN}-{PE_RSI_MAX})"
        )
    elif PE_RSI_MIN <= rsi <= PE_RSI_MAX and st_color == "GREEN":
        msg = (
            f"[i] RSI {rsi:.1f} in PE band ({PE_RSI_MIN}-{PE_RSI_MAX}) "
            f"but trend GREEN — scanning CE only (CE needs RSI {CE_RSI_MIN}-{CE_RSI_MAX})"
        )
    if msg:
        _rsi_mismatch_last_log = now
        print(msg, flush=True)


def log_rsi_band_alerts(df_1m, target_type, st_color):
    global _rsi_band_alert_last, _rsi_prev_value
    if df_1m is None or df_1m.empty or len(df_1m) < 15:
        return
    now = time.time()
    if now - _rsi_band_alert_last < 30:
        return
    rsi = calculate_rsi(df_1m)
    prev = _rsi_prev_value
    _rsi_prev_value = rsi
    msg = None
    cross = None
    if target_type == "CE":
        band = f"{CE_RSI_MIN}-{CE_RSI_MAX}"
        if rsi < CE_RSI_MIN:
            msg = (
                f"NIFTY 1m RSI {rsi:.1f} below CE band ({band}) — "
                "CE buy signals blocked"
            )
            if prev is not None and prev >= CE_RSI_MIN:
                cross = f"dropped from {prev:.1f} (left CE band)"
        elif rsi > CE_RSI_MAX:
            msg = (
                f"NIFTY 1m RSI {rsi:.1f} above CE band ({band}) — "
                "CE buy signals blocked (overbought)"
            )
            if prev is not None and prev <= CE_RSI_MAX:
                cross = f"rose from {prev:.1f} (left CE band)"
    else:
        band = f"{PE_RSI_MIN}-{PE_RSI_MAX}"
        if rsi < PE_RSI_MIN:
            msg = (
                f"NIFTY 1m RSI {rsi:.1f} below PE band ({band}) — "
                "PE buy signals blocked"
            )
            if prev is not None and prev >= PE_RSI_MIN:
                cross = f"dropped from {prev:.1f} (left PE band)"
        elif rsi > PE_RSI_MAX:
            msg = (
                f"NIFTY 1m RSI {rsi:.1f} above PE band ({band}) — "
                "PE buy signals blocked"
            )
            if prev is not None and prev <= PE_RSI_MAX:
                cross = f"rose from {prev:.1f} (left PE band)"
    if not msg:
        return
    _rsi_band_alert_last = now
    full = f"{msg}" + (f" [{cross}]" if cross else "")
    print(f"[rsi] {full}", flush=True)
    try:
        hourly_log.log(
            "RSI_BAND",
            option_type=target_type,
            rsi=round(rsi, 1),
            trend=st_color,
            reject_reason=cross or "outside_band",
            notes=full,
        )
    except Exception:
        pass


def print_heartbeat(df_1m, chain, target_type, valid_options, trigger_found):
    global _heartbeat_last_print
    if trigger_found:
        return
    now = time.time()
    if now - _heartbeat_last_print < _HEARTBEAT_INTERVAL:
        return
    _heartbeat_last_print = now
    pcr_val = calculate_live_pcr(chain)
    nifty_spot = float(chain.get("spot") or 0)
    nifty_close = float(df_1m.iloc[-2]["close"]) if len(df_1m) >= 2 else 0
    if "st_color" in df_1m.columns:
        st_color = str(df_1m.iloc[-2]["st_color"]).upper()
    elif "supertrend" in df_1m.columns:
        st_color = (
            "GREEN"
            if df_1m.iloc[-2]["close"] >= df_1m.iloc[-2]["supertrend"]
            else "RED"
        )
    else:
        st_color = "?"
    current_rsi = calculate_rsi(df_1m)
    atm_strike = chain.get("atm")
    atm_leg = next(
        (o for o in valid_options if isinstance(o, dict) and o.get("strike") == atm_strike),
        valid_options[0] if valid_options else None,
    )
    atm_ltp = atm_leg.get("ltp", 0) if isinstance(atm_leg, dict) else 0
    atm_sym = atm_leg.get("symbol", "-") if isinstance(atm_leg, dict) else "-"
    print(
        f"[{datetime.datetime.now().strftime('%H:%M:%S')}] "
        f"NIFTY 1m: {nifty_close} | Spot: {nifty_spot} | ATM {target_type} {atm_sym} @ {atm_ltp} | "
        f"RSI: {round(current_rsi, 1)} | Trend: {st_color} | PCR: {pcr_val}",
        flush=True,
    )


def get_nifty_1m_cached():
    global _intraday_cache
    now = time.time()
    if (
        _intraday_cache["df"] is not None
        and (now - _intraday_cache["t"]) < INTRADAY_CACHE_SEC
    ):
        return _intraday_cache["df"]
    df = tsl.get_intraday_data(UNDERLYING, "NSE", 1)
    if df is not None and not df.empty:
        df = tsl.add_supertrend(df, period=10, multiplier=3)
        _intraday_cache = {"t": now, "df": df}
    return df


def calculate_live_pcr(chain):
    if not chain or not isinstance(chain, dict) or "options" not in chain:
        return 1.0
    options = chain["options"]
    if not isinstance(options, list):
        return 1.0
    total_call_oi = sum(
        int(o.get("oi", 0))
        for o in options
        if isinstance(o, dict) and o.get("option_type") == "CE"
    )
    total_put_oi = sum(
        int(o.get("oi", 0))
        for o in options
        if isinstance(o, dict) and o.get("option_type") == "PE"
    )
    return round(total_put_oi / total_call_oi, 3) if total_call_oi > 0 else 1.0


def _fetch_index_chain(underlying, strike_range, expiry_ref, cache_attr, expiry_attr, fail_log_attr):
    """Fetch option chain for NIFTY or SENSEX; cache per underlying."""
    global _chain_fail_last_log, _sensex_chain_fail_last_log
    chain = tsl.get_option_chain(
        underlying=underlying,
        strike_range=strike_range,
        expiry=expiry_ref,
    )
    if chain and isinstance(chain, dict) and chain.get("options"):
        chain = filter_chain_strike_window(dict(chain))
        chain["_cached_at"] = time.time()
        globals()[cache_attr] = chain
        globals()[expiry_attr] = chain.get("expiry")
        return chain
    now = time.time()
    fail_last = globals().get(fail_log_attr, 0.0)
    if now - fail_last > 30:
        print(
            f"[!] {underlying} option chain fetch failed — retrying (using last cache if recent).",
            flush=True,
        )
        globals()[fail_log_attr] = now
    cached = globals().get(cache_attr)
    if cached:
        age = now - cached.get("_cached_at", 0)
        if age < 60:
            stale = dict(cached)
            fresh = tsl._rest_index_ltp(underlying)
            if fresh:
                stale["spot"] = fresh
                step = 100 if underlying in ("SENSEX", "BANKEX") else 50
                stale["atm"] = round(fresh / step) * step
            return stale
    return None


def fetch_chain(strike_range=None):
    return _fetch_index_chain(
        UNDERLYING,
        strike_range if strike_range is not None else STRIKE_RANGE,
        _last_expiry,
        "_last_chain",
        "_last_expiry",
        "_chain_fail_last_log",
    )


def fetch_sensex_chain(strike_range=None):
    if not SENSEX_CHAIN_ENABLED:
        return None
    return _fetch_index_chain(
        SENSEX_UNDERLYING,
        strike_range if strike_range is not None else SENSEX_STRIKE_RANGE,
        _last_sensex_expiry,
        "_last_sensex_chain",
        "_last_sensex_expiry",
        "_sensex_chain_fail_last_log",
    )


def chains_for_excel(nifty_chain=None):
    """NIFTY + SENSEX legs merged for Websocket.xlsx quotes, volume (E), OI (K–L)."""
    n = nifty_chain if nifty_chain is not None else _last_chain
    s = _last_sensex_chain if SENSEX_CHAIN_ENABLED else None
    if n and s:
        return build_combined_chain(n, s)
    return n or s


def await_915_market_open():
    print(
        f"[*] Core Scanner initialized at {datetime.datetime.now().strftime('%H:%M:%S')}.",
        flush=True,
    )
    while True:
        now = datetime.datetime.now()
        if now.weekday() < 5 and now.time() >= datetime.time(9, 15):
            print(
                "[+] 09:15 AM Market Opening boundary breached. Beginning data routing loops.",
                flush=True,
            )
            break
        if now.weekday() >= 5:
            print("[-] Weekend detected. Scanner shutting down.", flush=True)
            sys.exit(0)
        print(
            f"[{now.strftime('%H:%M:%S')}] Pre-market session. Awaiting 9:15 AM open...",
            flush=True,
        )
        time.sleep(30.0)


if __name__ == "__main__":
    set_shared_state("SCAN")
    await_915_market_open()

    print("[+] Continuous Market Signal Monitoring Active...", flush=True)
    hourly_log.print_startup_info()
    oi_volume_log.print_startup_info()
    print_alert_sound_help()
    if SYNC_EXCEL_LTP:
        sensex_note = (
            f" + {SENSEX_UNDERLYING} chain (BFO, cols K–L OI)"
            if SENSEX_CHAIN_ENABLED
            else ""
        )
        print(
            f"[i] Excel C–J quotes + K–L OI{sensex_note}; "
            "3 CE + 3 PE per index from ATM. Live: py Dhan_websocket.py",
            flush=True,
        )

    while True:
        try:
            hourly_log.tick(scanner_state=get_shared_state())
            maybe_release_stale_mute()
            now_time = datetime.datetime.now().time()
            if now_time > datetime.time(15, 30):
                print(
                    "[─] Market closing hours reached. Scanner shutting down cleanly.",
                    flush=True,
                )
                break

            if get_shared_state() == "MUTE":
                if SENSEX_CHAIN_ENABLED:
                    fetch_sensex_chain()
                sync_excel_ltp(tsl, chains_for_excel())
                combined = chains_for_excel()
                if combined:
                    run_oi_volume_monitor(combined)
                print(
                    f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Scanner Status: MUTE "
                    "(trade engine active. Sleeping...)",
                    flush=True,
                )
                time.sleep(5.0)
                continue

            df_1m = get_nifty_1m_cached()
            if df_1m is None or df_1m.empty or len(df_1m) < MIN_BARS:
                if SENSEX_CHAIN_ENABLED:
                    fetch_sensex_chain()
                sync_excel_ltp(tsl, chains_for_excel())
                print(
                    f"[{datetime.datetime.now().strftime('%H:%M:%S')}] "
                    f"Waiting for NIFTY 1m candles (got {0 if df_1m is None else len(df_1m)} bars)...",
                    flush=True,
                )
                time.sleep(2.0)
                continue

            chain = fetch_chain()
            sensex_chain = fetch_sensex_chain() if SENSEX_CHAIN_ENABLED else None
            if AUTO_STRIKE_WS_ROWS and SYNC_EXCEL_LTP and xw:
                wb_ws = _websocket_workbook()
                if wb_ws is not None:
                    ltp_sheet = wb_ws.sheets["LTP"]
                    if chain:
                        refresh_strike_window_on_websocket(
                            ltp_sheet,
                            chain,
                            refresh_sec=STRIKE_SHEET_REFRESH_SEC,
                        )
                    if sensex_chain:
                        refresh_strike_window_on_websocket(
                            ltp_sheet,
                            sensex_chain,
                            refresh_sec=STRIKE_SHEET_REFRESH_SEC,
                        )
            excel_chain = chains_for_excel(chain)
            sync_rows, _ = sync_excel_ltp(tsl, excel_chain)
            log_rsi_trend_mismatch(df_1m)
            run_oi_volume_monitor(excel_chain)

            if not chain or not isinstance(chain, dict) or "options" not in chain:
                if (
                    _last_chain
                    and (time.time() - _last_chain.get("_cached_at", 0)) < 60
                ):
                    chain = _last_chain
                    st_color = (
                        str(df_1m.iloc[-2]["st_color"]).upper()
                        if "st_color" in df_1m.columns
                        else "RED"
                    )
                    target_type = "CE" if st_color == "GREEN" else "PE"
                    valid_options = [
                        o
                        for o in chain.get("options", [])
                        if isinstance(o, dict) and o.get("option_type") == target_type
                    ]
                    print_heartbeat(df_1m, chain, target_type, valid_options, False)
                time.sleep(2.0)
                continue

            pcr_val = calculate_live_pcr(chain)
            nifty_spot = float(chain.get("spot") or 0)
            day_dates = pd.to_datetime(df_1m["start_Time"]).dt.date
            today = day_dates.max()
            day_df = df_1m[day_dates == today]
            if day_df.empty:
                day_df = df_1m
            today_open = float(day_df.iloc[0]["open"])
            prior = day_dates[day_dates < today]
            if len(prior) > 0:
                prev_df = df_1m[day_dates == prior.max()]
                previous_close = float(prev_df.iloc[-1]["close"])
            else:
                previous_close = today_open
            if "st_color" in df_1m.columns:
                st_color = str(df_1m.iloc[-2]["st_color"]).upper()
            elif "supertrend" in df_1m.columns:
                st_color = (
                    "GREEN"
                    if df_1m.iloc[-2]["close"] >= df_1m.iloc[-2]["supertrend"]
                    else "RED"
                )
            else:
                time.sleep(2.0)
                continue
            target_type = "CE" if st_color == "GREEN" else "PE"
            log_rsi_band_alerts(df_1m, target_type, st_color)

            options_list = chain.get("options", [])
            if not isinstance(options_list, list):
                time.sleep(2.0)
                continue

            valid_options = [
                o
                for o in options_list
                if isinstance(o, dict) and o.get("option_type") == target_type
            ]
            chain_df = pd.DataFrame(options_list) if options_list else None

            # Macro CE/PE volume deltas → oi_volume_alerts CHAIN_MACRO rows
            if chain_df is not None and not chain_df.empty:
                import Chain_Analyzer

                Chain_Analyzer.process_and_analyze_chain(
                    chain_df, nifty_spot, core, underlying=UNDERLYING
                )
            if SENSEX_CHAIN_ENABLED and _last_sensex_chain:
                sx_opts = _last_sensex_chain.get("options") or []
                if sx_opts:
                    import Chain_Analyzer

                    sx_df = pd.DataFrame(sx_opts)
                    sx_spot = float(_last_sensex_chain.get("spot") or 0)
                    if not sx_df.empty and sx_spot > 0:
                        Chain_Analyzer.process_and_analyze_chain(
                            sx_df, sx_spot, core, underlying=SENSEX_UNDERLYING
                        )

            trigger_found = False
            for candidate in valid_options:
                score, _ = core.build_and_score_contract(
                    candidate, target_type, df_1m, pcr_val
                )
                if score >= 70:
                    passed, reason, _ = core.explain_trigger_failure(
                        df_1m,
                        None,
                        target_type,
                        candidate,
                        nifty_spot,
                        previous_close,
                        today_open,
                        pcr_val,
                        chain_df,
                    )
                    if not passed and score >= core.STRONG_BUY_THRESHOLD:
                        print(
                            f"[scan] {candidate.get('symbol')} score={score} "
                            f"reject: {reason}",
                            flush=True,
                        )
                        hourly_log.log(
                            "REJECT",
                            symbol=candidate.get("symbol"),
                            option_type=target_type,
                            score=score,
                            reject_reason=reason,
                            rsi=round(calculate_rsi(df_1m), 1),
                            trend=st_color,
                            pcr=pcr_val,
                            nifty_spot=nifty_spot,
                        )
                if score >= core.STRONG_BUY_THRESHOLD:
                    if core.detect_trigger_1m(
                        df_1m,
                        None,
                        target_type,
                        candidate,
                        nifty_spot,
                        previous_close,
                        today_open,
                        pcr_val,
                        chain_df,
                    ):
                        print(
                            f"\n🔥 SIGNAL VERIFIED! Score: {score} on {candidate['symbol']}. "
                            "Handing off to Main Engine.",
                            flush=True,
                        )
                        hourly_log.log(
                            "SIGNAL_VERIFIED",
                            symbol=candidate.get("symbol"),
                            option_type=target_type,
                            score=score,
                            rsi=round(calculate_rsi(df_1m), 1),
                            trend=st_color,
                            pcr=pcr_val,
                            nifty_spot=nifty_spot,
                        )
                        play_alert_sound("buy")
                        set_shared_state("MUTE")
                        script_dir = os.path.dirname(os.path.abspath(__file__))

                        signal_data = {
                            "symbol": str(candidate["symbol"]),
                            "option_type": str(candidate["option_type"]),
                            "score": int(score),
                        }
                        signal_path = os.path.join(script_dir, "signal.json")
                        try:
                            with open(signal_path, "w") as f:
                                json.dump(signal_data, f)
                            print(
                                f"[+] Signal passed to Main Engine for "
                                f"{candidate['symbol']} (score {score}) via signal.json",
                                flush=True,
                            )
                        except Exception as e:
                            print(f"[-] Error writing signal.json: {e}", flush=True)
                            set_shared_state("SCAN")

                        trigger_found = True
                        break

            print_heartbeat(df_1m, chain, target_type, valid_options, trigger_found)
            time.sleep(3.0)

        except Exception as e:
            import traceback

            print(f"[-] Scanner Runtime Error Alert: {e}", flush=True)
            traceback.print_exc()
            time.sleep(5.0)
