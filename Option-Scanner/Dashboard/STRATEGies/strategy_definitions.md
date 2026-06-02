# Strategy Definitions & Conditions
*This document tracks the exact rule logic for all live trading strategies.*

> [!NOTE]
> This file serves as the definitive logic ledger. If we adjust thresholds or rules in the future, those changes will be appended or update here.

---

## [Uptrend_Buy.py] 1. Momentum Breakout (Uptrend)
*Regime: Strong Trending Market*

**Logic:** Buys the dip on a pullback to value (VWAP/EMA) during a strong structural uptrend.

**Exact Conditions:**
* **Regime Filter:** ADX must be >= `22` (Chop Threshold). ADX must be rising (Current ADX > Previous ADX). Fast moving average must be above slow (EMA20 > EMA50).
* **Structural Filter:** Must maintain a "Higher Low" structural pattern. The current low must be strictly greater than the previous swing low (over a 20-candle lookback).
* **Distance/Support Check:** Price must pull back and touch dynamic support. The distance between the current low and either VWAP or EMA20 must be <= `ATR * 0.25`.
* **Candle Rejection:** The candle must be bullish (green, Close > Open). Must prove rejection of lower prices with a lower wick that is >= the candle body.

---

## [Downtrend_Sell.py] 2. Momentum Breakout (Downtrend)
*Regime: Strong Trending Market*

**Logic:** Sells the rip on a rally to resistance (VWAP/EMA) during a strong structural downtrend.

**Exact Conditions:**
* **Regime Filter:** ADX must be >= `22`. ADX must be rising (Current ADX > Previous ADX). Fast moving average must be below slow (EMA20 < EMA50).
* **Structural Filter:** Must maintain a "Lower High" structural pattern. The current high must be strictly less than the previous swing high (over a 20-candle lookback).
* **Distance/Resistance Check:** Price must rally and touch dynamic resistance. The distance between the current high and either VWAP or EMA20 must be <= `ATR * 0.25`.
* **Candle Rejection:** The candle must be bearish (red, Close < Open). Must prove rejection of higher prices with an upper wick that is >= the candle body.
* **Price Action Confirmation:** The current low must break below the previous low (`curr_low < prev_low`).

---

## [Chop_Mode.py] 3. Chop Mode Reversion
*Regime: Sideways / Range-bound Market*

**Logic:** Mean reversion strategy that buys bounces off the lower Bollinger Band and rejects from the upper Bollinger Band when directionality is dead.

**Exact Conditions:**
* **Regime Filter:** ADX must be strictly `< 22`.
* **CE Signal (Bounce):** 
  * Close price drops below the Lower Bollinger Band (20-period, 2 StdDev).
  * RSI reaches oversold exhaustions (`RSI < 30`).
* **PE Signal (Reject):**
  * Close price rises above the Upper Bollinger Band (20-period, 2 StdDev).
  * RSI reaches overbought exhaustions (`RSI > 75`).
* **Execution:** Selects deep ITM options (Delta ~ 0.70) to capture the bounce efficiently.

---

## [Theta_Dodge.py] 4. Theta Dodge Scalper
*Regime: Choppy Market (Fast Spikes)*

**Logic:** Extremely fast scalping logic designed to jump in and out of micro-structure volume bursts while dodging time-decay in choppy markets.

**Exact Conditions:**
* **Regime Filter:** ADX must be `< 22`.
* **Volatility Filter:** ATR must be between `5.0` and `18.0` points (tradable range), and ATR must NOT be expanding (Current ATR <= Previous ATR).
* **Timing Filter:** Will not fire during the Opening Range Breakout (first 45 minutes of the market open).
* **Volume Burst:** Option volume must instantly surge `> 1.5x` its 20-period moving average.
* **CE Scalp:** Previous close was below the Lower BB, current close is back *above* the Lower BB, and current close is above VWAP.
* **PE Scalp:** Previous close was above the Upper BB, current close is back *below* the Upper BB, and current close is below VWAP.

