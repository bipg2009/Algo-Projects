import time
import datetime
import pdb

client_id = ""
access_token = ""
# =========================================================
# IMPORT ENGINES
# =========================================================

import Option_strategy_core as strategy_engine
import Risk_Engine as risk_engine
import Monitor_Engine as monitor_engine
import Dhan_Tradehull as tradehull  

# =========================================================
# CONFIGURATION
# =========================================================

SCAN_INTERVAL = 2

ENABLE_ORDER_EXECUTION = False

ENABLE_PDB_PAUSE_AFTER_SIGNAL = True

# =========================================================
# MOCK MARKET DATA FETCHER
# Replace Later With:
# - Broker API
# - NSE Feed
# - Websocket
# =========================================================

def fetch_market_data():

    """
    PLACEHOLDER FUNCTION

    Replace with live market feeds later.
    """

    market_data = {

        "df_1m": None,

        "option_row": {

            "symbol": "NIFTY 24000 CE",

            "ltp": 24.00,

            "volume": 250000,

            "oi_change": 8.5,

            "score": 86
        },

        "option_type": "CE",

        "nifty_spot": 24100,

        "previous_close": 23920,

        "today_open": 24150,

        "pcr_value": 1.18
    }

    return market_data

# =========================================================
# PRINT SIGNAL
# =========================================================

def print_signal(
    option_symbol,
    option_type,
    ltp,
    score
):

    print("\n")

    print(
        "===================================================="
    )

    print(
        "🔥 STRONG BUY SIGNAL DETECTED"
    )

    print(
        f"Instrument : {option_symbol}"
    )

    print(
        f"Type       : {option_type}"
    )

    print(
        f"LTP        : Rs {ltp}"
    )

    print(
        f"Score      : {score}"
    )

    print(
        f"Time       : "
        f"{datetime.datetime.now().strftime('%H:%M:%S')}"
    )

    print(
        "===================================================="
    )

    print("\n")

# =========================================================
# PDB SAFE HOLD MODE
# =========================================================

def pause_engine_until_continue():

    print("\n")

    print(
        "===================================================="
    )

    print(
        "🛑 HYPERCARE SAFE HOLD ACTIVATED"
    )

    print(
        "Scanner paused after signal detection."
    )

    print(
        "Manually monitor the setup."
    )

    print(
        "Once trade is completed manually:"
    )

    print(
        "Type: c"
    )

    print(
        "Then press ENTER to resume scanner."
    )

    print(
        "===================================================="
    )

    print("\n")

    pdb.set_trace()

# =========================================================
# MAIN HYPERCARE LOOP
# =========================================================

def run_hypercare_engine():

    print("\n")

    print(
        "===================================================="
    )

    print(
        "HYPERCARE ENGINE STARTED"
    )

    print(
        "ORDER EXECUTION DISABLED"
    )

    print(
        "SIGNAL MONITOR MODE ACTIVE"
    )

    print(
        "===================================================="
    )

    print("\n")

    print(
        "NOTE: fetch_market_data() has no live feed (df_1m=None). "
        "For production scanning run: py Market_Scanner.py"
    )

    print("\n")

    last_wait_msg = 0.0

    while True:

        try:

            # -------------------------------------------------
            # FETCH MARKET DATA
            # -------------------------------------------------

            market_data = fetch_market_data()

            df_1m = market_data.get("df_1m")

            opt_row = market_data.get("option_row")

            option_type = market_data.get("option_type")

            nifty_spot = market_data.get("nifty_spot")

            previous_close = market_data.get("previous_close")

            today_open = market_data.get("today_open")

            pcr_value = market_data.get("pcr_value")

            # -------------------------------------------------
            # BASIC NULL CHECKS
            # -------------------------------------------------

            if not opt_row:

                time.sleep(SCAN_INTERVAL)

                continue

            if df_1m is None or df_1m.empty or len(df_1m) < 30:

                now = time.time()
                if now - last_wait_msg >= 30:
                    print(
                        f"[{datetime.datetime.now().strftime('%H:%M:%S')}] "
                        "MainEngine idle — no live 1m bars. "
                        "Use Market_Scanner.py for live NIFTY + option scan.",
                        flush=True,
                    )
                    last_wait_msg = now

                time.sleep(SCAN_INTERVAL)

                continue

            # -------------------------------------------------
            # RISK ENGINE CHECK (must match Risk_Engine.allow_trade signature)
            # -------------------------------------------------

            rsi_series = strategy_engine.calculate_rsi_series(df_1m)

            allowed_trade = risk_engine.allow_trade(
                df_1m,
                rsi_series,
                option_type,
                previous_close,
                today_open,
            )

            if not allowed_trade:

                print(

                    f"[{datetime.datetime.now().strftime('%H:%M:%S')}] "

                    f"Risk Engine blocked trade."
                )

                time.sleep(SCAN_INTERVAL)

                continue

            # -------------------------------------------------
            # STRATEGY ENGINE CHECK (also runs allow_trade internally)
            # -------------------------------------------------

            trigger = strategy_engine.detect_trigger_1m(

                df_1m=df_1m,

                option_type=option_type,

                opt_row=opt_row,

                nifty_spot=nifty_spot,

                previous_close=previous_close,

                today_open=today_open,

                pcr_value=pcr_value
            )

            # -------------------------------------------------
            # SIGNAL DETECTED
            # -------------------------------------------------

            if trigger:

                option_symbol = opt_row.get("symbol")

                ltp = opt_row.get("ltp", 0)

                score = opt_row.get("score", 86)

                print_signal(

                    option_symbol=option_symbol,

                    option_type=option_type,

                    ltp=ltp,

                    score=score
                )

                # ---------------------------------------------
                # SAFE MODE
                # ---------------------------------------------

                print(
                    "[SAFE MODE] "
                    "Live order execution disabled."
                )

                # ---------------------------------------------
                # PAUSE SCANNER
                # ---------------------------------------------

                if ENABLE_PDB_PAUSE_AFTER_SIGNAL:

                    pause_engine_until_continue()

            # -------------------------------------------------
            # HEARTBEAT
            # -------------------------------------------------

            else:

                print(

                    f"[{datetime.datetime.now().strftime('%H:%M:%S')}] "

                    f"Scanning market..."
                )

            # -------------------------------------------------
            # LOOP DELAY
            # -------------------------------------------------

            time.sleep(SCAN_INTERVAL)

        except Exception as e:

            print("\n")

            print(
                "===================================================="
            )

            print(
                "MAIN ENGINE ERROR"
            )

            print(
                str(e)
            )

            print(
                "===================================================="
            )

            print("\n")

            time.sleep(5)

# =========================================================
# START ENGINE
# =========================================================

if __name__ == "__main__":

    run_hypercare_engine()