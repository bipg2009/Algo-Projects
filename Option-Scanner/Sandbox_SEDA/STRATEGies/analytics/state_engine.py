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
        
        ema9 = last_row.get("ema_9", last_row.get("EMA9", 0))
        ema20 = last_row.get("ema_21", last_row.get("EMA20", 0))
        adx = last_row.get("ADX", 20)
        
        if ema9 > ema20 and adx > 22:
            state = "Strong Bull Trend"
            score = 15
            conf = 0.8
        elif ema9 < ema20 and adx > 22:
            state = "Strong Bear Trend"
            score = 15
            conf = 0.8
        
        return RegimeState(state, conf, score, now)

    @staticmethod
    def classify_5m_structure(df_5m: pd.DataFrame) -> StructureState:
        now = datetime.datetime.now()
        if df_5m is None or len(df_5m) < 2:
            return StructureState("Unknown", 0.0, 0, now)
        
        state = "Consolidating"
        score = 0
        c1, c2 = df_5m.iloc[-1].get("close", 0), df_5m.iloc[-2].get("close", 0)
        if c1 > c2:
            state = "HH-HL Expansion"
            score = 15
        elif c1 < c2:
            state = "LL-LH Expansion"
            score = 15
            
        return StructureState(state, 0.7, score, now)

    @staticmethod
    def classify_3m_confirmation(df_3m: pd.DataFrame) -> ParticipationState:
        now = datetime.datetime.now()
        if df_3m is None or df_3m.empty:
            return ParticipationState("Unknown", 0.0, 0, now)
            
        state = "Average Participation"
        score = 0
        if "vwap" in df_3m.columns or "VWAP" in df_3m.columns:
            vwap = df_3m.iloc[-1].get("vwap", df_3m.iloc[-1].get("VWAP", 0))
            close = df_3m.iloc[-1].get("close", 0)
            if close > vwap:
                state = "Institutional Buying"
                score = 15
            else:
                state = "Institutional Selling"
                score = 15
                
        return ParticipationState(state, 0.75, score, now)

    @staticmethod
    def classify_derivatives_state(chain_data: dict) -> DerivativeState:
        now = datetime.datetime.now()
        pcr = float(chain_data.get("pcr", 1.0)) if isinstance(chain_data, dict) else 1.0
        bias = "Bullish" if pcr > 1.15 else "Bearish" if pcr < 0.85 else "Neutral"
        score = 5 if bias != "Neutral" else 0
        
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
            
        state = "Wait"
        score = 0
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
