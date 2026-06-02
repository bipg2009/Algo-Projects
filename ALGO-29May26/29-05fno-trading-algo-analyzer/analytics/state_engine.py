from dataclasses import dataclass
from datetime import datetime, time
import pandas as pd

@dataclass
class SessionState:
    phase: str # e.g., "STATE_OPEN_VOLATILITY"
    description: str
    allowed_aggression: float # 0.0 to 1.0 (strictness multiplier)

@dataclass
class ExecutionState_1M:
    momentum_velocity: str  # e.g., "ACCELERATING", "FLAT", "DECELERATING"
    candle_aggression: float # Body/Wick ratio (0.0 to 1.0)
    oi_velocity: str # e.g. "SPIKING", "DROPPING", "FLAT"

@dataclass
class ConfirmationState_3M:
    vwap_state: str  # e.g., "ACCEPTED_ABOVE", "REJECTED_BELOW", "CHOPPING"
    pullback_quality: str # e.g., "LOW_VOL_COMPRESSION", "HIGH_VOL_DUMP"

@dataclass
class StructureState_5M:
    trend_structure: str # e.g., "HIGHER_HIGHS", "LOWER_LOWS", "RANGE"
    volatility: str # e.g., "EXPANDING", "CONTRACTING"

@dataclass
class RegimeState_10M:
    market_regime: str # e.g., "LOW_VOL_COMPRESSION", "HIGH_VOL_EXPANSION", "PANIC_VOLATILITY", "EXPIRY_CHAOS", "TREND_DAY", "MEAN_REVERSION"
    macro_volatility: str # e.g., "HIGH_ATR", "NORMAL_ATR"

@dataclass
class UnifiedMarketState:
    execution: ExecutionState_1M
    confirmation: ConfirmationState_3M
    structure: StructureState_5M
    regime: RegimeState_10M
    session: SessionState
    confidence_score: int # 0 to 100 
    timestamp: str


class SessionStateEngine:
    """
    Time-of-day contextual intelligence.
    Identifies market phases for Indian Index Options to determine allowed aggression and entry strictness.
    """
    @staticmethod
    def get_current_session(dt: datetime) -> SessionState:
        t = dt.time()
        
        if time(9, 15) <= t < time(9, 55):
            return SessionState(phase="STATE_OPEN_VOLATILITY", description="Gap chaos", allowed_aggression=0.8)
        elif time(9, 55) <= t < time(11, 40):
            return SessionState(phase="STATE_TREND_SEEKING", description="Trend development", allowed_aggression=1.0)
        elif time(11, 40) <= t < time(12, 25):
            return SessionState(phase="STATE_RANGING_LUNCH", description="Lunch Period Break", allowed_aggression=0.3)
        elif time(12, 25) <= t < time(13, 25):
            return SessionState(phase="STATE_RANGING_EXT", description="Extended Lunch", allowed_aggression=0.3)
        elif time(13, 25) <= t < time(14, 15):
            return SessionState(phase="STATE_POST_LUNCH", description="Post Lunch", allowed_aggression=0.8)
        elif time(14, 15) <= t <= time(15, 30):
            return SessionState(phase="STATE_TREND_ACCELERATION", description="Trend acceleration", allowed_aggression=1.0)
        else:
            # Outside normal market hours
            return SessionState(phase="STATE_CLOSED", description="Market Closed", allowed_aggression=0.0)


