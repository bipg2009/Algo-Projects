import time
import datetime
import os
import pandas as pd
from System_Config import SYNC_EXCEL_LTP

try:
    import xlwings as xw
except ImportError:
    xw = None

from scanner_excel import (
    ensure_sheet_quote_headers,
    build_chain_maps,
    quote_row_from_chain_option,
    merge_quote_rows,
    is_fno_symbol
)

_EXCEL_STATUS_INTERVAL = 30.0
_WATCHLIST_PRINT_INTERVAL = 15.0
_excel_sync_last_status = 0.0
_watchlist_last_print = 0.0
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_WEBSOCKET_XLSX = os.path.join(_SCRIPT_DIR, "Websocket.xlsx")

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
        print(f"[!] Excel LTP sync: 0/{total} rows updated (open Websocket.xlsx in Excel or check symbols/REST).", flush=True)
    elif updated < total:
        print(f"[i] Excel LTP sync: {updated}/{total} rows ({total - updated} still unmatched).", flush=True)

def _websocket_workbook():
    if not xw: return None
    for opener in (lambda: xw.books["Websocket.xlsx"], lambda: xw.Book("Websocket.xlsx"), lambda: xw.Book(_WEBSOCKET_XLSX)):
        try:
            wb = opener()
            if wb is not None:
                return wb
        except Exception:
            pass
    return None

def _sheet_last_data_row(sheet, max_scan=500):
    try:
        vals = sheet.range(f"A1:A{max_scan}").value
    except Exception:
        return 1
    if not isinstance(vals, list):
        vals = [vals]
    last = 1
    for i, v in enumerate(vals, start=1):
        if v is None: continue
        sym = str(v).strip()
        if not sym or sym.lower() == "nan": continue
        if i == 1 and sym.lower() in ("script name", "symbol", "script"): continue
        last = i
    return last

def _normalize_sheet_exchange(sym, exch):
    exch = str(exch or "NSE").strip().upper()
    alias = {"NSE_FNO": "NFO", "NSE FNO": "NFO", "NSE_EQ": "NSE", "EQ": "NSE", "BSE_FNO": "BFO", "IDX_I": "NSE_IDX"}
    exch = alias.get(exch, exch)
    if is_fno_symbol(sym) and exch in ("NSE", "NSE_EQ", ""):
        exch = "NFO"
    return exch

def print_watchlist_scan(watchlist_rows, ltps_by_row):
    global _watchlist_last_print
    if not watchlist_rows: return
    now = time.time()
    if now - _watchlist_last_print < _WATCHLIST_PRINT_INTERVAL: return
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
    from market_data_engine import chains_for_excel # moved import here to avoid circular dep
    watchlist_rows = []
    ltps_by_row = {}
    if not SYNC_EXCEL_LTP or not xw:
        return watchlist_rows, ltps_by_row
    wb = _websocket_workbook()
    if wb is None:
        _log_excel_sync(0, 0, "Websocket.xlsx not open — start Excel with file in Option Scanner folder")
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
        exch_col = "Exchange" if "Exchange" in df.columns else (df.columns[1] if len(df.columns) > 1 else None)
        chain_for_ltp = chains_for_excel(chain if isinstance(chain, dict) else None)
        quote_map, oi_map = build_chain_maps(chain_for_ltp)
        for i in range(len(df)):
            sym = str(df[name_col].iloc[i]).strip()
            if not sym or sym.lower() == "nan": continue
            exch = "NSE"
            if exch_col is not None: exch = str(df[exch_col].iloc[i] or "NSE").strip()
            watchlist_rows.append((sym, _normalize_sheet_exchange(sym, exch)))
        rest_quotes = tsl.get_rest_quotes_for_watchlist(watchlist_rows, quiet=True) if watchlist_rows else {}
        col_values, oi_values, updated, row_num = [], [], 0, 0
        for i in range(len(df)):
            sym = str(df[name_col].iloc[i]).strip()
            if not sym or sym.lower() == "nan":
                col_values.append([None] * 8); oi_values.append([None, None]); continue
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
                except (TypeError, ValueError): pass
            col_values.append(row); oi_values.append(oi_row if oi_row else [None, None])
        end_row = len(col_values) + 1
        if col_values:
            sheet.range(f"C2:J{end_row}").value = col_values
            sheet.range(f"K2:L{end_row}").value = oi_values
        _log_excel_sync(updated, len(watchlist_rows))
        print_watchlist_scan(watchlist_rows, ltps_by_row)
    except Exception as exc:
        _log_excel_sync(0, 0, str(exc))
    return watchlist_rows, ltps_by_row

def get_workbook():
    return _websocket_workbook()
