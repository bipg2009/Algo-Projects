import math
from System_Config import (
    TARGET_POINTS, INITIAL_SL_POINTS,
    LOT_SIZES, DEFAULT_LOT_SIZE, DEPLOYED_CAPITAL
)


def get_lot_size(option_symbol: str) -> int:
    """Returns lot size for the given option symbol using System_Config.LOT_SIZES."""
    sym_upper = str(option_symbol).upper()
    for key, size in LOT_SIZES.items():
        if key in sym_upper:
            return size
    return DEFAULT_LOT_SIZE


from models import TradeParameters

def calculate_trade_parameters(ltp: float, option_symbol: str, margin_requirement_pc: float) -> TradeParameters:
    """
    Dedicated Trade_Calculator: math engine for execution packages.
    Calculates Margin, Target Points, Stop Loss, and Qty before Dhan API firing.
    """
    lot_size = get_lot_size(option_symbol)
    
    parsed_ltp = float(ltp) if ltp else 0.1
    lots = int(DEPLOYED_CAPITAL // (parsed_ltp * lot_size))
    if lots < 1:
        lots = 1
        
    # Revert to shares because DhanHQ requires shares, and the ALGO expects shares
    qty = lot_size * lots
    target_price = round(float(ltp) + TARGET_POINTS, 2)
    sl_price = round(float(ltp) - INITIAL_SL_POINTS, 2)
    
    pct_val = margin_requirement_pc if margin_requirement_pc < 1.0 else (margin_requirement_pc / 100.0)
    estimated_margin = round(float(qty * ltp * pct_val), 2)
    
    return TradeParameters(
        symbol=option_symbol,
        qty=qty,
        target_price=target_price,
        sl_price=sl_price,
        estimated_margin=estimated_margin
    )
