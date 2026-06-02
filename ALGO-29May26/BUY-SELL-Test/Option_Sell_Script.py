import time
import pandas as pd
from pathlib import Path
from MainEngine import get_live_client
from System_Config import ENABLE_ORDER_EXECUTION

def execute_manual_market_order(tsl):
    print("\n" + "="*50)
    print("      MANUAL OPTION MARKET ORDER EXECUTION")
    print("="*50)

    # 1. Ask for Option Type
    opt_type_input = input("\nEnter option type (C for CALL / P for PUT): ").strip().upper()
    if opt_type_input in ["C", "CALL"]:
        opt_type = "CE"
    elif opt_type_input in ["P", "PUT"]:
        opt_type = "PE"
    else:
        print("[!] Invalid option type. Exiting.")
        return

    # 2. Ask for Strike Price
    try:
        strike_input = input(f"\nEnter {opt_type} Strike Price (e.g., 23000): ").strip()
        strike_price = float(strike_input)
    except ValueError:
        print("[!] Invalid strike price. Exiting.")
        return

    # Assuming current weekly expiry formatting "NIFTY 02 JUN" based on the error output user showed.
    # We will construct a symbol dynamically. In Dhan, if instrument is not perfect, it fails.
    # The user was trading "NIFTY 02 JUN 23850 CALL" / PUT. Let's make it smart enough to construct that if the user traded before it.
    underlying = "NIFTY"
    expiry_format = "02 JUN" # User specified same week expiry (2nd June)
    call_put_word = "CALL" if opt_type == "CE" else "PUT"
    
    # E.g. "NIFTY 02 JUN 23850 CALL"
    # But checking Dhan_Tradehull typically trading symbol for NIFTY options goes like NIFTY24JUN23850CE or similar.
    # Wait, the logs show: ">> WILL SHORT SELL: NIFTY 02 JUN 23850 CALL" -> That's probably the printed name or exact symbol in custom dictionary?
    # Let's search inside instrument_df to find the EXACT symbol matching the user's requirement.
    
    # 3. Find exactly this strike and option type in NIFTY current expiry.
    print(f"\n🔍 Searching for NIFTY {opt_type} {strike_price} for nearest expiry...")
    try:
        df = tsl.instrument_df
        # Filter for NIFTY options
        opt_df = df[(df['SEM_EXM_EXCH_ID'].isin(['NFO', 'NSE'])) & 
                    (df['SEM_INSTRUMENT_NAME'] == 'OPTIDX') & 
                    ((df['SEM_TRADING_SYMBOL'].str.startswith('NIFTY')) | 
                     (df['SEM_CUSTOM_SYMBOL'].str.startswith('NIFTY')))]
                     
        if opt_df.empty:
            print("[!] Could not find any NIFTY options in instrument lists.")
            return

        # Ensure numeric strike
        opt_df = opt_df.copy()
        opt_df['SEM_STRIKE_PRICE'] = pd.to_numeric(opt_df['SEM_STRIKE_PRICE'], errors='coerce')
        
        # Filter by requested Strike and CE/PE
        target_df = opt_df[(opt_df['SEM_STRIKE_PRICE'] == strike_price) & (opt_df['SEM_OPTION_TYPE'] == opt_type)]
        
        if target_df.empty:
            print(f"[!] Could not find any contract for NIFTY {strike_price} {opt_type}.")
            return
            
        # Get the one with the earliest expiry
        target_df = target_df.sort_values(by='SEM_EXPIRY_DATE')
        candidate = target_df.iloc[0]
        
        # Prefer Trading Symbol
        trading_sym = candidate['SEM_TRADING_SYMBOL']
        custom_sym = candidate['SEM_CUSTOM_SYMBOL']
        expiry_date = candidate['SEM_EXPIRY_DATE']
        
        sym_to_trade = trading_sym if pd.notna(trading_sym) and trading_sym else custom_sym
        exch = "NFO" 
        
        print(f"   -> FOUND: {sym_to_trade} (Expiry: {expiry_date})")

    except Exception as e:
        print(f"[!] Error finding contract: {e}")
        return

    # 4. Ask for Quantity
    try:
        qty_input = input("\nEnter Quantity (e.g. 75 for NIFTY) [Default: 75]: ").strip()
        qty = int(qty_input) if qty_input else 75
    except ValueError:
        print("[!] Invalid quantity. Exiting.")
        return

    # 5. Confirm Execution
    print(f"\n--- SELL ORDER CONFIRMATION ---")
    print(f" >> WILL SHORT SELL: {sym_to_trade}")
    print(f" >> QUANTITY: {qty}")
    print(f" >> ORDER TYPE: MARKET (MIS)")
    
    conf = input(f"\nPlace Order NOW? [Y/N] [Default: Y]: ").strip().upper()
    if not conf:
        conf = "Y"
        
    if conf != "Y":
        print("Action Cancelled by User.")
        return

    # 6. Execute Order directly to broker API
    print("\n[+] Routing SELL Limit Order (Marketable)...")
    if not ENABLE_ORDER_EXECUTION:
        print(f"[\033[93mSIMULATION\033[0m] Sell Order for {sym_to_trade}")
        return

    try:
        def round_to_tick(price, tick_size=0.05):
            return round(round(price / tick_size) * tick_size, 2)
            
        ltp = float(tsl.get_ltp(sym_to_trade))
        print(f"   -> Current LTP of {sym_to_trade}: {ltp}")
        limit_price = round_to_tick(ltp * 0.90)  # 10% below LTP to trigger immediately
        if limit_price <= 0.05:
            limit_price = 0.05
        
        print(f"   -> Sending LIMIT order at Price: {limit_price} (Product: MARGIN)")
        
        order_response = tsl.order_placement(
            tradingsymbol=sym_to_trade,
            exchange=exch,
            quantity=qty,
            price=limit_price,
            trigger_price=0,
            order_type="LIMIT",
            transaction_type="SELL",
            trade_type="MARGIN"
        )
        print(f"[\033[92mSUCCESS\033[0m] Order Request Sent. API Response: {order_response}")
    except Exception as e:
        print(f"[\033[91mFAILED\033[0m] Order API Exception: {e}")
        print("Detailed Error typically means Dhan rejected the order parameters (e.g. Market order not allowed).")

if __name__ == "__main__":
    tsl = get_live_client()
    if not tsl:
        print("Could not connect to broker.")
    else:
        execute_manual_market_order(tsl)
