# =====================================================================
# SYSTEM CONFIGURATION — Single Source of Truth
# All thresholds, constants, and limits belong here.
# Never hardcode values in engine files.
# =====================================================================

# ---------------------------------------------------------------------
# EXECUTION MODE
# ---------------------------------------------------------------------
ENABLE_ORDER_EXECUTION: bool = False  # True = live Dhan orders; False = simulation
TEST_MODE_INTERACTIVE: bool = False  # True = Route order to Test.py for manual confirm
ENABLE_PDB_PAUSE_AFTER_SIGNAL: bool = False

# ---------------------------------------------------------------------
# TRADE PARAMETERS
# ---------------------------------------------------------------------
TARGET_POINTS: float = 60.0
INITIAL_SL_POINTS: float = 15.0
DEPLOYED_CAPITAL: float = 300000.0
MARGIN_REQUIREMENT_PCT: float = 0.12
BACKTEST_SLIPPAGE_PCT: float = 0.01  # 1% premium penalty to model entry latency/jumps

# ---------------------------------------------------------------------
# DIRECTIONAL TOGGLES
# ---------------------------------------------------------------------
ENABLE_CE_TRADES: bool = True  # Master switch for Call options
ENABLE_PE_TRADES: bool = True  # Master switch for Put options

# ---------------------------------------------------------------------
# LOT SIZES (Updated to current NSE/BSE specifications)
# ---------------------------------------------------------------------
LOT_SIZES: dict = {
    "NIFTY": 65,
    "BANKNIFTY": 30,
    "FINNIFTY": 60,
    "SENSEX": 20,
    "RELIANCE": 20,
}
DEFAULT_LOT_SIZE: int = 25

# ---------------------------------------------------------------------
# INDICATOR ENGINE CONSTANTS
# ---------------------------------------------------------------------
EMA_FAST: int = 9
EMA_SLOW: int = 20
VOLUME_EMA_PERIOD: int = 20
ADX_CHOP_THRESHOLD: float = 22.0  # Below this the market is classified as chop/sideways

# ---------------------------------------------------------------------
# RSI TRIGGERS & BANDS
# Conformed precisely to your strict 65 breakout setup.
# ---------------------------------------------------------------------
CE_RSI_TRIGGER: float = 65.0  # Synced to your strict breakout rule (was 63.0)
PE_RSI_TRIGGER: float = 41.0
CE_RSI_MIN: float = CE_RSI_TRIGGER  # Lower boundary of CE RSI band
CE_RSI_MAX: float = 90.0  # Overbought ceiling for CE band alerts
PE_RSI_MIN: float = 10.0  # Oversold floor for PE band alerts
PE_RSI_MAX: float = PE_RSI_TRIGGER  # Upper boundary of PE RSI band
BASE_RSI_POINTS: int = 10  # Points awarded per RSI alignment in scoring

# ---------------------------------------------------------------------
# RISK ENGINE
# ---------------------------------------------------------------------
GAP_RISK_THRESHOLD: int = 100  # Index pts gap between prev close and open to flag gap
RISK_CONFIDENCE_BASE: int = 65  # Minimum score when PnL >= 0
RISK_CONFIDENCE_RED: int = 75  # Minimum score when PnL < 0 (tighter filter)
PANIC_LOT_MULTIPLIER: float = 0.5  # Size reduction in panic / high VIX regime
ACCEL_LOT_MULTIPLIER: float = 1.5  # Size increase in high-confidence trend acceleration

# ---------------------------------------------------------------------
# MARKET SCANNER & PIPELINE CORE
# ---------------------------------------------------------------------
UNDERLYING: str = "NIFTY"
STRIKE_RANGE: int = 3
SENSEX_CHAIN_ENABLED: bool = False
SENSEX_UNDERLYING: str = "SENSEX"
SENSEX_STRIKE_RANGE: int = 3
STATE_FILE: str = "scanner_state.json"
EXECUTION_SCRIPT: str = "MainEngine.py"
MIN_BARS: int = 2
SYNC_EXCEL_LTP: bool = True
CLEAN_INVALID_WS_ROWS: bool = True
AUTO_STRIKE_WS_ROWS: bool = True

STRIKE_SHEET_REFRESH_SEC: int = 90
INTRADAY_CACHE_SEC: int = 45
MUTE_RELEASE_SEC: int = 600

# ---------------------------------------------------------------------
# OPTION STRATEGY SCORING & FILTERS
# ---------------------------------------------------------------------
STRONG_BUY_THRESHOLD: int = 110
BUY_THRESHOLD: int = 95
WATCHLIST_THRESHOLD: int = 80
MIN_PREMIUM_THRESHOLD: float = 10.0
TACTICAL_LOOKBACK: int = 15
EXHAUSTION_WINDOW: int = 30
PE_EXHAUSTION_WINDOW: int = 15
MAX_NIFTY_DROP: float = 100.0
NIFTY_DROP_WINDOW: int = 30
PCR_BULLISH: float = 1.15
PCR_BEARISH: float = 0.85
NORMAL_ITM_DISTANCE: int = 0
GAP_ITM_DISTANCE: int = 0
OI_CHANGE_ALERT_PCT: float = 20.0
OTM_OFFSET_POINTS: int = 100  # Distance from ATM for OTM strangle legs
