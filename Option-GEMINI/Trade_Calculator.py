import math
import SafetyLogger
from System_Config import *

def get_lot_size(option_symbol):
    try:
        sym_upper = str(option_symbol).upper() if option_symbol else ""
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
    except Exception as e:
        SafetyLogger.log_error_with_context("Trade_Calculator", "get_lot_size", e, {"option_symbol": option_symbol})
        return 65

def calculate_trade_parameters(ltp, option_symbol, margin_requirement_pc):
    """
    Dedicated Trade_Calculator: math engine for execution packages.
    Calculates Margin, Target Points, Stop Loss, and Qty before Dhan API firing.
    """
    try:
        parsed_ltp = float(ltp) if ltp else 0.1
        DEPLOYED_CAPITAL = 100000.0
        lot_size = get_lot_size(option_symbol)
        
        lots = math.floor(DEPLOYED_CAPITAL / (parsed_ltp * lot_size))
        if lots < 1:
            lots = 1
            
        qty = lots * lot_size
        
        target_price = round(parsed_ltp + TARGET_POINTS, 2)
        sl_price = round(parsed_ltp - INITIAL_SL_POINTS, 2)
        
        parsed_margin_pc = float(margin_requirement_pc) if margin_requirement_pc else 0.12
        pct_val = parsed_margin_pc if parsed_margin_pc < 1.0 else (parsed_margin_pc / 100.0)
        estimated_margin = round(float(qty * parsed_ltp * pct_val), 2)
        
        return {
            "symbol": option_symbol,
            "qty": qty,
            "target_price": target_price,
            "sl_price": sl_price,
            "estimated_margin": estimated_margin,
        }
    except Exception as e:
        SafetyLogger.log_error_with_context(
            "Trade_Calculator", "calculate_trade_parameters", e,
            {"ltp": ltp, "symbol": option_symbol, "margin_pc": margin_requirement_pc}
        )
        return {
            "symbol": option_symbol,
            "qty": 65,
            "target_price": 0.0,
            "sl_price": 0.0,
            "estimated_margin": 0.0,
        }
