# Algo Trading Coding Standards

Please maintain these coding standards strictly at all times.

## 1. File & Module Rules
- One file = one responsibility.
- Python files should ideally remain under 500 lines of code (LOC).
- Files must expose functions/classes — not behave like scripts. No file should directly execute trading logic on import.
- Never call Python files using `os.system()`.
- Use consistent file naming: `snake_case.py` (e.g., `indicator_engine.py`, `risk_engine.py`). Avoid "god files".

## 2. Function Rules
- Functions should ideally remain between 30 to 40 LOC.
- If a function exceeds 80 LOC, split it.
- Function naming rule: `snake_case`, <= 20 chars.
- Max nesting depth = 3.

## 3. Variable & Typing Rules
- Variable names: Short but meaningful (Recommended: 3–15 chars). Use `snake_case` everywhere.
- Avoid global variables.
- All constants/configs must remain in `config.py` (or `system_config.py`).
- Use type hints wherever possible.

## 4. Architecture & Engine Rules
- Every engine must support the standard lifecycle hooks: `init()`, `start()`, `stop()`, `health_check()`.
- Use queues for inter-engine communication.
- Strategy engine must not place orders directly.
- OMS engine must not generate signals.
- Side utilities (Excel, Telegram, DB) must run asynchronously.
- Keep `main.py` minimal.

## 5. Performance & Safety Rules
- Avoid pandas in live tick execution path. Keep execution path latency optimized at all times.
- No blocking IO in execution spine.
- Use rolling memory buffers only.
- No duplicate indicator logic across modules.
- Use `logger` instead of `print()`.
- No silent exception handling.

## 6. Main.py Rules (Institutional Standard)
- `main.py` should ideally be < 150 lines.
- It should ONLY:
  - initialize
  - connect modules
  - start workers
  - monitor health

## 7. OMS Latency & Zero-Blocking Rules
- Never use blocking sleep (`time.sleep()`) in the main event or OMS execution loops.
- Use asynchronous non-blocking API calls for order placement and status checks.
- Offload non-critical OMS logging/I/O to background threads or queues.
- Execution latency takes precedence: OMS core must react instantly to signals without waiting for network confirmations from unrelated components.

## 8. Third-Party Files
- `Dhan_Tradehull.py` is a broker-supplied API file. Do NOT change it ever. It is strictly off-limits. Fix the project files first.

## 9. Option Specifications
- NIFTY options default quantity / lot size must always be set to 75. Ensure this is consistently used in scripts and validations.
