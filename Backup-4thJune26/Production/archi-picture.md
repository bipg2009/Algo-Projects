# MASTER ARCHITECTURE DIAGRAM (DO NOT DELETE)
> **Note to AI / Self**: This file is the primary visual "brain" for the user. Do not remove, delete, or overwrite it without explicit instruction. It acts as the anchor for the system's mental model.

## Staged Event-Driven Architecture (SEDA) with Institutional State Engine

```text
===================================================================================================
                                📡 1. INGESTION LAYER
===================================================================================================
                                (Raw Market Feeds)
     [ Dhan WebSocket ]                                      [ REST Pollers ]
   (Live Ltp/Vol/OI Ticks)                                  (OI Chains & PCR)
             │                                                      │
             └───────────────────────┐  ┌───────────────────────────┘
                                     ▼  ▼
===================================================================================================
                         ⏳ [ M A R K E T   D A T A   Q U E U E ]
===================================================================================================
                                     │
           ┌─────────────────────────┼────────────────────────────────────┐
           │                         ▼                                    │
           │      ================================================        │ (Fan-out Side Channels)
           │      | 🧮 INDICATOR ENGINE (Math & Aggregation)      |        ├──> 📊 [ METRICS QUEUE ]
           │      ================================================        │      ↳ Prometheus / Grafana
           │      | Syncs Data: 10m | 5m | 3m | 1m                 |        │
           │      | Vector Math: RSI, ADX, VWAP, EMA, BB           |        ├──> 🗄️ [ DATABASE QUEUE ]
           │      | Volatility:  ATR (Premium Expansion)           |        │      ↳ SQLite / TimescaleDB
           │      ================================================        │
           │                         │                                    ├──> 📗 [ EXCEL QUEUE ]
           │                         ▼                                    │      ↳ Async xlwings buffer
           │      ================================================        │
           │      | 🚦 S I G N A L   Q U E U E                   |        ├──> 🔔 [ ALERT QUEUE ]
           │      ================================================        │      ↳ Discord / Telegram
           │                         │                                    │
           │                         ▼                                    ├──> 📝 [ LOG QUEUE ]
           │      ================================================        │      ↳ Console JSON Logs
           │      | 🧠 STRATEGY ENGINE (Institutional States)    |        │
           │      ================================================        │
           │      | ⏱️ SESSION TIME-OF-DAY ENGINE                 |        │
           │      |   ↳ e.g., 9:15(Gap) -> 12:40(Lunch Noise)    |        │
           │      |   ↳ Emits Strictness & Aggression Multiplier |        │
           │      |----------------------------------------------|        │
           │      | THE 4-TIER HIERARCHY:                        |        │
           │      | [20%] 10m: Soft Regime Filter                |        │
           │      | [40%]  5m: Structural Intelligence           |        │
           │      | [25%]  3m: Confirmation Intelligence         |        │
           │      | [15%]  1m: Execution Intelligence            |        │
           │      |----------------------------------------------|        │
           │      | 🧬 FUSION -> Final Probability Score (0-100) |        │
           │      | 📉 CONFIDENCE DECAY -> Penalizes stale       |        │
           │      |                     entries over time.       |        │
           │      ================================================        │
           │                         │                                    │
           │                         ▼                                    │
           │      ================================================        │
           │      | 🛡️ RISK ENGINE (The Firewall)                 |        │
           │      ================================================        │
           │      | Checks: Max Drawdown, Choppiness limits,     |        │
           │      | consecutive losses, and positional Greeks.   |        │
           │      ================================================        │
           │                         │                                    │
           │                         ▼                                    │
           │      ================================================        │
           │      | 🚀 E X E C U T I O N   Q U E U E             |        │
           │      ================================================        │
           │                         │                                    │
           │                         ▼                                    │
           │      ================================================        │
           │      | 🏦 OMS GATEWAY (Order Management)            |        │
           │      ================================================        │
           │      | Calculates sizes, handles entry/exits,      |        │
           │      | formats payloads for Broker API.             |        │
           │      ================================================        │
           │                         │                                    │
           └─────────────────────────┼────────────────────────────────────┘
                                     ▼
===================================================================================================
                                🎯 6. BROKER API
===================================================================================================
                                (Dhan Tradehull)
```

## Why it looks like this:
1. **The Straight Path (Center)**: This is your low-latency execution spine. From signal to broker, nothing blocks it.
2. **The Fan-Out (Right)**: Writing to Excel and sending Discord messages are physically segmented. Excel can freeze entirely, and the central spine will keep trading without knowing or caring.
3. **The State Brain (Middle)**: Math happens first (Indicator Engine). Context is injected next (Session Time-of-Day). Then the 4 timeframes cast their "votes" weighted beautifully (40% to the 5m structure!).

This is your master map representing our exact Python structure.
