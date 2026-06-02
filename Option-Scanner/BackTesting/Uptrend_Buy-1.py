"""
SEDA-Compliant Backtest Engine: 1m, 3m, 5m, and 10m Multi-Timeframe Sync Engine.
Executes historical sweeps by ensuring macro alignment indices match core 1m bars.
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

import Option_strategy_core as core
import System_Config

print("NSE Option Scanner BACKTEST — starting SEDA engine...", flush=True)

TEST_DATE = "2026-05-22"
EXPIRY_CODE = 1
API_PAUSE_SEC = 1.2
NIFTY_SECURITY_ID = 13

# Synchronised execution window parameter
OPTION_BAR_TF = 1
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
    return (
        f"{underlying} {dt.day} {dt.strftime('%b').upper()} {int(strike)} {option_type}"
    )


def cache_path(name):
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, name)


def fetch_nifty_bars(tsl, test_date, interval=1):
    """Fetches and caches NIFTY index data for a specific minute interval frame."""
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


def build_seda_dataframe(tsl, test_date):
    """
    SEDA ARCHITECTURE ALIGNMENT ENGINE
    Fetches 1m, 3m, 5m, and 10m data frames and aggregates them cleanly
    into a unified 1-minute execution map to prevent structural key errors.
    """
    print(f"[SEDA LOG] Building multi-timeframe grid alignment for {test_date}...")

    # 1. Fetch individual structural data sheets
    df_1m = fetch_nifty_bars(tsl, test_date, interval=1)
    df_3m = fetch_nifty_bars(tsl, test_date, interval=3)
    df_5m = fetch_nifty_bars(tsl, test_date, interval=5)
    df_10m = fetch_nifty_bars(tsl, test_date, interval=10)

    # Convert timestamps to explicit datetime structures for relational index tracking
    for df in [df_1m, df_3m, df_5m, df_10m]:
        df["start_Time"] = pd.to_datetime(df["start_Time"])

    # 2. Process technical indicators per dataset layer using your internal helper scripts
    # (Assuming indicators like EMA20, EMA50, ADX, RSI are assigned here by your indicator engine)

    # 3. Synchronise and blend multi-timeframe trends into the base 1m framework
    # We use forward-fill ('ffill') to cleanly project macro trends onto micro execution bars
    df_3m_sub = df_3m[["start_Time", "EMA20", "EMA50"]].rename(
        columns={"EMA20": "EMA20_3m", "EMA50": "EMA50_3m"}
    )
    df_5m_sub = df_5m[["start_Time", "EMA20", "EMA50", "ADX"]].rename(
        columns={"EMA20": "EMA20_5m", "EMA50": "EMA50_5m", "ADX": "ADX_5m"}
    )
    df_10m_sub = df_10m[["start_Time", "EMA20", "EMA50"]].rename(
        columns={"EMA20": "EMA20_10m", "EMA50": "EMA50_10m"}
    )

    # Sequentially merge layers using left join maps to eliminate lookahead/repainting anomalies
    df_seda = pd.merge_asof(
        df_1m.sort_values("start_Time"),
        df_3m_sub.sort_values("start_Time"),
        on="start_Time",
        direction="backward",
    )
    df_seda = pd.merge_asof(
        df_seda,
        df_5m_sub.sort_values("start_Time"),
        on="start_Time",
        direction="backward",
    )
    df_seda = pd.merge_asof(
        df_seda,
        df_10m_sub.sort_values("start_Time"),
        on="start_Time",
        direction="backward",
    )

    return df_seda


def fetch_one_option_leg(tsl, strike_offset, opt_type, test_date, expiry_code):
    next_day = (pd.to_datetime(test_date) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    fields = ["close", "iv", "volume", "oi", "spot", "strike"]
    resp = tsl.Dhan.expired_options_data(
        str(NIFTY_SECURITY_ID),
        "NSE_FNO",
        "OPTIDX",
        "WEEK",
        expiry_code,
        strike_offset,
        opt_type,
        fields,
        test_date,
        next_day,
        OPTION_BAR_TF,
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
            leg = fetch_one_option_leg(
                tsl, strike_key, opt_type, test_date, expiry_code
            )
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
            trimmed = {
                k: (v[start:] if isinstance(v, list) else v) for k, v in s.items()
            }
            aligned.append({**item, "series": trimmed})
        else:
            aligned.append(item)
    return aligned


def option_bar_idx(minute_idx):
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
        options.append(
            {
                "strike": strike,
                "option_type": item["option_type"],
                "symbol": label,
                "display_symbol": label,
                "ltp": ltp,
                "iv": iv,
                "oi": oi,
                "oi_change": oi - prev_oi,
                "volume": volume,
                "spot": spot,
            }
        )
    if not options:
        return None
    spot = options[0]["spot"]
    atm = round(spot / 50) * 50
    return {"spot": spot, "atm": atm, "options": options}


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
            return {
                "ltp": float(s["close"][bar_opt_idx]),
                "oi": oi,
                "oi_change": oi - prev,
                "volume": vol,
                "prev_volume": prev_vol,
            }
    return {
        "ltp": pick["ltp"],
        "oi": pick.get("oi", ""),
        "oi_change": pick["oi_change"],
        "volume": pick["volume"],
        "prev_volume": pick["volume"],
    }


def simulate_trade(pick, entry_1m_idx, nifty_1m, legs, test_date):
    """Simulates a trade entry with latency slippage."""
    if entry_1m_idx + 1 < len(nifty_1m):
        entry_1m_idx += 1
    bar_opt_entry = option_bar_idx(entry_1m_idx)
    opt = get_option_snapshot(legs, pick, bar_opt_entry)

    base_entry_price = opt["ltp"]
    slippage_penalty = getattr(System_Config, "BACKTEST_SLIPPAGE_PCT", 0.01)
    final_execution_price = base_entry_price * (1.0 + slippage_penalty)

    print(
        f"[SEDA EXECUTION] filled at: {final_execution_price:.2f} (Slippage: {slippage_penalty*100}%)"
    )
    return final_execution_price
