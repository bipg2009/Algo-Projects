from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import datetime

@dataclass
class TradeParameters:
    symbol: str
    qty: int
    target_price: float
    sl_price: float
    estimated_margin: float

@dataclass
class TradePosition:
    symbol: str
    option_type: str
    qty: int
    entry_ltp: float
    target: float
    sl: float
    initial_sl: float
    margin_used: float
    entry_time: datetime.datetime
    entry_oi: int = 0
    peak_price: float = 0.0
    strategy_suffix: str = ""
    breakeven_triggered: bool = False
    entry_spot: float = 0.0
    spot_sl: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "option_type": self.option_type,
            "qty": self.qty,
            "entry_ltp": self.entry_ltp,
            "target": self.target,
            "sl": self.sl,
            "initial_sl": self.initial_sl,
            "margin_used": self.margin_used,
            "entry_time": self.entry_time,
            "entry_oi": self.entry_oi,
            "peak_price": max(self.peak_price, self.entry_ltp),
            "strategy_suffix": self.strategy_suffix,
            "breakeven_triggered": self.breakeven_triggered,
            "entry_spot": self.entry_spot,
            "spot_sl": self.spot_sl
        }
