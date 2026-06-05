# Event-Driven Algorithmic Trading Architecture (EDA)
**Complete Specification Blueprint**

## Overview
This document provides a production-grade blueprint for transitioning the platform from a tightly coupled architecture into a highly concurrent, non-blocking Event-Driven Architecture (EDA). By isolating execution pathways from blocking I/O operations (such as Excel logging and network alerts), this architecture guarantees consistent execution latency under volatile market conditions.

---

## 1. Unified Architecture Pipeline

**[ Dhan Market Socket ]** -> Raw JSON Packet Stream
↓
**`ingestion/websocket_client.py` (Layer 1)** -> Converts raw bytes into Immutable Typed Event Dataclasses
↓
**`asyncio.PriorityQueue` (Layer 2 - Core Event Bus)** -> Message Router
↓
*(Routes Based on Priority to Consumers)*

### Core Execution Modules:
*   **`analytics/indicators.py` (Layer 3)** -> IndicatorEngine (Computes NumPy metrics)
*   **`strategy/alpha_generator.py` (Layer 3)** -> StrategyCore (Matches triggers)
*   **`strategy/risk_manager.py` (Layer 3)** -> RiskGuard (Final gatekeeper)
*   **`execution/oms.py` (Layer 4)** -> OrderManagementSystem (Live Orders via Dhan API)

### Isolated Output Modules (The Bottleneck Killers):
*   **`presentation/excel_worker.py` (Layer 5)** -> AsyncExcelWriter (Batches write commands to `.xlsx`)
*   **`presentation/alert_dispatcher.py` (Layer 5)** -> AlertNotificationHub (Telegram, Discord, Audio)

---

## 2. Immutable Event Dataclass Model & Priority Table

The platform communicates exclusively using thread-safe, frozen dataclasses.

| Event Class Name | Priority | Payload Attributes |
| :--- | :--- | :--- |
| `OrderEvent` | 1 (Highest) | `order_id`, `symbol`, `qty`, `side`, `order_type`, `price` |
| `SignalEvent` | 2 | `strategy_id`, `symbol`, `direction`, `underlying_price`, `timestamp` |
| `TickEvent` | 3 | `symbol`, `ltp`, `volume`, `oi`, `timestamp` |
| `ChainUpdateEvent`| 4 | `underlying`, `expiry`, `strike_matrix_dict`, `timestamp` |
| `LogEvent` | 5 (Lowest) | `message`, `level`, `origin_module` |

---

## 3. Layer Breakdown

### Layer 1: Data Ingestion (Producers)
*Zero business logic. Handles networking and payload standardization.*
*   **`DhanWebsocketClient`**: TCP connections, auto-reconnect, pushes `TickEvent`.
*   **`HistoricalChainPoller`**: Isolated async interval worker polls REST for Option Chains, OI, PCR. Pushes `ChainUpdateEvent`.

### Layer 2: Core Event Bus
*   `asyncio.PriorityQueue()` guarantees non-blocking, priority-aware, deterministic execution.

### Layer 3: Analytics & Strategy Core
*Pure mathematics and logic. No file or API I/O operations.*
*   **`IndicatorEngine`**: Rolling NumPy circular buffers. Computes RSI, VWAP, EMA, ADX quickly. Consumes `TickEvent`, produces `IndicatorUpdateEvent`.
*   **`StrategyCore`**: Evaluates active setups (RSI trend mismatches, volume spikes, ATM proximity). Produces `SignalEvent`.
*   **`RiskGuard`**: Validates instantaneous risk (Gap cooldowns, drawdown protection, position exposure). Produces `OrderEvent`.

### Layer 4: Execution Engine
*Acts as the interface for account capital management.*
*   **`OrderManagementSystem (OMS)`**: Interfaces directly with `Dhan_Tradehull.py`. Verifies lot sizing, maintains audit trails, handles retries.

### Layer 5: Presentation & I/O Isolation Boundaries
*Removes main sources of system latency (Excel COM objects).*
*   **`AsyncExcelWriter`**: Runs in dedicated thread/subprocess. Buffers spreadsheet writes with a flush interval of 150ms-250ms.
*   **`AlertNotificationHub`**: Fully asynchronous `aiohttp` networking for Telegram and webhooks.

---

## 4. Key Advantages over Legacy System
1.  **Elimination of Excel Latency**: Moving from synchronous execution (Tick -> Write -> Wait) to asynchronous buffered queues.
2.  **Elimination of Duplicated Logic**: `IndicatorEngine` becomes the true Single Source of Truth.
3.  **Native Headless Support**: By disabling Layer 5, the core can run on cloud VMs for maximum throughput and simulated backtesting.
