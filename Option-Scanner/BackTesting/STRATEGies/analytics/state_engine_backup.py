import datetime
from dataclasses import dataclass
import pandas as pd

@dataclass
class RegimeState:
    state: str
    confidence: float
    score: int
    timestamp: datetime.datetime

@dataclass
class StructureState:
    state: str
    confidence: float
    score: int
    timestamp: datetime.datetime

@dataclass
class ParticipationState:
    state: str
    confidence: float
    score: int
    timestamp: datetime.datetime

@dataclass
class DerivativeState:
    buildup_type: str
    pcr_bias: str
    oi_trend: str
    confidence: float
    score: int
    timestamp: datetime.datetime

@dataclass
class ExecutionState:
    state: str
    confidence: float
    score: int
    timestamp: datetime.datetime

@dataclass
class MarketContext:
    regime_10m: RegimeState
    structure_5m: StructureState
    confirmation_3m: ParticipationState
    derivatives: DerivativeState
    execution_1m: ExecutionState
    context_timestamp: datetime.datetime

class StateClassifier:
    @staticmethod
    def classify_10m_regime(df_10m: pd.DataFrame) -> RegimeState:
        now = datetime.datetime.now()
        if df_10m is None or df_10m.empty:
            return RegimeState("Unknown", 0.0, 0, now)
        
        last_row = df_10m.iloc[-1]
        state = "Chop"
        score = 0
        conf = 0.5
        
        close_price = last_row.get("close", 0)
        open_price = last_row.get("open", 0)
        
        ema9 = last_row.get("EMA9", close_price)
        ema20 = last_row.get("EMA20", open_price)
        adx = last_row.get("ADX", 25)
        
        if pd.isna(ema9): ema9 = close_price
        if pd.isna(ema20): ema20 = open_price
        if pd.isna(adx): adx = 25
        
        if ema9 > ema20:
            state = "Bull Trend"
            conf = 0.8
            if adx >= 35:
                score = 25
                state = "Strong Bull Trend"
            elif adx >= 25:
                score = 18
            elif adx >= 20:
                score = 10
            else:
                score = 5
        elif ema9 < ema20:
            state = "Bear Trend"
            conf = 0.8
            if adx >= 35:
                score = 25
                state = "Strong Bear Trend"
            elif adx >= 25:
                score = 18
            elif adx >= 20:
                score = 10
            else:
                score = 5
        
        return RegimeState(state, conf, score, now)

    @staticmethod
    def classify_5m_structure(df_5m: pd.DataFrame) -> StructureState:
        now = datetime.datetime.now()
        if df_5m is None or len(df_5m) < 5:
            return StructureState("Unknown", 0.0, 0, now)
        
        recent = df_5m.tail(5)
        highs = recent['high'].values
        lows = recent['low'].values
        
        hh_hl = 0
        lh_ll = 0
        for i in range(1, len(recent)):
            if highs[i] > highs[i-1]: hh_hl += 1
            if lows[i] > lows[i-1]: hh_hl += 1
            if highs[i] < highs[i-1]: lh_ll += 1
            if lows[i] < lows[i-1]: lh_ll += 1
            
        if hh_hl > lh_ll:
            if hh_hl >= 8:
                state, score = "Strong HH-HL", 25
            elif hh_hl >= 6:
                state, score = "Mild HH-HL", 20
            elif hh_hl >= 4:
                state, score = "Neutral HH-HL", 10
            else:
                state, score = "Weak HH-HL", 0
        else:
            if lh_ll >= 8:
                state, score = "Strong LL-LH", 25
            elif lh_ll >= 6:
                state, score = "Mild LL-LH", 20
            elif lh_ll >= 4:
                state, score = "Neutral LL-LH", 10
            else:
                state, score = "Weak LL-LH", 0
            
        return StructureState(state, 0.7, score, now)

    @staticmethod
    def classify_3m_confirmation(df_3m: pd.DataFrame) -> ParticipationState:
        now = datetime.datetime.now()
        if df_3m is None or df_3m.empty:
            return ParticipationState("Unknown", 0.0, 0, now)
            
        state = "Average Participation"
        score = 0
        if "VWAP" in df_3m.columns or "vwap" in df_3m.columns:
            vwap = df_3m.iloc[-1].get("VWAP", df_3m.iloc[-1].get("vwap", 0))
            close = df_3m.iloc[-1].get("close", 0)
            if pd.isna(vwap) or vwap == 0:
                return ParticipationState("Unknown", 0.0, 0, now)
                
            distance_pct = ((close - vwap) / vwap) * 100
            
            if distance_pct > 0.5:
                state, score = "Strong Institutional Buying", 20
            elif distance_pct > 0.2:
                state, score = "Mild Institutional Buying", 10
            elif distance_pct > 0.0:
                state, score = "Neutral Institutional Buying", 5
            elif distance_pct < -0.5:
                state, score = "Strong Institutional Selling", 20
            elif distance_pct < -0.2:
                state, score = "Mild Institutional Selling", 10
            elif distance_pct < -0.0:
                state, score = "Neutral Institutional Selling", 5
            else:
                state, score = "Average Participation", 0
                
        return ParticipationState(state, 0.75, score, now)

    @staticmethod
    def classify_derivatives_state(chain_data: dict) -> DerivativeState:
        now = datetime.datetime.now()
        pcr = float(chain_data.get("pcr", 1.0)) if isinstance(chain_data, dict) else 1.0
        bias = "Bullish" if pcr >= 1.15 else "Bearish" if pcr <= 0.85 else "Neutral"
        score = 10 if bias != "Neutral" else 0
        
        return DerivativeState(
            buildup_type="Unknown",
            pcr_bias=bias,
            oi_trend="Neutral",
            confidence=0.6,
            score=score,
            timestamp=now
        )

    @staticmethod
    def classify_1m_execution(df_1m: pd.DataFrame) -> ExecutionState:
        now = datetime.datetime.now()
        if df_1m is None or df_1m.empty:
            return ExecutionState("Unknown", 0.0, 0, now)
            
        state = "Dynamic"
        score = 0 # Calculated directionally in Option_strategy_core.py
        return ExecutionState(state, 0.5, score, now)

    @staticmethod
    def build_market_context(df_1m, df_3m, df_5m, df_10m, chain_data) -> MarketContext:
        now = datetime.datetime.now()
        return MarketContext(
            regime_10m=StateClassifier.classify_10m_regime(df_10m),
            structure_5m=StateClassifier.classify_5m_structure(df_5m),
            confirmation_3m=StateClassifier.classify_3m_confirmation(df_3m),
            derivatives=StateClassifier.classify_derivatives_state(chain_data),
            execution_1m=StateClassifier.classify_1m_execution(df_1m),
            context_timestamp=now
        )
