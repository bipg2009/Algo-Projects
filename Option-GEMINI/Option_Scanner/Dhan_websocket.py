import base64
import datetime
import json
import os
import sys
import time
import warnings
from pathlib import Path

import pandas as pd
import xlwings as xw
from dotenv import load_dotenv
from dhanhq import DhanContext, MarketFeed
from pathlib import Path


from scanner_excel import ensure_sheet_quote_headers, quote_row_from_dhan

warnings.filterwarnings("ignore")

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(_SCRIPT_DIR)
_WEBSOCKET_XLSX = os.path.join(_SCRIPT_DIR, "Websocket.xlsx")

CRED_ENV = os.path.join(_SCRIPT_DIR, "cred.env")
load_dotenv(CRED_ENV)
client_id = str(os.getenv("DHAN_CLIENT_CODE", "")).strip()
access_token = os.getenv("DHAN_TOKEN_ID", "").strip()

_INDEX_NSE = {
    "NIFTY", "NIFTY 50", "BANKNIFTY", "NIFTY BANK", "FINNIFTY",
    "NIFTY FIN SERVICE", "MIDCPNIFTY", "NIFTY MID SELECT",
}
_INDEX_BSE = {"SENSEX", "BANKEX"}


def check_access_token(token: str) -> None:
    if not token:
        print("Missing DHAN_TOKEN_ID in cred.env")
        sys.exit(1)
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload))
        exp = datetime.datetime.fromtimestamp(data["exp"])
        now = datetime.datetime.now()
        print(f"Token expires: {exp.strftime('%Y-%m-%d %H:%M:%S')}")
        if now >= exp:
            print("\n*** ACCESS TOKEN EXPIRED — update cred.env (DHAN_TOKEN_ID) ***\n")
            sys.exit(1)
        print(f"Token OK ({int((exp - now).total_seconds() // 60)} min left).\n")
    except Exception as e:
        print(f"Could not read token expiry ({e}). Continuing anyway.")


def get_instrument_file():
    global instrument_df
    current_date = time.strftime("%Y-%m-%d")
    expected_file = "all_instrument " + str(current_date) + ".csv"
    for item in os.listdir("Dependencies"):
        path = os.path.join(item)
        if item.startswith("all_instrument") and current_date not in item.split(" ", 1)[-1]:
            if os.path.isfile(os.path.join("Dependencies", path)):
                os.remove(os.path.join("Dependencies", path))
    if expected_file in os.listdir("Dependencies"):
        print(f"Reading existing file {expected_file}")
        instrument_df = pd.read_csv(os.path.join("Dependencies", expected_file), low_memory=False)
    else:
        print("Downloading instrument file from Dhan")
        instrument_df = pd.read_csv(
            "https://images.dhan.co/api-data/api-scrip-master.csv", low_memory=False
        )
        instrument_df.to_csv(os.path.join("Dependencies", expected_file))
    return instrument_df


def normalize_exchange(symbol: str, exchange: str) -> str:
    sym = symbol.upper().strip()
    if sym in _INDEX_NSE:
        return "NSE_IDX"
    if sym in _INDEX_BSE:
        return "BSE_IDX"
    return exchange


def dedupe_watchlist(watchlist):
    seen = set()
    out = []
    for s in watchlist:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


check_access_token(access_token)
print("Opening Websocket.xlsx (live feed writes column C)...")
if not os.path.isfile(_WEBSOCKET_XLSX):
    print(f"Missing {_WEBSOCKET_XLSX}")
    sys.exit(1)
wb = xw.Book(_WEBSOCKET_XLSX)
sheet = wb.sheets["LTP"]
ensure_sheet_quote_headers(sheet)
instrument_df = get_instrument_file()