---

## [Order_Book_Imbalance.py] 5. Order Book Imbalance (OBI)
*Regime: Momentum / Micro-trend*

**Logic:** Detects institutional buying/selling pressure by tracking Bid vs Ask limits directly in the live broker exchange feed.

**Exact Conditions:**
* **Calculation:** Imbalance = `(Total Bid Qty - Total Ask Qty) / (Total Bid Qty + Total Ask Qty)`.
* **Thresholds:** Maintains a rolling mean and 2 standard deviations (+/-) of the imbalance over a 60-period history.
* **Volume Confirm:** Current underlying volume must be `> 1.5x` its 20-period average.
* **CE OBI Signal:** 
  * Imbalance has persisted above the `Upper Threshold` (+2 StdDev) for the last 3 consecutive ticks.
  * Price is rising (Current Close > Prev Close).
  * Price > VWAP.
  * EMA20 > EMA50.
  * Put-Call Ratio (PCR) `>= 0.60`.
* **PE OBI Signal:** 
  * Imbalance has persisted below the `Lower Threshold` (-2 StdDev) for the last 3 consecutive ticks.
  * Price is falling (Current Close < Prev Close).
  * Price < VWAP.
  * EMA20 < EMA50.
  * Put-Call Ratio (PCR) `<= 1.40`.

---

## [Option_Sell_Script.py] 6. Option Selling Strangle Script
*Regime: Sideways / Trend Fading*

**Logic:** A manual-execution utility script that fetches the option chain and places short-sell market orders (MIS) for Out-of-the-Money (OTM) options. It uses Supertrend and RSI to determine whether to sell naked options or a dual-leg short strangle.

**Exact Conditions:**
* **Strike Selection:** Automatically calculates ATM based on NIFTY Spot, then targets CE and PE strikes based on `OTM_OFFSET_POINTS` defined in `System_Config.py`.
* **Bullish Selling:** If Nifty 1m Supertrend is `GREEN` and RSI `> 55` (Strongly Bullish), it will sell **OTM PE only** to capture downside premium decay.
* **Bearish Selling:** If Nifty 1m Supertrend is `RED` and RSI `< 45` (Strongly Bearish), it will sell **OTM CE only** to capture upside premium decay.
* **Sideways Selling:** If conditions do not align with a strong trend (e.g. chop/sideways), it will sell **BOTH** OTM CE and OTM PE to create a **Short Strangle**, capturing theta decay on both sides.
* **Execution:** Prompts the user for manual confirmation and lot size before routing the sell orders directly to the broker via the Main Engine.

---

## [Option_strategy_core.py] 7. Core Selection Rules
*Applies to standard breakout strategies.*

**Logic:** Validates that the selected option contract is safe to trade based on underlying volume and open interest barriers.

**Exact Conditions:**
* **Moneyness / Strike Distance:** The selected strike must be near ATM (In-the-Money or At-the-Money). It will instantly reject strikes that are too far Out-of-the-Money.
* **Volume Support:** The chosen direction (CE or PE) must have massive institutional interest. The total volume for the chosen option type must be strictly `> 1.2x` the total volume of the opposing type across the chain.
* **Open Interest Support:** Similar to volume, the Open Interest must heavily favor the trade direction. For a PE trade, Total CE OI (Resistance) must be `> 1.2x` Total PE OI. For a CE trade, Total PE OI (Support) must be `> 1.2x` Total CE OI.
* **Open Interest Barrier Defense:** Ensures price is not running directly into a wall. The code scans for the nearest strike with the highest Open Interest. The distance to this "OI Wall" must be `>= 60` Nifty points.

