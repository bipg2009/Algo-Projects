# Institutional Multi-Timeframe State Engine (Design)

This document maps the proposed "Multi-timeframe Analytics" paradigm into concrete, implementable Python components for our evolving Event-Driven Architecture (EDA).

## 1. The Core Paradigm Shift
We are moving from **binary indicator crossover logic** (Retail) to **hierarchical probabilistic state machines** (Institutional). 

**Current (Weak):**
`if 1m_rsi > 60 and 1m_vwap_cross == True -> BUY`

**New (Robust):**
`if 5m_regime == TREND_EXPANSION and 3m_structure == VWAP_ACCEPTED and 1m_micro == MOMENTUM_IGNITION -> 85% Probability -> BUY`

## 2. The Functional Layers (The "How")

To achieve this, we insert a **State Detection Layer** between our math and our execution.

### Layer 1: Market Regime (5-Minute)
**Goal:** Identifies the macro environment. Controls *if* we trade, and *how aggressively* (sizing).
*   `TRENDING_UP`: Max size, trend-following strategies allowed.
*   `CHOPPY`: Mean reversion only, smaller size, tight targets.
*   `VOLATILITY_EXPANSION`: Breakout strategies allowed.

### Layer 2: Market Structure (3-Minute)
**Goal:** Filters out noise and validates pullbacks.
*   `PULLBACK_COMPRESSION`: Volume is drying up on a pullback (Bullish).
*   `VWAP_ACCEPTED`: Price has held above VWAP for 'N' consecutive candles.
*   `TREND_PERSISTING`: Structural Higher-Highs and Higher-Lows.

### Layer 3: Microstructure / Trigger (1-Minute)
**Goal:** The sniper trigger. We execute when the structure aligns with the regime.
*   `MOMENTUM_IGNITION`: High body-to-wick ratio, velocity increase.
*   `OI_ACCELERATION`: Spike in Open Interest velocity (not absolute value).
*   `LIQUIDITY_SWEEP`: Fast reversal after a low-break.

---

## 3. Concrete First Steps: What to build right now?

We cannot build the `State Fusion Engine` until we have clean data. Therefore, the very first step in this new direction is to lay the foundation for **Multi-Timeframe Data Pipelines**. 

### Step 1: Implement the `CandleAggregator`
Right now, the system fetches 1-minute data from Dhan. We need an internal component that reliably maintains rolling 1m, 3m, and 5m DataFrames in memory without making 3x the API calls.
*   **Action:** Build a `timeframe_manager.py` that takes the 1m tick/candle stream and resamples it into synchronized 3m and 5m frames.

### Step 2: Extract and Isolate the `IndicatorLayer`
Our indicators (`calculate_rsi`, `add_vwap`) are currently jammed into `Option_strategy_core.py`. 
*   **Action:** Move all math into a pure `indicators.py`. Compute these indicators across all three timeframes (1m, 3m, 5m) independently.

### Step 3: Define the `MarketState` Dataclasses
Once we have the indicators calculating on three timeframes, we create the structural objects that will hold the intelligent states.

```python
from dataclasses import dataclass

@dataclass
class MicroState_1M:
    momentum_velocity: str  # e.g., "ACCELERATING", "FLAT", "DECELERATING"
    candle_aggression: float # Body/Wick ratio
    oi_velocity: str

@dataclass
class StructureState_3M:
    vwap_state: str  # e.g., "ACCEPTED_ABOVE", "REJECTED_BELOW"
    pullback_quality: str # e.g., "LOW_VOL_COMPRESSION"

@dataclass
class RegimeState_5M:
    market_regime: str # e.g., "TRENDING", "CHOPPY"
    volatility: str # e.g., "EXPANDING", "CONTRACTING"

@dataclass
class UnifiedMarketState:
    micro: MicroState_1M
    structure: StructureState_3M
    regime: RegimeState_5M
    confidence_score: int # 0 to 100
```

### Step 4: Build State Classifiers
Write pure functions that convert the raw indicator DataFrames into the `MarketState` dataclasses. For example, a function `classify_5m_regime(df_5m)` that looks at ADX and Bollinger Band width to output `"CHOPPY"` or `"TRENDING"`.

## Summary of Execution Plan for this Evolution:
1. **Refactor Data Flow:** Replace direct Dhan API calls in logic with a central `CandleAggregator` (1m, 3m, 5m).
2. **Build Math Library:** Isolate `indicators.py` to calculate RSI/VWAP across the 3 timeframes.
3. **Build State Detection:** Create the Classifiers to translate numbers into "Regimes", "Structure", and "Micro-triggers".
4. **Build Fusion Engine:** Create a scoring model (Confidence 0-100%) based on timeframe alignment.
5. **Connect to OMS:** Only execute if `UnifiedMarketState.confidence_score > 80`.
