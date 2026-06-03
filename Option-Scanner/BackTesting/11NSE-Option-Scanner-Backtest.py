"""
SEDA-Compliant Core Backtest Engine
Coordinates multi-timeframe candle data, executes the 165-point strategy scoring engine,
and runs the multi-stage trailing exit rules row-by-row.
"""

import importlib.util
import json
import os
import sys
import time
import traceback
import pandas as pd
import numpy as np

# Set IS_BACKTEST environment variable to avoid live API queries during backtesting
os.environ["IS_BACKTEST"] = "1"

import Option_strategy_core as core
import System_Config
import indicator_engine as Indicators

print("NSE Option Scanner BACKTEST — starting SEDA engine...", flush=True)

TEST_DATE = "2026-05-22"
EXPIRY_CODE = 1
API_PAUSE_SEC = 1.2
NIFTY_SECURITY_ID = 13

# Synchronised execution window parameter (1-to-1 matching)
OPTION_BAR_TF = 1
# SYSTEM AUDIT FIX: Locked paths inside the BackTesting folder layout explicitly
CACHE_DIR = (
    r"C:\Biplab\ALGO-Projects\Option-Scanner\BackTesting\Dependencies\backtest_cache"
)
RESULTS_DIR = (
    r"C:\Biplab\ALGO-Projects\Option-Scanner\BackTesting\Dependencies\backtest_results"
)
STRIKE_RANGE = 2

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

    # Pre-process mathematical columns on standard 1-minute tracking arrays
    df_1m = Indicators.add_ema(df_1m)
    df_1m = Indicators.add_vwap(df_1m)
    df_1m = Indicators.add_supertrend(df_1m)
    df_1m["RSI"] = Indicators.calculate_rsi_series(df_1m, period=14)

    # Process indicators across higher timeframes before flattening
    for d in [df_3m, df_5m, df_10m]:
        d = Indicators.add_ema(d)
    df_5m["ADX"] = Indicators.add_supertrend(df_5m)["ATR"]  # Maps ADX/ATR equivalents

    # Convert timestamps to explicit datetime structures for relational index tracking
    for df in [df_1m, df_3m, df_5m, df_10m]:
        df["start_Time"] = pd.to_datetime(df["start_Time"])

    # 3. Blends multi-timeframe trends into the base 1m framework via backward mapping
    df_3m_sub = df_3m[["start_Time", "EMA20", "EMA50"]].rename(
        columns={"EMA20": "EMA20_3m", "EMA50": "EMA50_3m"}
    )
    df_5m_sub = df_5m[["start_Time", "EMA20", "EMA50", "supertrend"]].rename(
        columns={"EMA20": "EMA20_5m", "EMA50": "EMA50_5m", "supertrend": "ADX_5m"}
    )
    df_10m_sub = df_10m[["start_Time", "EMA20", "EMA50"]].rename(
        columns={"EMA20": "EMA20_10m", "EMA50": "EMA50_10m"}
    )

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

    # Inject simulated Heikin-Ashi calculation arrays required for exit logic
    df_seda["HA_Close"] = (
        df_seda["open"] + df_seda["high"] + df_seda["low"] + df_seda["close"]
    ) / 4
    ha_opens = [df_seda["open"].iloc[0]]
    for idx in range(1, len(df_seda)):
        ha_opens.append((ha_opens[-1] + df_seda["HA_Close"].iloc[idx - 1]) / 2)
    df_seda["HA_Open"] = ha_opens
    df_seda["HA_Is_Red"] = df_seda["HA_Close"] < df_seda["HA_Open"]

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


def get_option_snapshot(legs, target_strike, option_type, bar_idx):
    """Retrieves standard structural snapshot blocks for specific options contracts."""
    for item in legs:
        if item["option_type"] != option_type:
            continue
        s = item["series"]
        if bar_idx >= len(s["close"]):
            continue
        if int(float(s["strike"][bar_idx])) == int(target_strike):
            oi = int(s["oi"][bar_idx])
            prev_oi = int(s["oi"][bar_idx - 1]) if bar_idx > 0 else oi
            vol = int(s["volume"][bar_idx])

            # Simulated dummy indicators for option snapshot matching
            return {
                "symbol": f"NIFTY_{int(target_strike)}_{option_type}",
                "display_symbol": f"NIFTY_{int(target_strike)}_{option_type}",
                "ltp": float(s["close"][bar_idx]),
                "volume": vol,
                "volume_ema": vol * 0.9 if vol > 0 else 1.0,
                "oi": oi,
                "oi_change": oi - prev_oi,
                "oi_change_pct": (
                    ((oi - prev_oi) / prev_oi * 100) if prev_oi > 0 else 0.0
                ),
                "premium_change_pct": 5.0,
                "bid_ask_spread_pct": 0.1,
                "option_vwap": float(s["close"][bar_idx]) * 0.98,
                "strike": target_strike,
                "option_type": option_type,
            }
    return None


