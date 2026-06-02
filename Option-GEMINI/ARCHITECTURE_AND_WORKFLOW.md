# FnO Algorithmic Trading Safety Arena
## Production-Grade Architecture & Workflow Specification

This document provides a detailed breakdown of the system architecture, sequential workflows, module roles, and error-resilience rules designed to safeguard Option and Futures execution.

---

## 1. System Architecture Diagram & Topology

Below is the conceptual topological flow of the system. The platform is designed with a strict **unidirectional state-boundary** separated into three primary phases: **Scan & Filter**, **Verification & Order Entry**, and **Automated Tracking (Hypercare)**.

```text
                      +-------------------------+
                      |   Dhan Exchange Server  |
                      +------------+------------+
                                   ^  | 
          Live Tick Feed (REST/WS) |  | 
                                   |  v
+------------------+     +-------------------------+     +------------------+
| Communication.py |<----|    Dhan_Tradehull.py    |---->| scanner_excel.py |
| - Health tracker |     +----+---------------+----+     | - Records scans  |
| - Reg Heartbeat  |          |               |          | - Status log     |
+------------------+          | Continuous    |          +------------------+
                              | Polling       |                    ^
+------------------+  +-------v---------------+-------+  +---------|--------+
|  Indicators.py   |->|       Market_Scanner.py       |<-|  Risk_Engine.py  |
|  - VWAP, EMAs,   |  |  - Core Indicator Poll        |  |  - Gap-risk,     |
|  - Volume EMAs   |  |  - Evaluates Nifty Spot/Chain |  |    Candle size   |
+------------------+  +---------------+---------------+  +------------------+
                                      |
                    Writes trigger to | signal.json
                                      v
+------------------+  +---------------+---------------+  +------------------+
| excel_ledger_    |<-|         MainEngine.py         |->| Option_strategy_ |
| orderbook.py     |  |  - Central Controller         |  | core.py          |
| - Logs execution |  |  - High-res math valuation    |  | - Indep. checks  |
+------------------+  +---+-----------------------+---+  +------------------+
         ^                |                       |
         |      +---------v----------+  +---------v----------+
         |      |  Chain_Analyzer.py |  | Trade_Calculator.py|
         |      |  - Obstacles,      |  | - Lot Size, Target |
         |      |    OI/Vol ratio    |  |   Est. Margin      |
         |      +--------------------+  +---------+----------+
         |                                        |
         |                                        | Spawns Subprocess
         |                                        v
         |            +---------------------------+-----------+  +-------------------+
         +------------|          Price_Check.py               |->| Monitor_Engine.py |
         (On BUY/SELL)|  - 30s High-Contrast Terminal         |  | - Live Trailing   |
                      |  - Continuous Post-entry Tracker      |  | - SL/Target eval  |
                      +---------------------------+-----------+  +-------------------+
                                                  |
                                Exit Signal / Sells triggers
                                                  v
                              Writes exit_signal.json -> Resumes Scan
```

### Key Supporting Modules Added Context
* **`System_Config.py`**: A central configuration registry holding all global constants (e.g., `UNDERLYING = "NIFTY"`, intervals, strikes, limits). All other files (`Market_Scanner.py`, `scanner_excel.py`, `Indicators.py`, etc.) import their configuration constants directly from this file to ensure uniformity and prevent hardcoded drift.
* **`Monitor_Engine.py`**: A specialized sub-engine called exclusively by `Price_Check.py` executing post-trade trailing evaluations (chart reversals, trailing target calculations, and dynamic stop-loss adjustments).
* **`Communication.py`**: A decoupled health and diagnostic module handling module-to-module ping heartbeats and API status resolutions.
* **`excel_ledger_orderbook.py` / `scanner_excel.py`**: Decoupled ledger repositories keeping API transaction states entirely separated from scanner history streams to avoid lock-contention. `scanner_excel.py` also handles the Excel synchronization routines moved out of `Market_Scanner.py`.
* **`Indicators.py`**: Computes moving averages, VWAP, and RSI. All RSI trend evaluation logic and band alerts have been consolidated here to reduce the footprint of the scanner.

---

## 2. Shared File Separation: `scanner_excel.py` vs. `excel_ledger_orderbook.py`

