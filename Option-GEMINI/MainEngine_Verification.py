import SafetyLogger
from System_Config import *

def verify_trade_calculations(ltp, option_symbol, calc_package, margin_requirement_pc):
    """
    Crucial verification step: independently recalculates math for Qty, SL, Target, Margin.
    Matches calculated numbers against the calc_package exactly to prevent catastrophic errors.
    """
    try:
        print(f"[Core Verification] Independently recalculating math for {option_symbol} at LTP {ltp}...")
        
        # Independent Constants
        TRADING_LOTS = 1
        
        expected_lot_size = 75
        sym_upper = str(option_symbol).upper()
        if "SENSEX" in sym_upper:
            expected_lot_size = 20
        elif "RELIANCE" in sym_upper:
            expected_lot_size = 500
        elif "FINNIFTY" in sym_upper:
            expected_lot_size = 60
        elif "BANKNIFTY" in sym_upper:
            expected_lot_size = 30
        elif "NIFTY" in sym_upper:
            expected_lot_size = 65
        
        parsed_ltp = float(ltp) if ltp else 0.1
        DEPLOYED_CAPITAL = 100000.0
        lots = int(DEPLOYED_CAPITAL // (parsed_ltp * expected_lot_size))
        if lots < 1:
            lots = 1
            
        expected_qty = expected_lot_size * lots
        expected_target = round(float(ltp) + TARGET_POINTS, 2)
        expected_sl = round(float(ltp) - INITIAL_SL_POINTS, 2)
        
        pct_val = margin_requirement_pc if margin_requirement_pc < 1.0 else (margin_requirement_pc / 100.0)
        expected_margin = round(float(expected_qty * ltp * pct_val), 2)
        
        is_valid = True
        if calc_package["qty"] != expected_qty:
            print(f"[-] QTY Verification Failed! expected {expected_qty}, got {calc_package['qty']}")
            is_valid = False
        if calc_package["target_price"] != expected_target:
            print(f"[-] Target Verification Failed! expected {expected_target}, got {calc_package['target_price']}")
            is_valid = False
        if calc_package["sl_price"] != expected_sl:
            print(f"[-] SL Verification Failed! expected {expected_sl}, got {calc_package['sl_price']}")
            is_valid = False
        if float(calc_package["estimated_margin"]) != expected_margin:
            print(f"[-] Margin Verification Failed! expected {expected_margin}, got {calc_package['estimated_margin']}")
            is_valid = False
            
        if is_valid:
            print("[+] MainEngine Verification SUCCESS. Green Light for execution!")
            
        return is_valid
    except Exception as e:
        SafetyLogger.log_error_with_context(
            "MainEngine_Verification", "verify_trade_calculations", e,
            {"ltp": ltp, "symbol": option_symbol, "calc_package": calc_package}
        )
        return False
