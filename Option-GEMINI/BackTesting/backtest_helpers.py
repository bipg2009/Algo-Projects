"""Backtest-only helpers (do not modify Option_strategy_core.py)."""

import datetime

import pandas as pd

IST = "Asia/Kolkata"
MARKET_OPEN_TIME = datetime.time(9, 15)
MARKET_SESSION_END = datetime.time(15, 30)
MARKET_EXIT_TIME = datetime.time(15, 12)
MARKET_ENTRY_CUTOFF = datetime.time(14, 30)


def to_ist(ts):
    dt = pd.to_datetime(ts)
    if dt.tzinfo is None:
        dt = dt.tz_localize("UTC")
    return dt.tz_convert(IST)


def format_ist(ts):
    return to_ist(ts).strftime("%d-%m-%y %H:%M:%S IST")


def format_ist_time(ts):
    return to_ist(ts).strftime("%H:%M:%S IST")


def report_date_slug(test_date):
    dt = pd.to_datetime(test_date, dayfirst=True)
    return dt.strftime("%d-%m-%y")


def bar_time_ist(bar_time):
    return to_ist(bar_time).time()


def is_within_session(bar_time):
    t = bar_time_ist(bar_time)
    return MARKET_OPEN_TIME <= t <= MARKET_SESSION_END


def is_entry_time_allowed(bar_time):
    t = bar_time_ist(bar_time)
    return MARKET_OPEN_TIME <= t < MARKET_ENTRY_CUTOFF


def trade_outcome(price, trailing_sl, is_sell):
    """trailing_sl - price: positive = Success, negative = Failure."""
    if not is_sell:
        return ""
    diff = float(trailing_sl) - float(price)
    if diff > 0:
        return "Success"
    if diff < 0:
        return "Failure"
    return ""


def normalize_event(event):
    upper = (event or "").upper()
    if "BUY" in upper:
        return "BUY"
    if "SELL" in upper:
        return "SELL"
    return event


def entry_levels(entry_ltp):
    import Option_strategy_core as core

    return {
        "target": round(float(entry_ltp) + core.TARGET_POINTS, 2),
        "sl": round(float(entry_ltp) - core.INITIAL_SL_POINTS, 2),
    }


def add_supertrend(df, period=10, multiplier=3):
    """Add ST column + ST_COLOR for detect_trigger_1m (backtest only)."""
    work = df.copy()
    hl2 = (work["high"] + work["low"]) / 2
    tr = pd.concat(
        [
            work["high"] - work["low"],
            (work["high"] - work["close"].shift()).abs(),
            (work["low"] - work["close"].shift()).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr = tr.ewm(alpha=1 / period, adjust=False).mean()
    upper = hl2 + multiplier * atr
    lower = hl2 - multiplier * atr
    st = pd.Series(index=work.index, dtype=float)
    for i in range(len(work)):
        if i == 0:
            st.iloc[i] = upper.iloc[i]
            continue
        prev = st.iloc[i - 1]
        if work["close"].iloc[i] > prev:
            st.iloc[i] = max(lower.iloc[i], prev)
        else:
            st.iloc[i] = min(upper.iloc[i], prev)
    work["ST"] = st
    work["ST_COLOR"] = (work["close"] >= work["ST"]).map({True: "GREEN", False: "RED"})
    return work


def prepare_nifty_1m(df):
    import Option_strategy_core as core

    work = core.add_vwap(df.copy())
    work = core.add_ema(work)
    return add_supertrend(work)


def pcr_from_chain(chain):
    options = chain.get("options") or []
    call_oi = sum(int(o.get("oi", 0)) for o in options if o.get("option_type") == "CE")
    put_oi = sum(int(o.get("oi", 0)) for o in options if o.get("option_type") == "PE")
    if call_oi <= 0:
        return 1.0
    return round(put_oi / call_oi, 4)