class StateClassifier:
    """
    Evaluates pure indicator dataframes to classify contextual market states.
    Replaces binary retail thinking ("if RSI > 60: Buy") with State Generation.
    """
    
    @staticmethod
    def classify_10m_regime(df_10m: pd.DataFrame) -> RegimeState_10M:
        """Step 1 (10m): Identifies the Macro Environment (Regime Filter)"""
        if df_10m.empty or len(df_10m) < 2:
            return RegimeState_10M("UNKNOWN", "UNKNOWN")
        
        last_row = df_10m.iloc[-1]
        prev_row = df_10m.iloc[-2]
        
        # Regiment Classification Logic (ADX + EMA setup)
        regime = "MEAN_REVERSION"
        if 'adx' in last_row and not pd.isna(last_row['adx']):
            if last_row['adx'] > 25: # Strong trend strength
                regime = "TREND_DAY"
                    
        # Volatility Regime Overrides
        if 'bb_upper' in last_row and not pd.isna(last_row['bb_upper']):
            bb_width_current = last_row['bb_upper'] - last_row['bb_lower']
            bb_width_prev = prev_row['bb_upper'] - prev_row['bb_lower']
            
            # If BB width is expanding aggressively, it overrides as a breakout/expansion regime
            if bb_width_current > bb_width_prev * 1.10: 
                regime = "HIGH_VOL_EXPANSION"
            # If BB width is incredibly tight and ATR is dropping, it's contracting
            elif bb_width_current < bb_width_prev * 0.90:
                regime = "LOW_VOL_COMPRESSION"
                
        # Contextual Overrides (Placeholder logic for future hooks)
        # if is_expiry_day and time > 14:00: regime = "EXPIRY_CHAOS"
        # if vix_spike > 15%: regime = "PANIC_VOLATILITY"
                    
        macro_vol = "UNKNOWN"
        # Could link to VIX or ATR here
        if 'atr' in last_row and not pd.isna(last_row['atr']):
            # Simple placeholder logic for macro vol
            macro_vol = "HIGH_ATR" if last_row['atr'] > last_row['close'] * 0.005 else "NORMAL_ATR"
        
        return RegimeState_10M(market_regime=regime, macro_volatility=macro_vol)

    @staticmethod
    def classify_5m_structure(df_5m: pd.DataFrame) -> StructureState_5M:
        """Step 2 (5m): Evaluates Market Structure"""
        if df_5m.empty or len(df_5m) < 2:
            return StructureState_5M("UNKNOWN", "UNKNOWN")
        
        last_row = df_5m.iloc[-1]
        prev_row = df_5m.iloc[-2]
        
        trend = "RANGE"
        if 'ema_9' in last_row and 'ema_21' in last_row:
            if last_row['ema_9'] > last_row['ema_21']:
                trend = "HIGHER_HIGHS"
            elif last_row['ema_9'] < last_row['ema_21']:
                trend = "LOWER_LOWS"
        
        # Volatility Pipeline Logic (Bollinger Bands expansion checkout)
        volatility = "UNKNOWN"
        if 'bb_upper' in last_row and not pd.isna(last_row['bb_upper']):
            bb_width_current = last_row['bb_upper'] - last_row['bb_lower']
            bb_width_prev = prev_row['bb_upper'] - prev_row['bb_lower']
            
            if bb_width_current > bb_width_prev * 1.05:  # 5% outward expansion detected
                volatility = "EXPANDING"
            elif bb_width_current < bb_width_prev * 0.95:
                volatility = "CONTRACTING"
            else:
                volatility = "NEUTRAL"
                
        return StructureState_5M(trend_structure=trend, volatility=volatility)
        
    @staticmethod
    def classify_3m_confirmation(df_3m: pd.DataFrame) -> ConfirmationState_3M:
        """Step 3 (3m): Confirmation Layer (Filters noise and validates pullbacks & structure)"""
        if df_3m.empty or len(df_3m) < 3:
            return ConfirmationState_3M("UNKNOWN", "UNKNOWN")
            
        last_row = df_3m.iloc[-1]
        
        # VWAP Acceptance logic (Has it held above VWAP for 3 candles?)
        vwap_state = "UNKNOWN"
        if 'vwap' in last_row:
            recent_closes = df_3m['close'].tail(3)
            recent_vwaps = df_3m['vwap'].tail(3)
            
            if all(recent_closes > recent_vwaps):
                vwap_state = "ACCEPTED_ABOVE"
            elif all(recent_closes < recent_vwaps):
                vwap_state = "REJECTED_BELOW"
            else:
                vwap_state = "CHOPPING_AROUND"
                
        # Pullback quality formulation
        pullback_quality = "UNKNOWN"
        # Can scale this later to check volume during red candles
        
        return ConfirmationState_3M(vwap_state=vwap_state, pullback_quality=pullback_quality)

    @staticmethod
    def classify_1m_execution(df_1m: pd.DataFrame) -> ExecutionState_1M:
        """Step 4 (1m): The Sniper Execution Layer."""
        if df_1m.empty or len(df_1m) < 2:
            return ExecutionState_1M("UNKNOWN", 0.0, "UNKNOWN")
            
        last_row = df_1m.iloc[-1]
        
        # Momentum Velocity (Volume Expansion)
        momentum_velocity = "FLAT"
        if 'vol_acceleration' in last_row and not pd.isna(last_row['vol_acceleration']):
            if last_row['vol_acceleration'] > 0.5: # 50% jump in volume burst
                momentum_velocity = "ACCELERATING"
            elif last_row['vol_acceleration'] < -0.5:
                momentum_velocity = "DECELERATING"
                
        # Candle aggression (Ratio of body size vs full wick height)
        candle_range = last_row['high'] - last_row['low']
        if candle_range > 0:
            body = abs(last_row['close'] - last_row['open'])
            aggression = round(body / candle_range, 2)
        else:
            aggression = 0.0
            
        return ExecutionState_1M(
            momentum_velocity=momentum_velocity, 
            candle_aggression=aggression, 
            oi_velocity="UNKNOWN"  # Placeholder until linked
        )
        
    @staticmethod
    def fuse_market_state(execution: ExecutionState_1M, confirmation: ConfirmationState_3M, structure: StructureState_5M, regime: RegimeState_10M, session: SessionState, timestamp: str, signal_age_candles: int = 0) -> UnifiedMarketState:
        """
        The fusion engine!
        Scores the alignment of timeframes AND incorporates the current Time-of-Day Session constraints.
        Additionally implements Confidence Decay to prevent stale entries.
        """
        score = 0
        
        # ---- Example Institutional Setup Scoring (Bullish Continuation Setup) ----
        
        # 1. 10m Soft Regime Filter (Max 20 points)
        if regime.market_regime in ["TREND_DAY", "HIGH_VOL_EXPANSION"]:
            score += 20
        elif regime.market_regime in ["MEAN_REVERSION", "LOW_VOL_COMPRESSION"]:
            score -= 10 # Deduct points, danger / scalping risk
        elif regime.market_regime == "EXPIRY_CHAOS":
            score -= 15 # Highest danger
        elif regime.market_regime == "PANIC_VOLATILITY":
            score -= 5
            
        # 2. 5m Structural Intelligence (Max 40 points)
        if structure.trend_structure == "HIGHER_HIGHS":
            score += 40
            
        # 3. 3m Confirmation Intelligence (Max 25 points)
        if confirmation.vwap_state == "ACCEPTED_ABOVE":
            score += 25
            
        # 4. 1m Execution Intelligence (Are buyers aggressive NOW?) (Max 15 points)
        if execution.momentum_velocity == "ACCELERATING" and execution.candle_aggression > 0.6:
            score += 15
            
        # ----- Contextual Penalties/Adjustments -----
        if structure.volatility == "CONTRACTING":
            score -= 10 # Contracting volatility means trapped breakdown risk
            
        # Confidence Decay: Prevent Stale Entries
        if signal_age_candles > 0:
            decay_penalty = signal_age_candles * 15 # e.g., 3 candles = 45 point penalty
            score -= decay_penalty
            
        # Adjust for Session Time-of-day
        if session.phase in ["STATE_RANGING_LUNCH", "STATE_RANGING_EXT"]:
            score -= 20 # Heavy penalty for trading during lunchtime noise
            
        if session.phase == "STATE_TREND_ACCELERATION" and score >= 60:
            score += 10 # Provide momentum bump to good setups post 2:15pm
            
        # Apply the Session Allowed Aggression multiplier (scales size/confidence implicitly)
        score = int(score * session.allowed_aggression)
            
        # Clamp bounds
        confidence = int(max(0, min(100, score)))
        
        return UnifiedMarketState(
            execution=execution,
            confirmation=confirmation,
            structure=structure,
            regime=regime,
            session=session,
            confidence_score=confidence,
            timestamp=timestamp
        )