def create_instruments(watchlist, stock_exchange):
    rows = {}
    row_symbols = {}
    row = 1
    instruments = []
    instrument_exchange = {
        "NSE": "NSE", "BSE": "BSE", "NFO": "NSE", "BFO": "BSE", "MCX": "MCX",
        "CUR": "NSE", "BSE_IDX": "BSE", "NSE_IDX": "NSE",
    }
    exchange_id = {
        "NSE": MarketFeed.NSE, "BSE": MarketFeed.BSE, "MCX": MarketFeed.MCX,
        "NFO": MarketFeed.NSE_FNO, "BFO": MarketFeed.BSE_FNO, "IDX": MarketFeed.IDX,
        "BSE_IDX": MarketFeed.IDX, "NSE_IDX": MarketFeed.IDX,
    }
    for tradingsymbol in watchlist:
        tradingsymbol = str(tradingsymbol).strip()
        if not tradingsymbol or tradingsymbol.lower() == "nan":
            continue
        try:
            row += 1
            exchange_ = normalize_exchange(tradingsymbol, stock_exchange[tradingsymbol])
            exchange = instrument_exchange[exchange_]
            matched = instrument_df[
                (
                    (instrument_df["SEM_TRADING_SYMBOL"] == tradingsymbol)
                    | (instrument_df["SEM_CUSTOM_SYMBOL"] == tradingsymbol)
                )
                & (instrument_df["SEM_EXM_EXCH_ID"] == instrument_exchange[exchange])
            ]
            if exchange_ in ("NSE", "BSE") and "SEM_SERIES" in matched.columns:
                eq_rows = matched[matched["SEM_SERIES"] == "EQ"]
                if not eq_rows.empty:
                    matched = eq_rows
            security_id = matched.iloc[-1]["SEM_SMST_SECURITY_ID"]
            exchange_segment = exchange_id[exchange_]
            # Quote mode = LTP + ATP + Volume + O/H/L/C (Ticker = LTP only)
            feed_mode = MarketFeed.Quote
            instruments.append((exchange_segment, str(security_id), feed_mode))
            rows[int(security_id)] = row
            row_symbols[row] = tradingsymbol
            print(f"  row {row}: {tradingsymbol} ({exchange_}) -> id {int(security_id)}")
        except Exception as e:
            print(f"Error: {e} for {tradingsymbol}")
    return instruments, rows, row_symbols


def print_watchlist_snapshot(row_symbols):
    """Print every sheet row top → bottom from column C (not NIFTY tick spam)."""
    try:
        last_row = sheet.range("A1").end("down").row
        df = sheet.range(f"A1:J{last_row}").options(pd.DataFrame, header=1, index=False).value
        if df is None or df.empty:
            return
        name_col = "Script Name" if "Script Name" in df.columns else df.columns[0]
        exch_col = "Exchange" if "Exchange" in df.columns else (
            df.columns[1] if len(df.columns) > 1 else None
        )
        ltp_col = "LTP" if "LTP" in df.columns else (
            df.columns[2] if len(df.columns) > 2 else None
        )
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        n = len(df)
        print(f"\n[{ts}] ── WebSocket sheet scan ({n} rows) ──", flush=True)
        for i in range(n):
            sym = str(df[name_col].iloc[i]).strip()
            if not sym or sym.lower() == "nan":
                continue
            exch = str(df[exch_col].iloc[i] or "NSE").strip() if exch_col else "NSE"
            ltp = df[ltp_col].iloc[i] if ltp_col else None
            ltp_s = f"{float(ltp):.2f}" if ltp not in (None, "", "None") else "—"
            print(f"  {i + 1:2}. {sym:<28} {exch:<8} {ltp_s}", flush=True)
        print(flush=True)
    except Exception as e:
        print(f"Sheet scan error: {e}", flush=True)


