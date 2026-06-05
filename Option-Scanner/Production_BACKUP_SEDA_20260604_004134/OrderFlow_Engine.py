import time
from collections import deque
import logging

class OrderFlowEngine:
    def __init__(self, threshold_pct=10.0, window_minutes=3.0):
        self.threshold_pct = threshold_pct
        self.window_seconds = window_minutes * 60
        self.history = deque() # tuples of (timestamp, ce_bids, pe_bids)
        self.logger = logging.getLogger("OrderFlow")

    def record_snapshot(self, tsl, atm_ce_symbol, atm_pe_symbol):
        if not tsl:
            return
            
        try:
            ce_depth = tsl.get_market_depth(atm_ce_symbol)
            pe_depth = tsl.get_market_depth(atm_pe_symbol)
            
            if ce_depth and pe_depth:
                ce_bids = float(ce_depth.get("total_buy_quantity", 0))
                pe_bids = float(pe_depth.get("total_buy_quantity", 0))
                now = time.time()
                self.history.append((now, ce_bids, pe_bids))
                self._cleanup_old_snapshots(now)
        except Exception as e:
            self.logger.exception(f"Error recording OrderFlow snapshot: {e}")

    def _cleanup_old_snapshots(self, current_time):
        # Keep snapshots slightly beyond the window so we have a valid baseline
        while self.history and current_time - self.history[0][0] > self.window_seconds + 30:
            self.history.popleft()

    def get_orderflow_sentiment(self):
        """
        Returns BULLISH, BEARISH, or NEUTRAL based on the % change of Limit Bids for ATM CE vs PE
        over the rolling 3-minute window.
        """
        if len(self.history) < 2:
            return "NEUTRAL"
            
        now = time.time()
        self._cleanup_old_snapshots(now)
        
        oldest = self.history[0]
        newest = self.history[-1]
        
        # Ensure we have at least half the window's worth of data before trusting the signal
        if newest[0] - oldest[0] < (self.window_seconds * 0.5):
            return "NEUTRAL"
            
        old_ce, old_pe = oldest[1], oldest[2]
        new_ce, new_pe = newest[1], newest[2]
        
        if old_ce == 0 or old_pe == 0:
            return "NEUTRAL"
            
        ce_change_pct = ((new_ce - old_ce) / old_ce) * 100.0
        pe_change_pct = ((new_pe - old_pe) / old_pe) * 100.0
        
        # If CE bids drop rapidly and PE bids surge rapidly -> Bearish (Anticipate drop)
        if ce_change_pct <= -self.threshold_pct and pe_change_pct >= self.threshold_pct and new_pe > (new_ce * 5):
            return "BEARISH"
            
        # If PE bids drop rapidly and CE bids surge rapidly -> Bullish (Anticipate rally)
        if pe_change_pct <= -self.threshold_pct and ce_change_pct >= self.threshold_pct:
            return "BULLISH"
            
        return "NEUTRAL"

# Global singleton to be accessed by Scanner and Strategy Core
_engine = None

def get_engine():
    global _engine
    if _engine is None:
        _engine = OrderFlowEngine()
    return _engine
