import datetime

# =========================================================
# CONFIGURATION
# =========================================================

GAP_RISK_THRESHOLD = 250

GAP_COOLDOWN_MINUTES = 20

MAX_VWAP_DISTANCE_PERCENT = 0.45

MAX_CANDLE_PERCENT = 0.45

CE_RSI_EXHAUSTION = 73

PE_RSI_EXHAUSTION = 39

RSI_LOOKBACK = 30

MARKET_OPEN = datetime.time(9, 15)

# =========================================================
# GAP DETECTION
# =========================================================

def detect_gap_risk(
    previous_close,
    today_open
):

    gap_points = abs(
        today_open - previous_close
    )

    if gap_points >= GAP_RISK_THRESHOLD:
        return True

    return False

# =========================================================
# GAP COOLDOWN
# =========================================================

def gap_cooldown_active():

    now = datetime.datetime.now()

    market_open = datetime.datetime.combine(
        now.date(),
        MARKET_OPEN
    )

    minutes_passed = (
        now - market_open
    ).total_seconds() / 60

    return minutes_passed < GAP_COOLDOWN_MINUTES

# =========================================================
# VWAP EXTENSION
# =========================================================

def vwap_overextended(
    close_price,
    vwap_price
):

    distance = abs(
        (
            close_price - vwap_price
        ) / vwap_price
    ) * 100

    return distance > MAX_VWAP_DISTANCE_PERCENT

# =========================================================
# CANDLE EXHAUSTION
# =========================================================

def candle_exhausted(row):

    candle_percent = (
        abs(
            row["close"] - row["open"]
        ) / row["open"]
    ) * 100

    return candle_percent > MAX_CANDLE_PERCENT

# =========================================================
# RSI MEMORY FILTER
# =========================================================

def recent_rsi_exhaustion(
    rsi_series,
    option_type
):

    recent = rsi_series.iloc[-RSI_LOOKBACK:]

    if option_type == "CE":

        return (
            recent > CE_RSI_EXHAUSTION
        ).any()

    if option_type == "PE":

        return (
            recent < PE_RSI_EXHAUSTION
        ).any()

    return False

# =========================================================
# MASTER RISK FILTER
# =========================================================

def allow_trade(
    df_1m,
    rsi_series,
    option_type,
    previous_close,
    today_open
):

    # -----------------------------------------
    # GAP RISK
    # -----------------------------------------

    gap_mode = detect_gap_risk(
        previous_close,
        today_open
    )

    if gap_mode:

        if gap_cooldown_active():
            return False

    # -----------------------------------------
    # CURRENT BAR
    # -----------------------------------------

    row = df_1m.iloc[-2]

    # -----------------------------------------
    # VWAP OVEREXTENSION
    # -----------------------------------------

    if vwap_overextended(
        row["close"],
        row["VWAP"]
    ):
        return False

    # -----------------------------------------
    # CANDLE EXHAUSTION
    # -----------------------------------------

    if candle_exhausted(row):
        return False

    # -----------------------------------------
    # RSI MEMORY FILTER
    # -----------------------------------------

    if recent_rsi_exhaustion(
        rsi_series,
        option_type
    ):
        return False

    return True


def explain_allow_trade_block(
    df_1m,
    rsi_series,
    option_type,
    previous_close,
    today_open,
):
    """Return why allow_trade would block; empty string if trade is allowed."""
    gap_mode = detect_gap_risk(previous_close, today_open)

    if gap_mode and gap_cooldown_active():
        return "gap_cooldown_active"

    row = df_1m.iloc[-2]

    if vwap_overextended(row["close"], row["VWAP"]):
        distance = abs((row["close"] - row["VWAP"]) / row["VWAP"]) * 100
        return f"vwap_overextended_{distance:.2f}pct"

    if candle_exhausted(row):
        candle_pct = abs(row["close"] - row["open"]) / row["open"] * 100
        return f"candle_exhausted_{candle_pct:.2f}pct"

    if recent_rsi_exhaustion(rsi_series, option_type):
        return f"recent_rsi_exhaustion_{option_type}"

    return ""