def read_watchlist_from_sheet():
    last_row_col1 = sheet.range("A1").end("down").row
    last_row_col2 = sheet.range("B1").end("down").row
    row = max(last_row_col1, last_row_col2)
    data_frame = sheet.range("A1").expand().options(pd.DataFrame, header=1, index=False).value
    name_col = "Script Name" if "Script Name" in data_frame.columns else data_frame.columns[0]
    raw_exchange = sheet.range(f"A2:B{row}").options(dict).value
    stock_exchange = {str(k).strip(): v for k, v in raw_exchange.items()}
    watchlist = dedupe_watchlist([
        str(x).strip()
        for x in data_frame[name_col].tolist()
        if pd.notna(x) and str(x).strip() and str(x).strip().lower() != "nan"
    ])
    return watchlist, stock_exchange


def create_market_feed(cid, token, instruments):
    return MarketFeed(DhanContext(cid, token), instruments)


def run_feed(cid, token, instruments, rows, row_symbols, initial_watchlist):
    previous_watchlist = list(initial_watchlist)
    rows_map = dict(rows)
    data = None
    last_sheet_check = 0.0
    last_full_scan = 0.0
    last_tick_print = {}

    while True:
        try:
            if data is None:
                if not instruments:
                    print("No instruments — check column A (Script Name) and B (Exchange).")
                    time.sleep(5)
                    watchlist, stock_exchange = read_watchlist_from_sheet()
                    instruments, rows_map, row_symbols = create_instruments(
                        watchlist, stock_exchange
                    )
                    previous_watchlist = list(watchlist)
                    continue
                data = create_market_feed(cid, token, instruments)
                data.loop.run_until_complete(data.connect())
                print(f"Connected ({len(instruments)} symbols). Ctrl+C to stop.")

            if time.time() - last_sheet_check >= 5:
                watchlist, stock_exchange = read_watchlist_from_sheet()
                last_sheet_check = time.time()
                if watchlist != previous_watchlist:
                    print("Watchlist changed — reconnecting...")
                    instruments, rows_map, row_symbols = create_instruments(
                        watchlist, stock_exchange
                    )
                    previous_watchlist = list(watchlist)
                    try:
                        data.close_connection()
                    except Exception:
                        pass
                    data = create_market_feed(cid, token, instruments)
                    data.loop.run_until_complete(data.connect())

            if time.time() - last_full_scan >= 12.0:
                print_watchlist_snapshot(row_symbols)
                last_full_scan = time.time()

            response = data.get_data()
            if not response:
                time.sleep(0.02)
                continue
            if "LTP" in response or "avg_price" in response or "volume" in response:
                security_id = int(response["security_id"])
                excel_row = rows_map.get(security_id)
                if excel_row:
                    sym = str(row_symbols.get(excel_row, "")).upper()
                    try:
                        row_vals = quote_row_from_dhan(response)
                        sheet.range(f"C{excel_row}:J{excel_row}").value = [row_vals]
                        throttle = 30.0 if sym in _INDEX_NSE or sym in _INDEX_BSE else 3.0
                        now = time.time()
                        if now - last_tick_print.get(excel_row, 0) >= throttle:
                            last_tick_print[excel_row] = now
                            print(
                                f"{datetime.datetime.now().time()}: "
                                f"{row_symbols.get(excel_row, excel_row)} "
                                f"LTP={response['LTP']}",
                                flush=True,
                            )
                    except Exception as write_err:
                        print(f"Excel write row {excel_row}: {write_err}")
        except KeyboardInterrupt:
            print("\nStopped.")
            if data:
                try:
                    data.close_connection()
                except Exception:
                    pass
            break
        except Exception as e:
            print(f"WebSocket error: {e}")
            if data:
                try:
                    data.close_connection()
                except Exception:
                    pass
                data = None
            time.sleep(5)


def main_loop():
    print("Reading watchlist from Websocket.xlsx ...")
    watchlist, stock_exchange = read_watchlist_from_sheet()
    print(f"Found {len(watchlist)} symbols.")
    instruments, rows, row_symbols = create_instruments(watchlist, stock_exchange)
    print_watchlist_snapshot(row_symbols)
    run_feed(client_id, access_token, instruments, rows, row_symbols, watchlist)


if __name__ == "__main__":
    main_loop()
