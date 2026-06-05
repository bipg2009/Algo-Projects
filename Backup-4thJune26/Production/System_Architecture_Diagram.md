# Comprehensive System Architecture: Staged Event-Driven Pipeline (SEDA)
This document outlines the advanced, queue-centric, multi-timeframe trading architecture.

## 1. The Queue-Driven Pipeline (Primary Flow & Side Channels)

This architecture adopts a **Staged Event-Driven Architecture (SEDA)**. Instead of a single event bus, data moves through isolated stages separated by dedicated operational queues. This allows pub/sub fan-outs to parallel side channels without ever touching the primary execution latency.

```text
==========================================================================================
                                [ I N G E S T I O N ]
==========================================================================================
               (WebSocket Streams, Historical Sync, REST Pollers)
                                        │
                                        ▼
==========================================================================================
                            [ M A R K E T   D A T A   Q U E U E ]
==========================================================================================
                                        │
     ┌──────────────────────────────────┼──────────────────────────────────┐
     │                                  │                                  │ (Fan-out)
     │                                  ▼                                  ├─> [ EXCEL QUEUE ] 
     │       =======================================================       │   ↳ AsyncExcelWriter
     │       [ I N D I C A T O R   E N G I N E (Math & Aggregation)]       │
     │       =======================================================       ├─> [ DATABASE QUEUE ]
     │       (10m, 5m, 3m, 1m data syncing & vectorized indicators)        │   ↳ SQLite/TimescaleDB
     │       (RSI, ADX, VWAP, EMA, BB, ATR explicit for premium exp)       │
     │                                  │                                  │
     │                                  ▼                                  ├─> [ METRICS QUEUE ]
     │       =======================================================       │   ↳ Prometheus/Grafana
     │                          [ S I G N A L   Q U E U E ]                │
     │       =======================================================       │
     │                                  │                                  │
     │                                  ▼                                  │
     │       =======================================================       │
     │       [ S T R A T E G Y   E N G I N E (State Fusion & Context)  ]   │
     │       =======================================================       │
     │       (SessionStateEngine -> Time-of-Day Strictness constraints)    │
     │       (10m Regime -> 5m Structure -> 3m Confirm -> 1m Exec)         │
     │                                  │                                  │
     │                                  ▼                                  │
     │       =======================================================       │
     │       [ R I S K   E N G I N E (Firewall & Filter)           ]       │
     │       =======================================================       │
     │       (Max Drawdown, Gap Filters, Chop Limits)                      │
     │                                  │                                  │
     │                                  ▼                                  │ (Fan-out)
     │       =======================================================       ├─> [ ALERT QUEUE ]
     │                    [ E X E C U T I O N   Q U E U E ]                │   ↳ Discord/Telegram/Audio
     │       =======================================================       │
     │                                  │                                  ├─> [ LOG QUEUE ]
     │                                  ▼                                  │   ↳ Console/System Logs
     │       =======================================================       │
     │                          [ O M S   G A T E W A Y ]                  │
     │       =======================================================       │
     │       (Lot Sizing, Entry/Exit Ledgers, Order Formatting)            │
     │                                  │                                  │
     └──────────────────────────────────┼──────────────────────────────────┘
                                        ▼
==========================================================================================
                                [ B R O K E R   A P I ]
==========================================================================================
                                  (Dhan Tradehull)
```

## 2. Why this Pipeline is Elite

### 1. Dedicated Queues = Perfect Backpressure
Instead of one massive `asyncio.PriorityQueue`, having a `MARKET DATA QUEUE`, `SIGNAL QUEUE`, and `EXECUTION QUEUE` isolates workload. If the Indicator Engine takes a microsecond longer during a massive volatility spike, the `MARKET DATA QUEUE` absorbs the shock safely without crashing the WebSocket ingestion process.

### 2. Pub-Sub / Fan-Out (The "Parallel Side Channels")
This is the ultimate bottleneck killer. When data hits the `MARKET DATA QUEUE` or the `EXECUTION QUEUE`, the system "fans out" copies of the payload to the parallel channels:
*   **LOG QUEUE:** Pure JSON system lifecycle logs.
*   **ALERT QUEUE:** Sound bytes and Discord websockets.
*   **EXCEL QUEUE:** Batched `.xlsx` updates.
*   **DATABASE QUEUE:** TimescaleDB / SQLite order history and tick history.
*   **METRICS QUEUE:** Real-time system health (latency, slippage, queue depth).

*Crucially: If the EXCEL QUEUE gets backed up because Microsoft Excel freezes, the MAIN PIPELINE (Strategy -> Risk -> Execution) does not care. It keeps firing strictly down the center.*

## 3. Data Payloads Between Stages

**Stage 1: INGESTION → MARKET DATA QUEUE**
* Payload: `TickEvent(symbol, ltp, vol, oi, timestamp)`

**Stage 2: INDICATOR ENGINE → SIGNAL QUEUE**
* Payload: `IndicatorStateEvent({10m_df, 5m_df, 3m_df, 1m_df})` (Cleaned, calculated data arrays)

**Stage 3: STRATEGY ENGINE → RISK ENGINE**
* Payload: `ProposedTradeOffer(direction, confidence_score, target, stop)`

**Stage 4: RISK ENGINE → EXECUTION QUEUE**
* Payload: `ApprovedExecution(ticker, direction, base_qty, strategy_tag)`

**Stage 5: EXECUTION QUEUE → OMS GATEWAY → BROKER**
* Payload: `BrokerOrderRequest(api_spec_payload)`
