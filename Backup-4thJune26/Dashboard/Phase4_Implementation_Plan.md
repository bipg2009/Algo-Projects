# Phase 4 — Event-Driven Architecture Implementation Plan

Phase 4 tackles the hardest architectural challenges: replacing the "script-like" file-polling orchestration with an institutional-grade, event-driven server model.

## User Review Required

> [!IMPORTANT]  
> **React Web Dashboard instead of Excel**  
> Moving to a React-based web dashboard is a phenomenal idea. It is vastly superior to Excel in terms of latency, stability, and aesthetics. 
> 
> **How it works:**
> 1. We will add a lightweight **FastAPI WebSocket Server** to run in the background of `MainEngine.py`.
> 2. The Scanner and Price Tracker will push their live updates to this server via memory queues.
> 3. We will build a stunning, dynamic **React web app (using Vite and Tailwind/Vanilla CSS)** that runs locally in your browser. It will connect to the WebSocket and instantly display active trades, signals, and system health with micro-animations.
>
> *Question for you:* Are you okay with me initializing a new React web app inside a `dashboard/` subfolder in your Option-Scanner project directory?

## Proposed Changes

### 1. The Event Bus & WebSocket Server
**[NEW] `event_bus.py` & `api_server.py`**
- Create a centralized, thread-safe module using `queue.Queue`.
- Start a `FastAPI` WebSocket server that reads from the `dashboard_queue` and pushes JSON updates to the React frontend.

### 2. Managed Workers (Replacing Naked Subprocesses)
**[MODIFY] `oms_engine.py` & `Price_Check.py`**
- `Price_Check.py` will run as a background thread managed by `MainEngine`. It will no longer spawn a new console.
- `Market_Scanner.py` will also run as a background thread.
- Instead of printing to the console, they will push UI packets to `dashboard_queue`.

### 3. Dynamic React Dashboard
**[NEW] `dashboard/` (React Web App)**
- Use `npx create-vite-app` to scaffold a modern web UI.
- Build a premium, dark-mode dashboard showing:
  - Scanner Status (Scanning/Mute)
  - Active Trades (LTP, Stop Loss, Target, PnL)
  - Recent Signals & System Alerts

### 4. Zero-Blocking Execution Paths
**[MODIFY] `oms_engine.py`**
- Replace all busy-wait loops (`while True: time.sleep(1)`) used for test confirmations. Use threading events.

### 5. Risk Engine Re-Alignment
**[MODIFY] `MainEngine.py`**
- Route all signals dequeued from the `signal_queue` through `Risk_Engine.evaluate_offer()` before reaching OMS.

---

## Verification Plan

### Automated Tests
- N/A 

### Manual Verification
1. Boot the `MainEngine` Controller.
2. Open `localhost:5173` in your browser.
3. Type `market` in the Controller. Verify the web dashboard immediately shows the scanner as "Active" and displays live market updates.
4. Verify no `.json` IPC files are created on disk.
