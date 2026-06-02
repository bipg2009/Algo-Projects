import time
import os
import pandas as pd
from System_Config import (
    INTRADAY_CACHE_SEC,
    UNDERLYING,
    STRIKE_RANGE,
    SENSEX_CHAIN_ENABLED,
    SENSEX_UNDERLYING,
    SENSEX_STRIKE_RANGE
)
from scanner_excel import build_combined_chain, filter_chain_strike_window

_last_chain = None
_last_expiry = None
_last_sensex_chain = None
_last_sensex_expiry = None
_chain_fail_last_log = 0.0
_sensex_chain_fail_last_log = 0.0
_intraday_cache = {"t": 0.0, "df": None}

def calculate_live_pcr(chain: dict) -> float:
    if not chain or not isinstance(chain, dict) or "options" not in chain:
        return 1.0
    options = chain["options"]
    if not isinstance(options, list):
        return 1.0
    total_call_oi = sum(int(o.get("oi", 0)) for o in options if isinstance(o, dict) and o.get("option_type") == "CE")
    total_put_oi = sum(int(o.get("oi", 0)) for o in options if isinstance(o, dict) and o.get("option_type") == "PE")
    return round(total_put_oi / total_call_oi, 3) if total_call_oi > 0 else 1.0

def get_nifty_1m_cached(tsl) -> pd.DataFrame:
    global _intraday_cache
    now = time.time()
    if _intraday_cache["df"] is not None and (now - _intraday_cache["t"]) < INTRADAY_CACHE_SEC:
        return _intraday_cache["df"]
    df = tsl.get_intraday_data(UNDERLYING, "NSE", 1)
    if df is None:
        print("[DEBUG] get_intraday_data returned None", flush=True)
    elif df.empty:
        print("[DEBUG] get_intraday_data returned empty df", flush=True)
    else:
        print(f"[DEBUG] get_intraday_data returned {len(df)} rows. cols: {df.columns.tolist()}", flush=True)

    if df is not None and not df.empty:
        df = tsl.add_supertrend(df, period=10, multiplier=3)
        _intraday_cache = {"t": now, "df": df}
    return df

def _fetch_index_chain(tsl, underlying: str, strike_range: int, expiry_ref: str, cache_attr: str, expiry_attr: str, fail_log_attr: str):
    chain = tsl.get_option_chain(underlying=underlying, strike_range=strike_range, expiry=expiry_ref)
    if chain and isinstance(chain, dict) and chain.get("options"):
        chain = filter_chain_strike_window(dict(chain))
        chain["_cached_at"] = time.time()
        globals()[cache_attr] = chain
        globals()[expiry_attr] = chain.get("expiry")
        return chain
    
    now = time.time()
    fail_last = globals().get(fail_log_attr, 0.0)
    if now - fail_last > 30:
        print(f"[!] {underlying} option chain fetch failed — retrying (using last cache if recent).", flush=True)
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

def fetch_chain(tsl, strike_range=None):
    return _fetch_index_chain(tsl, UNDERLYING, strike_range if strike_range is not None else STRIKE_RANGE, _last_expiry, "_last_chain", "_last_expiry", "_chain_fail_last_log")

def fetch_sensex_chain(tsl, strike_range=None):
    if not SENSEX_CHAIN_ENABLED:
        return None
    return _fetch_index_chain(tsl, SENSEX_UNDERLYING, strike_range if strike_range is not None else SENSEX_STRIKE_RANGE, _last_sensex_expiry, "_last_sensex_chain", "_last_sensex_expiry", "_sensex_chain_fail_last_log")

def chains_for_excel(nifty_chain=None):
    n = nifty_chain if nifty_chain is not None else _last_chain
    s = _last_sensex_chain if SENSEX_CHAIN_ENABLED else None
    if n and s:
        return build_combined_chain(n, s)
    return n or s
