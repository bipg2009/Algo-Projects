"""
Live position monitor — SL, target, supertrend, EMA, time exit, trailing SL.

Run directly:
  py Monitor_Engine.py "NIFTY 26 MAY 24000 CALL"
  py Monitor_Engine.py "NIFTY 26 MAY 24000 CALL" CE 150.0 1234567 250.0 135.0
"""

import datetime
import json
import os
import re
import sys
import time
from pathlib import Path

import Indicators

# =========================================================
# CONFIGURATION
# =========================================================

SCANNER_ROOT = Path(__file__).resolve().parent
CRED_ENV = SCANNER_ROOT / "cred.env"
STATE_FILE = SCANNER_ROOT / "scanner_state.json"
UNDERLYING = "NIFTY"
TARGET_POINTS = 100.0
INITIAL_SL_POINTS = 15.0
POLL_SECONDS = 10.0

# User display format — do not change wording or punctuation
TICK_LINE_FORMAT = "LTP <{ltp}> OI >{oi}> & <VOL> <{vol}>"

TRAIL_PERCENT = 0.05
MARKET_EXIT_TIME = datetime.time(15, 15)


# =========================================================
# TRAILING SL
# =========================================================

def calculate_trailing_sl(current_ltp):
    return round(current_ltp * (1 - TRAIL_PERCENT), 2)


# =========================================================
# POSITION MONITOR (rules)
# =========================================================

def monitor_position(position, snapshot):
    side = position["option_type"]
    ltp = snapshot["ltp"]
    entry_ltp = position["entry_ltp"]
    current_sl = position["sl"]

    if ltp >= position["target"]:
        return "EXIT", "TARGET_HIT", current_sl

    if ltp <= current_sl:
        return "EXIT", "STOP_LOSS", current_sl

    st_color = snapshot.get("supertrend_1m")

    if side == "CE" and st_color == "RED":
        return "EXIT", "SUPERTREND_REVERSAL", current_sl

    if side == "PE" and st_color == "GREEN":
        return "EXIT", "SUPERTREND_REVERSAL", current_sl

    ema9 = snapshot.get("ema9")
    ema20 = snapshot.get("ema20")

    if ema9 is not None and ema20 is not None:
        if side == "CE" and ema9 < ema20:
            return "EXIT", "EMA_REVERSAL", current_sl
        if side == "PE" and ema9 > ema20:
            return "EXIT", "EMA_REVERSAL", current_sl

    if datetime.datetime.now().time() >= MARKET_EXIT_TIME:
        return "EXIT", "TIME_DECAY", current_sl

    if ltp > entry_ltp:
        trailing_sl = calculate_trailing_sl(ltp)
        if trailing_sl > current_sl:
            return "TRAIL", "PROFIT_LOCK", trailing_sl

    return "HOLD", "Momentum intact", current_sl


def build_snapshot(df_1m, current_ltp):
    """Market snapshot for monitor_position from NIFTY 1m bars + option LTP."""
    snapshot = {"ltp": float(current_ltp)}
    if df_1m is None or df_1m.empty:
        return snapshot

    work = df_1m
    if "EMA9" not in work.columns:
        work = Indicators.add_ema(work.copy())

    row = work.iloc[-2] if len(work) >= 2 else work.iloc[-1]

    if "st_color" in work.columns:
        snapshot["supertrend_1m"] = str(row.get("st_color", "")).upper()
    elif "supertrend" in work.columns:
        snapshot["supertrend_1m"] = (
            "GREEN" if float(row["close"]) >= float(row["supertrend"]) else "RED"
        )

    if "EMA9" in work.columns:
        snapshot["ema9"] = float(row["EMA9"])
        snapshot["ema20"] = float(row["EMA20"])

    return snapshot


def execute_hypercare_monitoring(position, df_1m, opt_row, current_ltp):
    """One evaluation tick — used by live loop and backtests."""
    snapshot = build_snapshot(df_1m, current_ltp)
    return monitor_position(position, snapshot)


# =========================================================
# LIVE RUNNER (py Monitor_Engine.py)
# =========================================================

def _load_cred_env():
    if not CRED_ENV.is_file():
        return
    try:
        from dotenv import load_dotenv

        load_dotenv(CRED_ENV)
    except ImportError:
        for line in CRED_ENV.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def release_scanner_lock():
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({"status": "SCAN", "updated_at": time.time()}, f)
        print("[+] Scanner released to SCAN.", flush=True)
    except Exception as e:
        print(f"[-] Failed to release scanner lock: {e}", flush=True)


def _print_usage():
    print(
        "[-] Monitor_Engine needs a trade to monitor.\n"
        "\n"
        "  Use quotes around the full option name:\n"
        '    py Monitor_Engine.py "NIFTY 26 MAY 24000 CALL"\n'
        "\n"
        "  Or without quotes (all words after the script name):\n"
        "    py Monitor_Engine.py NIFTY 26 MAY 24000 CALL\n"
        "\n"
        "  Full:\n"
        '    py Monitor_Engine.py "NIFTY 26 MAY 24000 CALL" CE 150.0 1234567 250.0 135.0\n'
        "\n"
        "  Do not paste 'py Price_Check.py' into the command — only the symbol.\n"
        "  Websocket.xlsx is optional; LTP falls back to Dhan REST if Excel is closed.\n",
        flush=True,
    )


