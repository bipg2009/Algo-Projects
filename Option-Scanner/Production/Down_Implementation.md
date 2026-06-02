# Refactor Downtrend_Sell.py for Production

The `Downtrend_Sell.py` script contains a very solid conceptual framework for a trend-continuation / mean-reversion scalping strategy. However, if deployed as-is, it will immediately fail in the production environment due to several critical architectural mismatches.

## Proposed Changes

Here is my plan to refactor the file to meet institutional coding standards and integrate cleanly with the Option Scanner framework.

### 1. Fix Indicator Key Mismatches
**Current State:** The script looks for `EMA_20`, `EMA_50`, `volume_ma_20`, `ADX`, and `ATR`.
**Production Reality:** `indicator_engine.py` generates `EMA20`, `EMA9`, and `Volume_EMA`. It does not calculate `EMA_50`, `ADX`, or `ATR` by default. 
**Proposed Fix:** I will update `indicator_engine.py` to calculate `EMA50`, `ADX`, and `ATR` so that the dataframe contains the exact metrics this strategy needs. I will also fix the string keys in `Downtrend_Sell.py` to match the exact output dictionary of the Indicator Engine.

### 2. Standardize Output Payload for the OMS Engine
**Current State:** The script returns underlying spot targets (`target_underlying`, `sl_underlying`).
**Production Reality:** The `TradePosition` and `Monitor_Engine` trail based on **Option Premium Points** (e.g., target = `entry_ltp + 60`). Spot trailing is dangerous because Delta shifts as the trade progresses.
**Proposed Fix:** I will refactor the return payload of `detect_downtrend_rejection_signal()` to map standard `target` and `sl` points based on the calculated spot distance multiplied by the requested `delta_target`.

### 3. Execution Pipeline Integration
**Current State:** The file is isolated and not called anywhere.
**Proposed Fix:** I will inject a call to `detect_downtrend_rejection_signal()` inside `Option_strategy_core.py`. If the primary breakout strategy doesn't trigger a trade, it will fall back to evaluating this "Sell the Rip" downtrend strategy.

## User Review Required

> [!WARNING]
> Before I proceed with rewriting the file and patching the Indicator Engine, please review the proposed fixes above. 

## Open Questions

> [!IMPORTANT]
> 1. Do you want this Downtrend strategy to run **alongside** our current RSI Momentum Breakout strategy (acting as a secondary trigger), or do you want it to **replace** the current strategy entirely?
> 2. Currently, it targets a 1:4 Risk-Reward ratio on the spot index. Do you want me to cap the Option Premium target to our standard 60 points (`System_Config.TARGET_POINTS`), or strictly follow the underlying Spot distances?
