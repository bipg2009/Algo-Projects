import math
from System_Config import TARGET_POINTS, INITIAL_SL_POINTS

def get_lot_size(option_symbol):
    sym_upper = str(option_symbol).upper()
    if "SENSEX" in sym_upper:
        return 20
    elif "RELIANCE" in sym_upper:
        return 500
    elif "FINNIFTY" in sym_upper:
        return 60
    elif "BANKNIFTY" in sym_upper:
        return 30
    elif "NIFTY" in sym_upper:
        return 65
    return 65

def calculate_trade_parameters(ltp, option_symbol, margin_requirement_pc):
    """
    Dedicated Trade_Calculator: math engine for execution packages.
    Calculates Margin, Target Points, Stop Loss, and Qty before Dhan API firing.
    """
    lot_size = get_lot_size(option_symbol)
    
    parsed_ltp = float(ltp) if ltp else 0.1
    DEPLOYED_CAPITAL = 100000.0
    lots = int(DEPLOYED_CAPITAL // (parsed_ltp * lot_size))
    if lots < 1:
        lots = 1
        
    qty = lot_size * lots
    target_price = round(float(ltp) + TARGET_POINTS, 2)
    sl_price = round(float(ltp) - INITIAL_SL_POINTS, 2)
    
    pct_val = margin_requirement_pc if margin_requirement_pc < 1.0 else (margin_requirement_pc / 100.0)
    estimated_margin = round(float(qty * ltp * pct_val), 2)
    
    return {
        "symbol": option_symbol,
        "qty": qty,
        "target_price": target_price,
        "sl_price": sl_price,
        "estimated_margin": estimated_margin,
    }
