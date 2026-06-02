# Proposed Architecture Flow (Scalable & Modular)

## Core Philosophy
The new architecture is built on the **Single Responsibility Principle** and an **Event-Driven / Pipeline approach**. This ensures the system can be scaled, tested (head-less without Excel), and maintained easily without massive file sizes.

---

## 1. Data & Broker Connectivity Layer (The Suppliers)
**Responsibility:** Fetch data from APIs and WebSockets. Provide centralized, clean data to the rest of the application.
*   `broker_client.py`: Singleton/Manager around `Tradehull` for HTTP polling (historic data, chains).
*   `socket_manager.py`: Manages WebSocket connections and raw ticking data.
*   `state_manager.py`: A thread-safe data store (eventually replaceable by Redis if scaled out) holding the latest LTPS, Nifty levels, and PCR.

## 2. Technical Math & Indicators Layer (The Calculators)
**Responsibility:** Pure mathematical calculation.
*   `indicators.py`: Contains `calculate_rsi()`, `add_vwap()`, `calculate_volume_ema()`, etc.
*   *Key Constraint:* No API calls, no print statements, no Excel links. Input is raw data (Pandas DF), Output is calculation results.

## 3. Strategy & Risk Engine (The Brains)
**Responsibility:** Analyze the state and indicators to produce Boolean or numeric Signals (Buy/Sell/Hold).
*   `strategy_runner.py`: Orchestrates specific strategies (e.g., Option buying logic).
*   `chain_analyzer.py`: Calculates OTM/ITM distances, PCR shifts, and volume spikes.
*   `risk_manager.py`: Gap risk, chop detection, and theta dodging. Acts as a strict firewall for trade signals.
*   *Key Constraint:* If this layer says "TRADE", the orchestrator listens. It does not execute the trade itself.

## 4. Presentation & Alerts Layer (The Output)
**Responsibility:** Formatting data for user consumption.
*   `excel_adapter.py`: Only updates specified cells/rows using `xlwings`.
*   `console_logger.py`: Beautiful terminal formatting (replaces scattered print statements).
*   `alerts_dispatcher.py`: Telegram logs, local sound alerts (wav).

## 5. Execution Engine (The Order Taker)
**Responsibility:** Managing live orders and lot sizing.
*   `trade_execution_manager.py`: Handles Dhan order placement and calculates lots.
*   `trade_ledger.py`: Records entries, exits, and P&L.

## 6. The Central Orchestrator (The Conductor)
**Responsibility:** Tie it all together without containing any heavy logic.
*   `master_loop.py` (Replaces `MainEngine.py` and `Market_Scanner.py` main functions).
*   *Flow:*
    1. Triggers `broker_client` to get latest data.
    2. Passes data to `indicators`.
    3. Passes indicators to `strategy_runner`.
    4. If signal is triggered, passes to `risk_manager`.
    5. If risk passed, passes to `trade_execution_manager` AND `alerts_dispatcher`.
    6. Passes current state to `excel_adapter` for UI update.

## Future-proofing Checklist:
- [x] **Headless Support**: Excel is now an optional "Adapter". The system can run on a remote cloud server via Terminal.
- [x] **DRY Principles**: Math and Risk checks are completely centralized. No duplicate RSI code.
- [x] **Testability**: Because `indicators.py` and `strategy_runner.py` are separated from real-time WebSockets, we can feed them mock CSV data easily.
