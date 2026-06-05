import pandas as pd
from typing import Optional, Dict, Any

# Order Book Imbalance (OBI) Strategy
# Duration: Short-term momentum scalp
# Strategy: Detects significant imbalance between displayed Bid/Ask quantities in the order book.

def init() -> None:
    pass

def start() -> None:
    pass

def stop() -> None:
    pass

def health_check() -> bool:
    return True

_imbalance_history: Dict[str, list] = {}

def _calculate_imbalance(bid_qty: float, ask_qty: float) -> float:
    total = bid_qty + ask_qty
    if total == 0:
        return 0.0
    return (bid_qty - ask_qty) / total

def detect_obi_signal(quote_data: Dict[str, Any], df_1m: pd.DataFrame) -> Optional[Dict[str, Any]]:
    global _imbalance_history
    if not quote_data or df_1m is None or len(df_1m) < 2:
        return None

    symbol = quote_data.get("symbol", "DEFAULT")
    total_buy_qty = quote_data.get("total_buy_quantity", 0)
    total_sell_qty = quote_data.get("total_sell_quantity", 0)
    
    imbalance = _calculate_imbalance(total_buy_qty, total_sell_qty)
    
    history = _imbalance_history.get(symbol, [])
    history.append(imbalance)
    if len(history) > 60:
        history.pop(0)
    _imbalance_history[symbol] = history
    
    if len(history) < 20:
        return None
        
    series = pd.Series(history)
    rolling_mean = series.mean()
    rolling_std = series.std()
    if pd.isna(rolling_std):
        rolling_std = 0.0
        
    upper_threshold = rolling_mean + 2 * rolling_std
    lower_threshold = rolling_mean - 2 * rolling_std
        
    current = df_1m.iloc[-1]
    previous = df_1m.iloc[-2]
    
    current_vol = current.get("volume", 0)
    avg_vol = current.get("volume_ma_20", 0) 
    if current_vol <= 1.5 * avg_vol:
        return None
    
    curr_close = current.get("close", 0)
    prev_close = previous.get("close", 0)
    vwap = current.get("VWAP", 0)

    last_3 = history[-3:]
    is_persistent_buy = all(x > upper_threshold for x in last_3)
    is_persistent_sell = all(x < lower_threshold for x in last_3)

    atr = current.get("ATR", 15)
    target_distance = 1.5 * atr
    sl_distance = 0.5 * atr
    
    ema20 = current.get("EMA_20", 0)
    ema50 = current.get("EMA_50", 0)
    pcr = quote_data.get("pcr", 1.0) # Default to neutral if absent

    # Price confirmation: Price moving up + True Imbalance + VWAP
    if is_persistent_buy and curr_close > prev_close and curr_close > vwap:
        if ema20 > ema50 and pcr >= 0.60:
            return {
                "signal": "BUY",
                "option_type": "CE",
                "delta_target": 0.50,
                "reason": f"Buy OBI + Price + VWAP + EMA Trend",
                "sl_underlying": curr_close - sl_distance,
                "target_underlying": curr_close + target_distance,
                "trail_activation_underlying": curr_close + (atr * 1.0),
                "trail_step_underlying": atr * 0.5,
                "strategy": "obi"
            }
        
    if is_persistent_sell and curr_close < prev_close and curr_close < vwap:
        if ema20 < ema50 and pcr <= 1.40:
            return {
                "signal": "BUY",
                "option_type": "PE",
                "delta_target": 0.50,
                "reason": f"Sell OBI + Price + VWAP + EMA Trend",
                "sl_underlying": curr_close + sl_distance,
                "target_underlying": curr_close - target_distance,
                "trail_activation_underlying": curr_close - (atr * 1.0),
                "trail_step_underlying": atr * 0.5,
                "strategy": "obi"
            }

    return None
