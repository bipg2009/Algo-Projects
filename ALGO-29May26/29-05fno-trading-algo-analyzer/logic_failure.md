# Logic Failure Log

## Issue: RSI below 30 not generating alerts

Conversation with Cursor regarding why an RSI below 30 does not trigger any alerts.

**User:**
rsi below 30 why it did not generate any alerts ?

**Cursor:**
I’ll check the current trigger conditions in your strategy code to explain exactly why RSI < 30 can still produce no alert.

RSI < 30 alone is not enough in your scanner.

For PE alerts, your logic requires multiple gates to pass, so low RSI can still be rejected:

1. RSI shape condition: not just low RSI now, it also checks recent RSI history (came_from_upper_band) and exhaustion.
2. Exhaustion block: if RSI stayed too low for too long, it is treated as exhausted and blocked.
3. Trend must be RED at trigger candle.
4. Deep ITM rule must pass (PE strike needs to be sufficiently above spot).
5. OI barrier distance must be safe.
6. Directional volume ratio must favor PE side.
7. Risk engine checks (VWAP extension, candle exhaustion, gap filters, etc.).
8. Score threshold must clear STRONG_BUY_THRESHOLD (85), and in gap mode even higher.

So a case like “RSI 9.8” can still produce no alert if, for example, it’s exhausted, not deep ITM, volume filter fails, or score stays below threshold.

If you share one exact timestamped row/log snapshot, I can tell you the most likely blocking gate in that specific case.

**User:**
[Snapshot Shared]

**Cursor:**
That snapshot is a strong candidate, but it still fails your hard PE filters.

Most likely blocker is this one:
* Spot = 23827.95, PE strike = 23850
* Distance = +22.05 points only
* Your PE deep-ITM rule needs about spot + 100 (NORMAL_ITM_DISTANCE = 100)
* So this contract is not deep ITM enough, and gets rejected before alert.

Also possible secondary blocker:
* RSI 24.5 can be treated as exhaustion depending on recent RSI window (if it stayed below PE trigger too long).
* So yes, even with RSI 24.5, Trend RED, PCR 2.842, no alert is expected under current rules.
