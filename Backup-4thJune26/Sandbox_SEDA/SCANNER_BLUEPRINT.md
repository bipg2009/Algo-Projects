# Option Scanner — file blueprint

## Live trading (required)

Run from folder: `Option Scanner`

| File | Role |
|------|------|
| **Market_Scanner.py** | Main loop: NIFTY 1m, option chain, signal rules, `scanner_state.json`, spawns **MainEngine** |
| **MainEngine.py** | Execution only (no scan): buy/sim order, ledger CSV, spawns **Price_Check** |
| **Price_Check.py** | Live SL/target dashboard (spawned by MainEngine); releases **SCAN** on EXIT |
| **Dhan_websocket.py** | Live WebSocket → `Websocket.xlsx` columns C–J (Quote mode) |
| **Dhan_Tradehull.py** | Dhan login, intraday, option chain, REST LTP batches |
| **Option_strategy_core.py** | RSI, score, ITM distance, `detect_trigger_1m` |
| **RiseFall_sub.py** | RSI rules: neutral **39–73** no action; bull **≥73**; bear **≤39** + 15m exhaustion check |
| **Risk_Engine.py** | Gap/VWAP/candle/RSI memory filters |
| **Monitor_Engine.py** | Trailing SL / exit rules (used by Price_Check) |
| **scanner_excel.py** | Websocket quotes, sheet cleanup, ITM rows, hourly CSV log |
| **excel_ledger_orderbook.py** | `trading_execution_ledger.csv` after each buy |
| **cred.env** | `DHAN_CLIENT_CODE`, `DHAN_TOKEN_ID` |
| **Websocket.xlsx** | Watchlist sheet `LTP` (A=symbol, B=exchange, C–J=quotes) |
| **scanner_state.json** | `SCAN` / `MUTE` between scanner and execution |
| **Dependencies/** | Instrument CSV, logs, hourly_logs |

### Typical live commands

```bat
run-scanner.bat          → Market_Scanner.py
py Dhan_websocket.py     → live Excel (set SYNC_EXCEL_LTP=False if both run)
```

Manual execution test (no scan):

```bat
py MainEngine.py "NIFTY 26MAY 24000 CE" CE 90
```

---

## Signal logic (audit summary)

1. **Market_Scanner** loads NIFTY 1m (≥30 bars), supertrend on prior bar.
2. **Side**: GREEN → CE only; RED → PE only.
3. **Per contract** (option chain, same expiry):
   - `build_and_score_contract` → need score ≥ **85**
   - `detect_trigger_1m` → deep **ITM 100pt** (150 gap), risk OK, score ≥ 85/92, RSI/trend (`RiseFall_sub`), etc.
4. **Signal** → `MUTE` + spawn **MainEngine.py** with `symbol`, `CE|PE`, `score`.
5. **MainEngine** → order + ledger + **Price_Check** (scanner stays MUTE).
6. **Price_Check** EXIT → writes `scanner_state.json` **SCAN** (or 10 min MUTE auto-release).

Console hints: `[rsi]` neutral/bull/bear status, trend mismatch, volume vs 20 EMA cross, OI change ≥20%, reject reasons, hourly CSV under `Dependencies/hourly_logs/`.

---

## Backtest (separate — not for live)

| File | Role |
|------|------|
| **BackTesting/** | Historical backtest scripts, caches, reports |
| **NSE-Option-Scanner-Backtest.py** | Root entry to backtest pipeline |

Live trading does **not** run **MainEngine** as a scanner; use **Market_Scanner.py** only for live API scan loop.

---

## Removed (fragmented / obsolete root `.py`)

Consolidated into **scanner_excel.py**:

- ~~watchlist_quote_columns.py~~
- ~~websocket_itm_sheet.py~~
- ~~websocket_sheet_validator.py~~
- ~~hourly_signal_log.py~~
- ~~clean_websocket_sheet.py~~ (cleanup = `CLEAN_INVALID_WS_ROWS` on scanner startup)

Deleted legacy / scratch:

- ~~Engine.py~~ — replaced by **MainEngine.py** (execution) + **Price_Check.py** (monitoring)
- ~~Dhan-codebase.py~~ — old demo
- ~~Multi Timeframe Algo.py~~ — separate experiment
- ~~dhan_fast.py~~ — unused helper
- ~~Excel/import os.py~~ — misnamed scratch script

---

## Dependency graph (live)

```
MainEngine
    |
Market_Scanner ──► Option_strategy_core ──► Risk_Engine
       │                    ├──► RiseFall_sub
       │                    ▲
       ├──► Dhan_Tradehull ──┘
       ├──► scanner_excel
       └──► MainEngine ──► excel_ledger_orderbook
                    └──► Price_Check ──► Monitor_Engine

Dhan_websocket ──► Dhan_Tradehull (instruments)
                 └──► scanner_excel (column helpers)
```

---

## Maintenance

- Prefer changing **Option_strategy_core** / **RiseFall_sub** / **Risk_Engine** for signal rules.
- Prefer **scanner_excel** for Excel/watchlist/hourly log only.
- **MainEngine.py**: execution settings (`ENABLE_ORDER_EXECUTION`, lot size, target/SL points).
- **Websocket.xlsx**: only **3 CE + 3 PE** from ATM (ATM, ATM±50, ATM±100 for NIFTY). Extra FNO rows are removed on startup and every ~90s.
- **OI_Volume_Alerts.xlsx**: separate log for `[oi]` / `[vol]` alerts (written by scanner via openpyxl, not websocket).
- Avoid adding new root `.py` files unless they are a new runnable entry (like Market_Scanner or MainEngine).
