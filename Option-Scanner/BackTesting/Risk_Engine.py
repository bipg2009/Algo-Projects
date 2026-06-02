from dataclasses import dataclass
from typing import Optional, Dict

def detect_gap_risk(previous_close, today_open) -> bool:
    if previous_close is None or today_open is None:
        return False
    # Threshold for gap. Let's say >250 pts for Nifty
    threshold = 250
    gap = abs(today_open - previous_close)
    return gap > threshold

def allow_trade(df_1m, rsi_series, option_type, previous_close, today_open) -> bool:
    # Dummy implementation so execution doesn't crash
    return True

def explain_allow_trade_block(df_1m, rsi_series, option_type, previous_close, today_open) -> str:
    return "Trade Blocked by Risk Engine"

class ExecutionBlocker(Exception):
    pass

@dataclass
class RiskProfile:
    daily_loss_limit: float
    max_consecutive_losses: int
    max_drawdown_pct: float
    allow_overnight: bool

@dataclass
class ProposedTradeOffer:
    direction: str
    confidence_score: int
    target: float
    stop: float
    state_context: object  # UnifiedMarketState

@dataclass
class ApprovedExecution:
    direction: str
    base_qty: int
    strategy_tag: str
    stop_loss: float
    take_profit: float

class SEDARiskEngine:
    """
    SEDA Pipeline Layer 4: The Firewall
    Intercepts signals from StrategyEngine and validates against account-level and contextual risk.
    """
    def __init__(self, profile: RiskProfile):
        self.profile = profile
        self.current_daily_pnl = 0.0
        self.consecutive_losses = 0
        self.peak_portfolio_value = 100000.0  # Placeholder 1 Lac
        self.current_portfolio_value = 100000.0

    def get_drawdown_pct(self) -> float:
        if self.peak_portfolio_value == 0:
            return 0.0
        return ((self.peak_portfolio_value - self.current_portfolio_value) / self.peak_portfolio_value) * 100

    def evaluate_offer(self, offer: ProposedTradeOffer) -> Optional[ApprovedExecution]:
        """
        Validates the ProposedTradeOffer against Risk Firewalls.
        """
        try:
            # 1. Hard Account Limits
            if self.current_daily_pnl <= -self.profile.daily_loss_limit:
                raise ExecutionBlocker(f"Daily Stop Loss Hit. Current PnL: {self.current_daily_pnl}")
            
            if self.consecutive_losses >= self.profile.max_consecutive_losses:
                raise ExecutionBlocker(f"Max consecutive losses reached ({self.consecutive_losses}). Cooling down.")
                
            if self.get_drawdown_pct() > self.profile.max_drawdown_pct:
                raise ExecutionBlocker("Max Drawdown Curve threshold breached.")

            # 2. Contextual Confidence Gates
            # Reject if confidence is too low. The threshold tightens if we are down for the day.
            required_confidence = 65
            if self.current_daily_pnl < 0:
                required_confidence = 75  # Demand higher quality setups when red
                
            if offer.confidence_score < required_confidence:
                raise ExecutionBlocker(f"Confidence score {offer.confidence_score} below requirement {required_confidence}")

            # 3. Dynamic Position Sizing (Greeks/Volatility adjusted based on state)
            base_lot_multiplier = 1
            if offer.state_context.regime.market_regime == "PANIC_VOLATILITY":
                # Reduce size strictly during panic/high VIX
                base_lot_multiplier = 0.5 
            elif offer.state_context.session.phase == "STATE_TREND_ACCELERATION" and offer.confidence_score > 85:
                # Add size during high probability trend acceleration
                base_lot_multiplier = 1.5 
                
            # If the session strictly forbids aggression, we cap it. 
            base_lot_multiplier = min(base_lot_multiplier, offer.state_context.session.allowed_aggression)
            
            if base_lot_multiplier <= 0:
                raise ExecutionBlocker("Session or Regiment restricts sizing to 0 (Do Not Trade).")

            return ApprovedExecution(
                direction=offer.direction,
                base_qty=int(base_lot_multiplier * 50), # e.g. 50 = NIFTY lot
                strategy_tag=f"{offer.state_context.regime.market_regime}_FUSION_{offer.confidence_score}",
                stop_loss=offer.stop,
                take_profit=offer.target
            )
            
        except ExecutionBlocker as e:
            # Log to FIREWALL / RISK LOG QUEUE
            print(f"[FIREWALL BLOCKED] {str(e)}")
            return None

    def update_pnl(self, realized_pnl: float):
        """Called by OMS when a trade is closed"""
        self.current_daily_pnl += realized_pnl
        self.current_portfolio_value += realized_pnl
        
        if self.current_portfolio_value > self.peak_portfolio_value:
            self.peak_portfolio_value = self.current_portfolio_value
            
        if realized_pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0

