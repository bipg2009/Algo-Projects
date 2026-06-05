# Algorithmic Scoring Logic (Maximum 165 Points)

## Entry Thresholds
| Score | Action |
| --- | --- |
| **100+** | Strong Buy |
| **85-99** | Buy |
| **70-84** | Watchlist |
| **<70** | Ignore |

The Option Scanner uses a dynamic scoring system to evaluate potential option contracts. 
Every evaluated option contract starts with a **Base Score of 60 points**. The system then adds or subtracts points based on the underlying market microstructure, momentum indicators, and institutional order flow.

### Score Components Summary
| Factor | Max Points |
| :--- | :--- |
| **Volume Expansion** | +15 |
| **OI Structure** | +20 |
| **VWAP + EMA Alignment** | +15 |
| **Premium Strength (Option VWAP)** | +10 |
| **ADX Regime** | +15 |
| **15-Minute Trend Filter** | +15 |
| **RSI Momentum** | +10 |
| **PCR** | +5 |
| **Maximum Total Score** | **165** |

---

## 0. Liquidity Filter (Hard Reject)
Liquidity filters execute before any scoring begins to instantly discard un-tradable options.
- **Bid-Ask Spread > 2%** ➔ **Trade Rejected**
- **Volume = 0** ➔ **Trade Rejected**
- **Option LTP < Minimum Premium** ➔ **Trade Rejected**

## 1. Option Volume Expansion (Max +15)
The algorithm detects discrete (1-minute) volume spikes on the specific option premium compared to its 20-period Exponential Moving Average (EMA).
- **Normal Mode:**
  - `Discrete Volume > Volume EMA` ➔ **+15 points**
  - `Discrete Volume <= Volume EMA` ➔ **-10 points**
- **Gap Mode:**
  - `Discrete Volume > (Volume EMA * 1.5)` ➔ **+15 points**
  - `Discrete Volume <= (Volume EMA * 1.5)` ➔ **-15 points**

## 2. Open Interest (OI) Structure (Max +20)
The scanner analyzes the institutional positioning from an Option Buyer's perspective by evaluating both `premium_change_pct` and `oi_change_pct` in tandem.
- **Short Covering (Very Bullish):** Premium > 0% AND OI < 0% ➔ **+20 points**
- **Long Build-Up (Bullish):** Premium > 0% AND OI > 0% ➔ 
  - *Base Score:* `+15 points` if Volume Confirmed, else `+5 points`.
  - *OI Multipliers:* 
    - `OI Change < 2%` ➔ **0.5x Multiplier**
    - `2% <= OI Change <= 5%` ➔ **1.0x Multiplier**
    - `OI Change > 5%` ➔ **1.5x Multiplier**
  - **Final OI Score = MIN(20, Calculated OI Score)**
- **Long Unwinding (Bearish):** Premium < 0% AND OI < 0% ➔ **-10 points**
- **Fresh Writing (Bearish):** Premium < 0% AND OI > 0% ➔ **-20 points**

## 3. Underlying Index Alignment (Max +15)
The algorithm checks if the underlying spot index (e.g., NIFTY) is aligned with its Volume Weighted Average Price (VWAP) and short-term trends.
- **For CALL (CE) Options:**
  - `Close >= VWAP` AND `EMA9 > EMA20` ➔ **+15 points**
  - Misaligned Trend ➔ **-15 points**
- **For PUT (PE) Options:**
  - `Close <= VWAP` AND `EMA9 < EMA20` ➔ **+15 points**
  - Misaligned Trend ➔ **-15 points**

## 4. Premium Strength (Option VWAP) (Max +10)
Checks the actual traded option instrument to ensure buyers are in control of the premium intraday.
- **For Both CE and PE:**
  - `Option LTP > Option VWAP` ➔ **+10 points**
  - `Option LTP <= Option VWAP` ➔ **-10 points**

## 5. ADX Regime (Max +15)
The system analyzes the trend strength using the 14-period ADX on the underlying 1-minute chart to identify healthy, trending markets. This strongly favors "Buy-the-Dip" / "Sell-the-Rip" environments and severely penalizes chop.
- **Strong & Rising Trend:** `ADX > 22` AND `ADX is rising (ADX Now > ADX Prev)` ➔ **+15 points**
- **Strong Trend (Not Rising):** `ADX >= 25` ➔ **+10 points**
- **Healthy Trend:** `22 <= ADX < 25` ➔ **+5 points**
- **Chop Penalty:** `18 <= ADX < 22` ➔ **-5 points**
- **Dead Market Penalty:** `ADX < 18` ➔ **-15 points**
- **Hard Kill:** `ADX < 15` ➔ **Trade Rejected**

## 6. 15-Minute Trend Filter (Max +15)
Filters out counter-trend trades by checking alignment on a Higher Timeframe (15-Minute) EMA equivalent.
- **For CALL (CE):**
  - `HTF_EMA20 > HTF_EMA50` ➔ **+15 points**
  - `HTF_EMA20 <= HTF_EMA50` ➔ **-20 points**
- **For PUT (PE):**
  - `HTF_EMA20 < HTF_EMA50` ➔ **+15 points**
  - `HTF_EMA20 >= HTF_EMA50` ➔ **-20 points**

## 7. Time-Weighted RSI Momentum (Max +10)
The system uses the 1-minute RSI on the underlying index to detect momentum breakouts. Points are scaled dynamically by a time-of-day multiplier.
- **For CALL (CE):**
  - `RSI >= CE_RSI_TRIGGER (e.g. 63)` ➔ **+10 points**
  - `RSI < 50` ➔ **-20 points**
  - **Hard Kill:** `RSI < 40` ➔ **Trade Rejected**
- **For PUT (PE):**
  - `RSI <= PE_RSI_TRIGGER (e.g. 41)` ➔ **+10 points**
  - `RSI > 50` ➔ **-30 points**
  - **Hard Kill:** `RSI > 60` ➔ **Trade Rejected**

## 8. Put-Call Ratio (Max +5)
Evaluates the broad market sentiment using the PCR ratio. The weighting is kept low because PCR is a lagging indicator.
- **For CALL (CE):** If `PCR > 1.15` (Bullish) ➔ **+5 points**
- **For PUT (PE):** If `PCR < 0.85` (Bearish) ➔ **+5 points**
