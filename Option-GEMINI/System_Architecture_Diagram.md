# Comprehensive System Architecture: Event-Driven Multi-Timeframe Engine

This document provides a highly granular diagram and architectural breakdown of the evolved trading system, integrating the asynchronous Event-Driven Architecture (EDA) with the 4-Tier Institutional Multi-Timeframe State Engine.

## 1. End-To-End Granular Architecture Diagram

```text
====================================================================================================================
                        [ 1. RAW DATA INGESTION & BROKER CONNECTIVITY ]
====================================================================================================================
      ▲                                                    ▲
      │ (Periodic REST Polls)                              │ (Persistent Stream)
┌─────┴────────────────┐                         ┌─────────┴─────────────────────┐
│ HistoricalChainPoller│                         │      DhanWebsocketClient      │
│ (Option Chains/OI)   │                         │  (High-Freq Ltp/Vol Ticks)    │
└─────────┬────────────┘                         └─────────┬─────────────────────┘
          │ [Produces ChainUpdateEvent]                    │ [Produces TickEvent]
          ▼                                                ▼
====================================================================================================================
                        [ 2. CORE EVENT BUS & ROUTER (ASYNCIO PRIORITY QUEUE) ]
====================================================================================================================
          └─────────────────────────────┬──────────────────┘
                                        ▼      
                              [ asyncio.PriorityQueue ]
                                        │
====================================================================================================================
                        [ 3. DATA AGGREGATION & INDICATOR MATH (SIDE-EFFECT FREE) ]
====================================================================================================================
                                        ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────┐
│  TimeframeManager (CandleAggregator)                                                           │
│  Synchronizes high-frequency ticks into strict time intervals:                                 │
│  ├──> 1m Dataset (Microstructure)                                                              │
│  ├──> 3m Dataset (Confirmation)                                                                │
│  ├──> 5m Dataset (Structure)                                                                   │
│  └──> 10m Dataset (Regime)                                                                     │
└───────────────────────────────────────┬────────────────────────────────────────────────────────┘
                                        ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────┐
│  IndicatorEngine (NumPy/Pandas Vectorized Math)                                                │
│  Computes technicals (RSI, ADX, VWAP, EMA, BB) strictly across 1m, 3m, 5m, 10m datasets.       │
│  Acts as the ONLY source of mathematical truth. No trading logic here.                         │
└───────────────────────────────────────┬────────────────────────────────────────────────────────┘
                                        ▼ [Produces IndicatorUpdateEvent]
====================================================================================================================
                        [ 4. INSTITUTIONAL 4-TIER STATE ENGINE (THE BRAIN) ]
====================================================================================================================
                                        ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────┐
│  StateClassifier                                                                               │
│                                                                                                │
│  [ Tier 1: 10m Soft Regime Filter ]      (Influence: 20%)                                      │
│   ↳ Evaluates: Trend Regimes, Macro Volatility (e.g., ADX + EMAs)                              │
│   ↳ State: 'TRENDING_UP', 'CHOPPY'                                                             │
│                                                                                                │
│  [ Tier 2: 5m Structural Intelligence ]  (Influence: 40%)                                      │
│   ↳ Evaluates: Higher-Highs, Lower-Lows, Breakouts, BB Expansion                               │
│   ↳ State: 'HIGHER_HIGHS', 'LOWER_LOWS'                                                        │
│                                                                                                │
│  [ Tier 3: 3m Confirmation Intel ]       (Influence: 25%)                                      │
│   ↳ Evaluates: VWAP Acceptance, Low Volatility Squeeze/Pullback Quality                        │
│   ↳ State: 'ACCEPTED_ABOVE', 'LOW_VOL_COMPRESSION'                                             │
│                                                                                                │
│  [ Tier 4: 1m Execution Intel ]          (Influence: 15%)                                      │
│   ↳ Evaluates: Momentum Acceleration, Candle Body/Wick Aggression, OI Variance                 │
│   ↳ State: 'ACCELERATING_MOMENTUM', 'HIGH_AGGRESSION'                                          │
└───────────────────────────────────────┬────────────────────────────────────────────────────────┘
                                        ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────┐
│  FusionEngine                                                                                  │
│  Probabilistically fuses the 4 states into a UnifiedMarketState:                               │
│  ↳ Final Confidence Score = % sum of aligned timeframes.                                       │
└───────────────────────────────────────┬────────────────────────────────────────────────────────┘
                                        ▼ [Produces SignalEvent IF Score > Threshold]
====================================================================================================================
                        [ 5. RISK, EXECUTION & OUTPUT (THE ACTION) ]
====================================================================================================================
                                        ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────┐
│  RiskGuard (Gatekeeper)                                                                        │
│  Intercepts SignalEvent -> Validates Gap downs, Consecutive Losses, Drawdowns, Theta Decay     │
└────────────────┬──────────────────────┬──────────────────────┬─────────────────────────────────┘
                 │                      │                      │
     [Produces OrderEvent]     [Produces LogEvent/UI]  [Produces LogEvent/UI]
                 ▼                      ▼                      ▼
┌───────────────────────────┐ ┌─────────────────────┐ ┌──────────────────────┐
│  OrderManagementSystem    │ │  AsyncExcelWriter   │ │ AlertNotificationHub │
│  (execution/oms.py)       │ │  (presentation)     │ │ (Discord/Telegram)   │
│---------------------------│ │---------------------│ │----------------------│
│  Validates lot sizing     │ │  Uses xlwings       │ │  Dispatches async    │
│  Tracks order states      │ │  Batched flushes    │ │  Webhooks & Audio    │
│  Calls Dhan_Tradehull API │ │  150ms-250ms delay  │ │  Non-blocking        │
└───────────────────────────┘ └─────────────────────┘ └──────────────────────┘
```