To eliminate write conflicts and blockages during parallel processing, the file-storage responsibilities are strictly separated between two dedicated Excel handlers:

### A. `scanner_excel.py`
* **Focus**: Market Scan Logging and Context Recording.
* **Role**: Serves as the recording ledger of active and past and ignored *signals*.
* **Write Pattern**: Appends scan-heartbeats, historical option chain snapshots, RSI-triggers, and PCR values when scanning the market. It maintains high-level statistics for model tuning and historical auditing of indicators.
* **State Behavior**: Safely appends and modifies sheets in-memory or via locked append routines to avoid crashing when the scanner is looping rapidly (250ms–1s ticks).

### B. `excel_ledger_orderbook.py`
* **Focus**: Real-Time Order Auditing and Transaction Execution.
* **Role**: High-speed, sequential operational transaction repository (like a banking ledger).
* **Write Pattern**: Specifically tracks:
  1. `BUY` / `SELL` (Completed successfully).
  2. `BUY_PENDING_DELAY` / `SELL_PENDING_DELAY` (If Tradehull takes more than 19ms to hand over the API response).
  3. `BUY_CONFIRMED` / `SELL_CONFIRMED` (Once the pending confirmation resolves without partial errors).
* **State Behavior**: Written immediately before and after trade executions to log order fill prices, lot sizes, utilized broker margins, commission estimates, and execution speed metrics.

---

## 3. High-Res Sequential Execution Workflow

### Step 1: Scanner Initialization & Baseline Tracking
1. `Market_Scanner.py` starts up and acquires current stock market metrics.
2. It fetches the daily NIFTY historical context: **Yesterday's Close** and **Today's Open**.
3. It passes these figures to `Risk_Engine.py` which computes gap risk (`Gap Risk Threshold: 250 points`). If a major gap is detected, a 20-minute gap cooldown block in `Risk_Engine.py` triggers to filter out volatile, unanchored opening candles.

### Step 2: Live Indicator Filtering
1. For every live chart tick, `Market_Scanner.py` retrieves the NIFTY Index candle history.
2. It calls `Indicators.py` to compile VWAP, EMA-9, and EMA-20 lines.
3. The option chain is parsed. It filters for deep In-The-Money (ITM) options contracts conforming to `Option_strategy_core.py` rules (`Normal ITM distance: 100 points`, `Gap-mode distance: 150 points`).

### Step 3: Directional & Behavioral Risk Filtering
Before evaluating indicators, `Market_Scanner.py` queries `Risk_Engine.py` to pass the candle through strict safety sieves:
* **VWAP Extension**: Blocks trade if the asset's current price is overextended from VWAP by more than `0.45%` (prevents entering at volatile high peaks).
* **Candle Exhaustion**: Blocks trade if a single 1-minute candle distance exceeds `0.45%` (prevents chasing spike breakouts).
* **RSI Memory Scan**: Blocks trade if the RSI has crossed severe thresholds (`CE_RSI_EXHAUSTION: 85`, `PE_RSI_EXHAUSTION: 20`) in the preceding 30 candles (prevents entering late stages of an exhausted rally or crash).

### Step 4: Technical & Multidimensional Score Scoring
If risk filters are satisfied, `Option_strategy_core.py` computes the composite technical score (Scale: 0–100):
* **Volume Delta**: Boosts score by `+15` points if latest volume exceeds Volume-EMA, or penalizes by `-10` points otherwise (utilizes `parse_discrete_1m_volume` from `Indicators.py`).
* **Open Interest (OI) Delta**: Boosts score by `+15` points if latest OI change is positive, or penalizes by `-15` points if negative.
* **Trend Alignment**: Boosts score by `+10` points if close is aligned with VWAP & EMA crossovers, or penalizes by `-15` points.
* **Put-Call Ratio (PCR)**: Boosts score by `+10` if PCR supports direction.
* **Time-Weighted RSI Breakout**: Multiplies RSI score impact based on the exact time of day (`Opening: 1.2x`, `Morning: 1.0x`, `Midday: 0.9x`, `Afternoon: 1.0x` via `RiseFall_sub.py`).

If the final score is above the target (`Strong Buy Threshold: 85`, or `92` if in gap-recovery mode), a buy alert triggers.