_MONTHS = (
    "JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC"
)
# NIFTY 26 MAY 24000 PUT / CALL (pulls contract out of pasted command lines)
_CONTRACT_RE = re.compile(
    rf"\b((?:NIFTY|BANKNIFTY|FINNIFTY|MIDCPNIFTY)\s+"
    rf"(?:\d{{1,2}}\s+)?(?:{_MONTHS})\s+\d{{4,6}}\s+(?:CALL|PUT))\b",
    re.IGNORECASE,
)


def _resolve_contract_symbol():
    """Best-effort contract name from argv, env, or pasted 'py … NIFTY … PUT' text."""
    env_sym = os.environ.get("MONITOR_SYMBOL", "").strip()
    if env_sym:
        return env_sym

    raw = " ".join(sys.argv[1:]).strip()
    match = _CONTRACT_RE.search(raw)
    if match:
        return match.group(1).strip()

    tokens = _clean_argv_tokens()
    if not tokens:
        return None
    if tokens[-1].upper() in ("CE", "PE"):
        return " ".join(tokens[:-1])
    return " ".join(tokens)


def _clean_argv_tokens():
    """
    Normalize argv: split glued strings like 'py Price_Check.py NIFTY 26 MAY 24000 PUT'
    and drop py / *.py tokens.
    """
    parts = []
    for arg in sys.argv[1:]:
        parts.extend(str(arg).strip().split())

    tokens = []
    for word in parts:
        low = word.lower().strip(",")
        if low in ("py", "python", "python3", "-m"):
            continue
        if low.endswith(".py"):
            continue
        tokens.append(word)

    # If junk remains before the contract, start at NIFTY / BANKNIFTY / …
    underlyings = ("NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "SENSEX", "BANKEX")
    for i, word in enumerate(tokens):
        if word.upper() in underlyings:
            return tokens[i:]
    return tokens


def _normalize_symbol(symbol):
    return " ".join(str(symbol or "").upper().split())


def _lookup_instrument_symbol(tsl, symbol):
    """Resolve to SEM_CUSTOM_SYMBOL from master file."""
    want = _normalize_symbol(symbol)
    try:
        df = tsl.instrument_df
        for col in ("SEM_CUSTOM_SYMBOL", "SEM_TRADING_SYMBOL"):
            if col not in df.columns:
                continue
            for val in df[col].astype(str):
                if _normalize_symbol(val) == want:
                    row = df[df[col].astype(str) == val]
                    if not row.empty:
                        return str(row.iloc[-1]["SEM_CUSTOM_SYMBOL"]).strip()
    except Exception:
        pass
    return symbol.strip()


def _find_option_row(chain, symbol):
    if not chain or not chain.get("options"):
        return None
    want = _normalize_symbol(symbol)
    for opt in chain["options"]:
        osym = str(opt.get("symbol", "")).strip()
        if _normalize_symbol(osym) == want:
            return opt
    for opt in chain["options"]:
        osym = str(opt.get("symbol", "")).strip()
        if want in _normalize_symbol(osym) or _normalize_symbol(osym) in want:
            return opt
    return None


def _infer_option_type(symbol):
    s = symbol.upper()
    if " PUT" in s or s.endswith("PUT"):
        return "PE"
    return "CE"


def print_price_tick(ltp, oi, vol):
    """Console line: LTP <…> OI >…> & <VOL> … (fixed format)."""
    print(
        TICK_LINE_FORMAT.format(
            ltp=ltp,
            oi=oi,
            vol=vol,
        ),
        flush=True,
    )


def _infer_underlying(symbol):
    s = symbol.upper()
    for u in ("BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "NIFTY"):
        if u in s:
            return u
    return UNDERLYING


def fetch_ltp_oi_vol(tsl, symbol):
    """LTP / OI / volume — option chain first (works without Websocket.xlsx)."""
    ltp = 0.0
    oi = 0
    vol = 0
    canonical = _lookup_instrument_symbol(tsl, symbol)
    try:
        chain = tsl.get_option_chain(
            underlying=_infer_underlying(canonical), strike_range=20
        )
        row = _find_option_row(chain, canonical)
        if row:
            canonical = str(row.get("symbol", canonical)).strip()
            oi = int(row.get("oi") or 0)
            vol = int(row.get("volume") or 0)
            ltp = float(row.get("ltp") or 0.0)
    except Exception:
        pass
    if ltp <= 0:
        ltp = float(tsl.get_ltp(canonical) or 0.0)
    return ltp, oi, vol, canonical


def calculate_oi_metric(entry_oi, current_oi):
    if entry_oi == 0:
        return "0% (Entry OI baseline missing)"
    pct_change = ((current_oi - entry_oi) / entry_oi) * 100
    if pct_change > 0:
        return f"Increased from Order Execution by {round(pct_change, 2)}%"
    if pct_change == 0:
        return "Same since Order Execution (0%)"
    if pct_change <= -5.0:
        return (
            f"Decreased by {round(abs(pct_change), 2)}% | "
            f"Entry OI: {entry_oi} -> Current OI: {current_oi}"
        )
    return f"Decreased by {round(abs(pct_change), 2)}%"


def parse_cli_arguments(tsl):
    raw_cmd = " ".join(sys.argv[1:])
    symbol = _resolve_contract_symbol()
    tokens = _clean_argv_tokens()

    if not symbol:
        _print_usage()
        sys.exit(1)

    if len(tokens) >= 6 and tokens[-5].upper() in ("CE", "PE"):
        try:
            option_type = tokens[-5].upper()
            ltp = float(tokens[-4])
            entry_oi = int(tokens[-3])
            target = float(tokens[-2])
            sl = float(tokens[-1])
            return {
                "symbol": symbol,
                "option_type": option_type,
                "entry_ltp": ltp,
                "entry_oi": entry_oi,
                "target": target,
                "sl": sl,
                "initial_sl": sl,
                "peak_price": ltp,
                "watch_only": False,
            }
        except (IndexError, ValueError):
            pass

    option_type = _infer_option_type(symbol)
    if tokens and tokens[-1].upper() in ("CE", "PE"):
        option_type = tokens[-1].upper()

    ltp, entry_oi, vol, symbol = fetch_ltp_oi_vol(tsl, symbol)
    if ltp <= 0:
        print(f"[-] Could not get LTP for {symbol}", flush=True)
        if raw_cmd and raw_cmd != symbol:
            print(f"[i] Ignored pasted command junk; using contract: {symbol}", flush=True)
        print(
            '[i] Run: py Monitor_Engine.py "NIFTY 26 MAY 24000 PUT"',
            flush=True,
        )
        print(f"[i] Or set env: set MONITOR_SYMBOL={symbol}", flush=True)
        sys.exit(1)

    target = round(ltp + TARGET_POINTS, 2)
    sl = round(ltp - INITIAL_SL_POINTS, 2)
    print(f"[+] Monitoring: {symbol}", flush=True)
    print_price_tick(ltp, entry_oi, vol)

    return {
        "symbol": symbol,
        "option_type": option_type,
        "entry_ltp": ltp,
        "entry_oi": entry_oi,
        "target": target,
        "sl": sl,
        "initial_sl": sl,
        "peak_price": ltp,
        "watch_only": True,
    }


def run_live_monitor():
    os.chdir(SCANNER_ROOT)
    if str(SCANNER_ROOT) not in sys.path:
        sys.path.insert(0, str(SCANNER_ROOT))

    _load_cred_env()
    client_code = os.getenv("DHAN_CLIENT_CODE")
    token_id = os.getenv("DHAN_TOKEN_ID")
    if not client_code or not token_id:
        print(f"[-] Missing DHAN_CLIENT_CODE or DHAN_TOKEN_ID in {CRED_ENV}", flush=True)
        sys.exit(1)

    from Dhan_Tradehull import Tradehull

    tsl = Tradehull(client_code, token_id)
    position = parse_cli_arguments(tsl)

    watch_only = position.get("watch_only", True)
    if watch_only:
        print(
            f"[+] {position['symbol']} — every {int(POLL_SECONDS)}s (Ctrl+C to stop)",
            flush=True,
        )
    else:
        print(
            f"[+] {position['symbol']} — trade monitor, auto-exit on SL/target/rules",
            flush=True,
        )

    try:
        while True:
            try:
                current_ltp, current_oi, current_vol, _ = fetch_ltp_oi_vol(
                    tsl, position["symbol"]
                )
                if current_ltp <= 0:
                    current_ltp = float(position["entry_ltp"])

                print_price_tick(current_ltp, current_oi, current_vol)

                if watch_only:
                    time.sleep(POLL_SECONDS)
                    continue

                df_1m = tsl.get_intraday_data(UNDERLYING, "NSE", 1)
                if df_1m is not None and not df_1m.empty and len(df_1m) >= 15:
                    df_1m = tsl.add_supertrend(df_1m, period=10, multiplier=3)

                action, reason, updated_sl = execute_hypercare_monitoring(
                    position, df_1m, None, current_ltp
                )

                if action == "TRAIL":
                    position["sl"] = updated_sl

                if action == "EXIT":
                    print(f"[-] EXIT: {reason}", flush=True)
                    time.sleep(2.0)
                    release_scanner_lock()
                    break

            except Exception as e:
                print(f"[-] Monitor loop error: {e}", flush=True)

            time.sleep(POLL_SECONDS)
    except KeyboardInterrupt:
        print("\n[+] Stopped by user.", flush=True)


if __name__ == "__main__":
    run_live_monitor()