## 2. Granular Data Flow Sequence

1. **Ingestion Loop (Async):** `DhanWebsocketClient` receives raw JSON from Dhan, unpacks it into an immutable `TickEvent`, and pushes it to the generic `core event bus` (a non-blocking `asyncio.PriorityQueue`).
2. **Buffering & Aggregation:** The `TimeframeManager` consumes ticks and seamlessly maintains distinct datasets for `1m`, `3m`, `5m`, and `10m` granularities, guaranteeing strict chronological alignment across windows.
3. **Indicator Calculation (Pure Math):** The state-free `IndicatorEngine` is triggered. It rapidly processes the new candles through vectorized NumPy/Pandas functions for RSI, VWAP, EMA, ADX, outputs an `IndicatorUpdateEvent`, and hands this cleanly to the Strategy core.
4. **State Classification (Contextual Intelligence):**
   * The `10m Layer` (20%) dictates the overarching macro regime safety mask.
   * The `5m Layer` (40%) provides the structural trend alpha vector.
   * The `3m Layer` (25%) confirms if the recent momentum implies structural acceptance.
   * The `1m Layer` (15%) pulls the trigger only on verified aggressive price action and volume expansion.
5. **Probabilistic Fusion:** `FusionEngine` assesses the 4 concurrent states using the custom weights. The outcome is a `UnifiedMarketState` housing a numerical confidence score rather than a binary YES/NO limit.
6. **Risk Adjustment:** If a setup scores `>80-85%`, the `FusionEngine` emits a `SignalEvent`. `RiskGuard` acts as the firewall, cross-referencing max drawdown and dynamic factors.
7. **Bifurcated Output (Eliminating Lag):** Once `RiskGuard` approves:
   * **Execution Thread:** Immediately fires the `OrderEvent` to the `OrderManagementSystem` (OMS).
   * **Presentation Thread:** Independently, the `AsyncExcelWriter` and `AlertNotificationHub` fetch the updated datasets to log asynchronously. The trading engine **never waits** on Excel COM object writes or network-based API alerts.

## 3. Scale & Modularity Checklist

* **Decoupled:** Indicators, Math, State Logic, Risk, Execution, UI all separated into modular, functional boxes.
* **Deterministic:** Calculations always run symmetrically against historic backtests or live ticks, meaning the backtester mimics the live flow identically.
* **Non-Blocking Infrastructure:** Excel hangs or Discord webhook limits have 0% chance of delaying the execution pipeline. 
* **Granular Upgradability:** Changing the `10m Filter` to a `15m Institutional Flow Filter` only requires updating the TimeframeManager resampling dictionary and tweaking the Regime logic without affecting the downstream OMS.