### Step 5: Master Head Handoff & Double-Calculation Verification
1. `Market_Scanner.py` writes the candidate contract data to `signal.json` and locks itself out by changing `scanner_state.json` status to `"EXECUTE"`.
2. `MainEngine.py` (system head controller) intercepts the `signal.json`.
3. `MainEngine.py` requests `Trade_Calculator.py` to construct an execution parameter sheet containing exact Lot Sizes, Target Levels, trailing SLs, and estimated margin needs based on `Margin_Requirement_PC = 12%`.
4. `MainEngine.py` then passes this execution sheet to `Option_strategy_core.py` (via `verify_trade_calculations`).
5. `Option_strategy_core.py` independently carries out duplicate mathematical formulas. If any figures (e.g. SL, target, margins, quantity of lots) differ by even 1 paisa from `Trade_Calculator.py` outcomes, **the execution is immediately aborted** as a mathematical fail-safe.
6. `MainEngine.py` checks `Chain_Analyzer.py` via `is_safe_to_trade()`. If the macro option chain findings indicate massive overhead OI concentrations (major roadblocks) or directional volume mismatch, **the transaction aborts**.

### Step 6: Tradehull API Execution & Precision Logging Gate
1. Once math and macro checks compile green, `MainEngine.py` resets a microsecond timer.
2. It calls `Tradehull.py` to submit a `MARKET BUY` NFO order.
3. If Tradehull receives direct API confirmation from the exchange under **19 milliseconds**, the transaction is logged immediately as `BUY` inside `excel_ledger_orderbook.py`.
4. If a network delay occurs and execution exceeds **19ms**, it is logged instantly to the ledger as `BUY_PENDING_DELAY`. When the confirmation resolves via subsequent polling, it updates to `BUY_CONFIRMED`.

### Step 7: Hypercare Live Tracking & Stop Loss Execution
1. Once filled, `MainEngine.py` spawns `Price_Check.py` as an independent subprocess console.
2. `Price_Check.py` enters high-care mode. It loops continuously, updating the console with a clean formatted terminal block every **30 seconds**.
3. It fetches live LTP, current Open Interest updates, and 1-minute chart RSI from `Monitor_Engine.py`.
4. It dynamically trails the Stop Loss as the price reaches target fractions.
5. If Stop Loss or Target is breached, or the chart indicators execute a reversal pattern (`Monitor_Engine.py` rule), `Price_Check` triggers a `MARKET SELL` order.
6. Similar to step 6, execution status is audited over the 19ms deadline. It logs `SELL_PENDING_DELAY` or `SELL_CONFIRMED` cleanly.
7. Upon order verification, `Price_Check.py` safely reverses the status inside `scanner_state.json` back to `"SCAN"` and exits itself, resuming the main scan loop.

---

## 4. Error Handling & Recovery Architecture (`SafetyLogger.py`)

Every file contains a strict `try-except` blanket with an explicit fallback design. If a database or API timeout occurs:

1. **SafetyLogger Pipeline**: Errors do not bubble up or crash execution. Instead, they are caught by `SafetyLogger.log_error_with_context()`.
2. **Context Enrichment**: The logger records the Python Module, exact method name, underlying system traceback, and variables (such as active LTP, active Option Striking distance, dynamic RSI values, and timestamps) at the split-second of failure.
3. **Registry Heartbeat Checking**: The module updates the `Communication.py` registry with status `"ERROR"`. If a module goes silent for more than 5 seconds, `Communication.py` classifies it as unresponsive (`RED_FLAG`) and alert streams trigger.
4. **Resilient Data Defending**: 
   * If `Indicators.py` misses closing values, it defaults series to safe neutral baselines (`RSI = 50.0`, `VWAP = close`) instead of crashing the core math engine.
   * If `Risk_Engine.py` encounters missing data during risk audits, it fails "closed" (e.g., reports VWAP as overextended, candle as exhausted, and blocks trading completely).
   * If `Chain_Analyzer.py` parses a malformed option chain DataFrame from Tradehull, it returns benign default states to prevent locking up the loop.

---
*Created on 2026-05-26 as a definitive production blueprint for FnO Trading Algo Safety Arena.*
