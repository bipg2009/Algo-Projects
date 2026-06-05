# Live Trading Integration Plan: Theta-Dodge & OBI

Since we are scrapping the backtester for these two strategies due to historical data limits, we will integrate them directly into your Live Trading Engine (`Market_Scanner.py` and `MainEngine.py`) for paper trading.

## Goal
Transform the system from a single-strategy monolith into a **Multi-Strategy Engine** that can scan for Momentum Breakouts, Theta-Dodge scalps, and Order Book Imbalances simultaneously.

## Step-by-Step Implementation

### 1. Theta-Dodge Strategy Modifications
- **Fix the Volume Metric:** `Theta-Dodge.py` currently looks for `volume` and `volume_ma_20` in the `df_1m` (Nifty Spot). We will modify it to accept the NIFTY dataframe *and* the selected Option's live quote, so it can correctly check the Option Premium volume.
- **Scanner Integration:** Inject a hook into `Market_Scanner.py` that evaluates `Theta-Dodge.detect_scalp_signal()` on every iteration.

### 2. Order Book Imbalance (OBI) Modifications
- **Data Source:** To feed `total_buy_quantity` and `total_sell_quantity` into `detect_obi_signal`, we will use the live Option Chain payload fetched via `tsl.Dhan.option_chain()`. 
- **Scanner Integration:** Inject a hook in `Market_Scanner.py` to evaluate the OBI logic concurrently with the core strategy.

### 3. Queue & Signal Routing (`MainEngine.py`)
Currently, `Market_Scanner` sends a very simple payload: `{"symbol": "NIFTY...", "option_type": "CE", "score": 95}`.
The new strategies generate precise risk parameters natively (e.g., `"sl_underlying"`, `"trail_activation_underlying"`, `"time_stop_candles"`).

- **Modify `Market_Scanner`** to append a `"strategy"` flag (e.g., `strategy: "theta_dodge"`) and the custom risk parameters into the `signal_queue`.
- **Modify `MainEngine.py` and `oms_engine.py`** to detect the `"strategy"` flag. If a custom strategy is detected, the engine will override the default 15-point stop-loss logic and instead use the exact dynamic SL and trailing steps requested by `Theta-Dodge` or `OBI`.

> [!WARNING]
> **Order Book Depth Dependency**
> The OBI strategy calculates `(bid_qty - ask_qty) / total`. We will pull `total_buy_quantity` and `total_sell_quantity` from the Live Dhan API Option Chain snapshot. We need to ensure that Dhan's option chain endpoint provides Market Depth fields; if it does not, OBI will remain dormant.

## User Review Required
Does this architecture align with how you want them running? (i.e., running in parallel on the live scanner, generating signals with custom dynamic stop-losses for the Main Engine to execute).