**Scoring Mechanism (build_score)**:
Every valid option contract is dynamically scored out of 100 before execution. A trade is only executed if the final score hits the `STRONG_BUY_THRESHOLD` (currently 87, or 92 in gap mode). 
The scoring starts at a baseline of **60**, representing neutral viability, and adds/subtracts points based on multiple independent confirmations:
* **Volume Expansion:** `+15` points if discrete 1-minute volume is greater than its EMA. `-10` points if it fails to beat its average.
* **OI Buildup:** `+15` points if the option's OI jumped > 5% in the last tick. `-15` points if OI dropped < -2%.
* **VWAP & EMA Alignment:** `+10` points if the Spot price is on the correct side of VWAP and fast EMA (9) is perfectly aligned with slow EMA (20). `-15` points if trend structure is wrong.
* **PCR Confirmation:** `+10` points if the Put-Call Ratio (PCR) explicitly confirms the trend direction (> Bullish threshold for CE, < Bearish threshold for PE).
* **RSI Momentum:** Dynamic points are added based on how deeply the RSI has crossed the breakout trigger, adjusted by a time-of-day multiplier. Massive penalties (`-20` to `-40` points) are applied if the RSI completely contradicts the trade direction.

---

## [Risk_Engine.py] 8. SEDA Risk Firewall
*Applies globally across all trades.*

**Logic:** Intercepts signals and blocks execution if account limits or high-risk state conditions are met.

**Exact Conditions:**
* **Hard Account Limits:** 
  * Rejects trades if the Daily Loss Limit is hit.
  * Rejects trades if Maximum Consecutive Losses are reached.
  * Rejects trades if the Maximum Drawdown percentage is breached.
* **Contextual Confidence:** Normal minimum signal confidence is 65. If the daily P&L is negative, the engine tightens the requirement and demands a confidence of 75 to trade.
* **Dynamic Sizing:** Halves (0.5x) the base lot size during `PANIC_VOLATILITY` states to protect capital. Increases size (1.5x) if the market is in a `STATE_TREND_ACCELERATION` and signal confidence is > 85.
* **Gap Risk Check:** Instantly blocks execution if the market opens with a gap of `> 250` Nifty points.

---

## [Price_Check.py & Monitor_Engine.py] 9. Execution & Trailing Rules
*Applies globally to all active open positions.*

**Logic:** Manages the position lifecycle, implements the Antigravity trailing stop logic, and triggers safety exits.

**Exact Conditions:**
* **Antigravity Trailing SL (Pure Premium Continuous):**
  1. **Continuous 15-Point Trail:** The moment the trade is executed, the Trailing Stop Loss (TSL) continuously tracks exactly `15 points` behind the peak option premium. 
  2. **100-Point Tightening Lock:** If the option premium hits a massive runner and the peak price reaches `Entry Price + 100 points`, the TSL violently tightens to track exactly `5 points` behind the peak price. Once in this mode, it locks and aggressively trails the price upward by 5 points for the rest of the trade.
* **Hard Stop Loss:** Exits instantly if the option premium hits the active Stop Loss. *(Note: Underlying Nifty spot SL logic has been completely removed).*
* **Supertrend Reversal (3-Candle Confirmation):** When the 1-minute Supertrend indicator flips color against the position (e.g., holding a CE and Supertrend flips RED), the system does **not** exit instantly. Instead, it enters a confirmation sequence using **Heikin-Ashi** candles to filter out market noise:
  1. **65% Trailing Warning:** If the previous closed Heikin-Ashi candle is against the trend, AND the currently forming Heikin-Ashi candle is against the trend at `>= 39 seconds` (65% completion), the Premium Stop Loss is immediately tightened to `Current LTP - 5 points`. Once tightened, this trailing SL is locked and cannot be loosened.
  2. **Hard Exit:** If 3 consecutive completed Heikin-Ashi candles close against the trend, the system instantly exits the trade at market price.
* **OI Unwinding Exit:** Exits if the option's Open Interest drops by `> 15%` from the entry baseline (indicating big players are exiting).
* **Time Decay Cutoff:** Exits the trade exactly at `12 minutes` if the open profit is strictly `< 5 points` (cutting dead trades).
