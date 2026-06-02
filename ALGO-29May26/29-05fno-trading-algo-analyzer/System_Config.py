# =========================================================
# SYSTEM CONFIGURATION
# =========================================================

# MainEngine Config
ENABLE_ORDER_EXECUTION = False  # True = live Dhan orders; False = simulation
TEST_MODE_INTERACTIVE = True    # True = Route order to Test.py and wait for manual confirm
ENABLE_PDB_PAUSE_AFTER_SIGNAL = False
TARGET_POINTS = 300.0
INITIAL_SL_POINTS = 15.0

# Market_Scanner Config
UNDERLYING = "NIFTY"
STRIKE_RANGE = 3
# BSE index option chain → Websocket.xlsx (BFO rows) + OI/volume from REST chain
SENSEX_CHAIN_ENABLED = False
SENSEX_UNDERLYING = "SENSEX"
SENSEX_STRIKE_RANGE = 3
STATE_FILE = "scanner_state.json"
EXECUTION_SCRIPT = "MainEngine.py"
MIN_BARS = 2
SYNC_EXCEL_LTP = True
CLEAN_INVALID_WS_ROWS = True
AUTO_STRIKE_WS_ROWS = True
STRIKE_SHEET_REFRESH_SEC = 90
INTRADAY_CACHE_SEC = 45
MUTE_RELEASE_SEC = 600

# Option Strategy Core Config
STRONG_BUY_THRESHOLD = 85
TACTICAL_LOOKBACK = 15
EXHAUSTION_WINDOW = 30
PE_EXHAUSTION_WINDOW = 15
MAX_NIFTY_DROP = 100.0       
NIFTY_DROP_WINDOW = 30       
PCR_BULLISH = 1.15
PCR_BEARISH = 0.85
NORMAL_ITM_DISTANCE = 100
GAP_ITM_DISTANCE = 150
OI_CHANGE_ALERT_PCT = 20.0
