import time
import pandas as pd
from pathlib import Path
from MainEngine import get_live_client
from market_data_engine import fetch_chain, get_nifty_1m_cached
from System_Config import UNDERLYING, ENABLE_ORDER_EXECUTION

OFFSET_POINTS = 100  # Distance from ATM to create the strangle (e.g. 100 pts OTM)

def execute_sell_otm_strangle(tsl, enable_order=True):
    print("\n🔍 Fetching Option Chain for STRANGLE SELL Analysis...")
    # Fetch wider chain directly to avoid excel ITM-only filter
    chain = tsl.get_option_chain(underlying=UNDERLYING, strike_range=15)
    if not chain or not chain.get("spot") or not chain.get("options"):
        print("[!] Failed to fetch option chain.")
        return

    nifty_spot = float(chain["spot"])
    # Determine ATM strike (rounding to nearest 50)
    atm_strike = round(nifty_spot / 50) * 50
    print(f"📊 NIFTY Spot: {nifty_spot:.2f} | Base ATM: {atm_strike}")

    ce_strike_target = atm_strike + OFFSET_POINTS
    pe_strike_target = atm_strike - OFFSET_POINTS

    options_df = pd.DataFrame(chain["options"])
    
    # Locate exact contracts
    ce_candidate = options_df[(options_df["strike"] == ce_strike_target) & (options_df["option_type"] == "CE")]
    pe_candidate = options_df[(options_df["strike"] == pe_strike_target) & (options_df["option_type"] == "PE")]

    ce_symbol = ce_candidate.iloc[0]["symbol"] if not ce_candidate.empty else None
    pe_symbol = pe_candidate.iloc[0]["symbol"] if not pe_candidate.empty else None

    print(f"   -> OTM CE Target (+{OFFSET_POINTS}): {ce_symbol} @ Strike {ce_strike_target}")
    print(f"   -> OTM PE Target (-{OFFSET_POINTS}): {pe_symbol} @ Strike {pe_strike_target}")

    if not ce_symbol and not pe_symbol:
        print("[!] Could not find OTM contracts. Adjust OFFSET_POINTS or check chain.")
        return

    # Determine market condition
    print("📈 Analyzing Market Trend (Nifty 1m, 10-3 Supertrend)...")
    df_1m = get_nifty_1m_cached(tsl)
    st_color = "UNKNOWN"
    rsi = 50.0

    if df_1m is not None and not df_1m.empty and len(df_1m) > 1:
        if "st_color" in df_1m.columns:
            st_color = str(df_1m.iloc[-2]["st_color"]).upper()
            
        import indicator_engine as ie
        rsi_series = ie.calculate_rsi_series(df_1m)
        if len(rsi_series) >= 2:
            rsi = rsi_series.iloc[-2]

    print(f"   -> Market RSI: {rsi:.2f}")
    print(f"   -> Market SuperTrend: {st_color}")

    # Decision Matrix
    to_sell = []
    
    if st_color == "GREEN" and rsi > 55:
        # Strongly Bullish -> Sell OTM PE only
        print("💡 Condition: BULLISH (Supertrend GREEN + High RSI). Selling OTM PE.")
        if pe_symbol: to_sell.append(pe_symbol)
        
    elif st_color == "RED" and rsi < 45:
        # Strongly Bearish -> Sell OTM CE only
        print("💡 Condition: BEARISH (Supertrend RED + Low RSI). Selling OTM CE.")
        if ce_symbol: to_sell.append(ce_symbol)
        
    else:
        # Sideways/Chop -> Sell both creating a Short Strangle
        print("💡 Condition: SIDEWAYS. Selling BOTH (Short Strangle).")
        if ce_symbol: to_sell.append(ce_symbol)
        if pe_symbol: to_sell.append(pe_symbol)

    if not to_sell:
        print("[!] No symbols selected for execution.")
        return
        
    print("\n--- SELL ORDER CONFIRMATION ---")
    for s in to_sell:
        print(f" >> WILL SHORT SELL: {s}")
        
    qty_str = input("\nEnter Quantity (e.g. 50): ").strip()
    try:
        qty = int(qty_str)
    except:
        print("Invalid Quantity. Cancelled.")
        return
        
    conf = input(f"Are you sure you want to Market SELL {qty} quantity of the above options? [Y/N]: ").strip().upper()
    if conf != "Y":
        print("Action Cancelled by User.")
        return

    print("\n[+] Routing MIS SELL Market Orders...")
    for sym in to_sell:
        exch = "BFO" if sym.startswith(("SENSEX", "BANKEX")) else "NFO"
        if not enable_order:
            print(f"[\033[93mSIMULATION\033[0m] Sell Order for {sym}")
            continue
            
        try:
            order_id = tsl.order_placement(
                tradingsymbol=sym,
                exchange=exch,
                quantity=qty,
                price=0,
                trigger_price=0,
                order_type="MARKET",
                transaction_type="SELL",
                trade_type="MIS"
            )
            print(f"[\033[92mSUCCESS\033[0m] Placed SELL order for {sym} | ID: {order_id}")
        except Exception as e:
            print(f"[\033[91mFAILED\033[0m] Order for {sym} failed: {e}")

if __name__ == "__main__":
    tsl = get_live_client()
    if not tsl:
        print("Could not connect to broker.")
    else:
        execute_sell_otm_strangle(tsl, ENABLE_ORDER_EXECUTION)