# =====================================================================
# CORE SIMULATION ENGINE ROUTINE
# =====================================================================
def run_backtest(tsl, test_date, expiry_code=1):
    """
    Executes row-by-row multi-timeframe simulation.
    Handles exact strategy entries and injected exit tracking loops.
    """
    df_seda = build_seda_dataframe(tsl, test_date)
    legs = fetch_option_legs(tsl, test_date, expiry_code)

    in_position = False
    trade_logs = []

    # Position tracking context states
    entry_index_price = 0.0
    entry_premium = 0.0
    current_sl = 0.0
    active_contract = None

    supertrend_flipped = False
    sl_tightened = False

    print("\n[ENGINE EXECUTION] Starting 1-minute historical row sweep...")

    for i in range(3, len(df_seda)):
        row = df_seda.iloc[i]
        prev_row = df_seda.iloc[i - 1]

        curr_rsi = row.get("RSI", 50.0)
        prev_rsi = prev_row.get("RSI", 50.0)
        rsi_trigger = getattr(System_Config, "CE_RSI_TRIGGER", 65.0)

        # -----------------------------------------------------------------
        # STRUCTURE ENTRY GATEWAY (RSI crossed above 65)
        # -----------------------------------------------------------------
        if not in_position:
            if curr_rsi > rsi_trigger and prev_rsi <= rsi_trigger:

                # Determine ATM Strike Selection base profile
                spot = row["close"]
                atm_strike = round(spot / 50) * 50

                opt_snap = get_option_snapshot(legs, atm_strike, "CE", i)
                if opt_snap is None:
                    continue

                # Run the complete 100-Hour 165-point scoring engine validation layer
                score, action = core.build_score(opt_snap, "CE", df_seda.iloc[: i + 1])

                if action in ["BUY", "STRONG BUY"]:
                    in_position = True
                    active_contract = opt_snap
                    entry_index_price = spot

                    # Apply slippage configurations from system parameters
                    base_premium = opt_snap["ltp"]
                    slippage = getattr(System_Config, "BACKTEST_SLIPPAGE_PCT", 0.01)
                    entry_premium = base_premium * (1.0 + slippage)

                    current_sl = entry_premium - getattr(
                        System_Config, "INITIAL_SL_POINTS", 15.0
                    )
                    supertrend_flipped = False
                    sl_tightened = False

                    print(
                        f"[ORDER BUY] Row {i}: Entered CE contract at Premium: {entry_premium:.2f} | Score: {score} ({action})"
                    )
                    continue

        # -----------------------------------------------------------------
        # INTEGRATED MULTI-STAGE EXIT SYSTEM
        # -----------------------------------------------------------------
        elif in_position:
            opt_snap = get_option_snapshot(legs, active_contract["strike"], "CE", i)
            if opt_snap is None:
                continue

            # Delta 0.5 option tracking approximations derived from index movement coordinates
            opt_open = entry_premium + (row["open"] - entry_index_price) * 0.5
            opt_close = entry_premium + (row["close"] - entry_index_price) * 0.5
            opt_low = entry_premium + (row["low"] - entry_index_price) * 0.5

            # --- EXIT RULE 1: RSI DROPS BELOW 60 CUTOFF ---
            if curr_rsi < 60.0:
                in_position = False
                print(
                    f"[ORDER SELL - RSI CUTOFF] Row {i}: RSI dropped to {curr_rsi:.2f}. Exited premium: {opt_close:.2f}"
                )
                continue

            # --- EXIT RULE 2: SUPERTREND & HEIKIN-ASHI MONITOR ENGINE ---
            if row["ST_direction"] == -1:
                # Supertrend prints RED
                supertrend_flipped = True

            if supertrend_flipped:
                # Part A: 39-Second Trailing Warning (65% Weighting Proxy)
                if df_seda["HA_Is_Red"].iloc[i - 1] and not sl_tightened:
                    sim_index_39s = row["open"] + 0.65 * (row["close"] - row["open"])
                    sim_premium_39s = (
                        entry_premium + (sim_index_39s - entry_index_price) * 0.5
                    )

                    if sim_index_39s < row["HA_Open"]:
                        new_sl = sim_premium_39s - 5.0
                        if new_sl > current_sl:
                            current_sl = new_sl
                            sl_tightened = True
                            print(
                                f"[RISK TIGHTENED] Row {i}: Warning active at 39s. SL choked to {current_sl:.2f}"
                            )

                # Part B: Hard Stop (3 consecutive completely closed Red Heikin-Ashi bars)
                if (
                    df_seda["HA_Is_Red"].iloc[i - 1]
                    and df_seda["HA_Is_Red"].iloc[i - 2]
                    and df_seda["HA_Is_Red"].iloc[i - 3]
                ):
                    in_position = False
                    print(
                        f"[ORDER SELL - HARD EX] Row {i}: 3 Consecutive Red HA candles. Exited open premium: {opt_open:.2f}"
                    )
                    continue

            # --- EXIT RULE 3: ABSOLUTE STOP LOSS SAFETY GUARD ---
            if opt_low <= current_sl:
                in_position = False
                print(
                    f"[ORDER SELL - SL HIT] Row {i}: Option low crossed trailing boundary. Closed at: {current_sl:.2f}"
                )
                continue
