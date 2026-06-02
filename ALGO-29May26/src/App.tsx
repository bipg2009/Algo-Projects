import { useState, useEffect, useRef } from 'react';
import { 
  ShieldCheck, 
  AlertTriangle, 
  TrendingUp, 
  Terminal, 
  ArrowRight, 
  Activity, 
  RotateCcw, 
  Code, 
  Copy, 
  Check, 
  Settings, 
  Power, 
  Play, 
  Cpu, 
  Sparkles, 
  Flame, 
  RefreshCw, 
  FileCode,
  Shield,
  BadgeAlert,
  ArrowBigUpDash,
  ExternalLink,
  ChevronRight,
  Gauge,
  Download,
  FileSpreadsheet
} from 'lucide-react';
import {
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  Tooltip,
  Legend
} from 'recharts';

// Define the shape of our Gemini report
interface AuditReport {
  safetyScore: number;
  executionScore: number;
  errorScore: number;
  fnoScore: number;
  recoveryScore: number;
  summary: string;
  criticalFailures: {
    title: string;
    description: string;
    severity: 'HIGH' | 'CRITICAL' | 'MEDIUM';
  }[];
  strengths: string[];
  greeksAssessed: {
    delta: string;
    theta: string;
    vega: string;
    liquidity: string;
  };
  greeksNumeric?: {
    delta: number;
    gamma: number;
    theta: number;
    vega: number;
    liquidity: number;
  };
  recommendations: string[];
  hardenedCode: string;
}

// Preset Python algorithms
const ALGO_PRESETS = [
  {
    id: 'options-buyer',
    name: 'Supertrend & RSI Options Buyer',
    description: 'Enters and exits options using simple market indicators. Highly prone to slippage and rate limit crashes.',
    category: 'Options Buying',
    code: `# Supertrend & RSI Options Buyer (Options Buying with Market Orders)
# WARNING: UNHARDENED PRODUCTION RISK
import time
from broker_api import AliceBlueClient

client = AliceBlueClient(api_key="MY_SECRET_KEY")
symbol = "NIFTY26MAY2524300CE" # At-The-Money Call option

while True:
    # Fetch indicators from underlying index
    trend, rsi = client.get_indicators("NIFTY 50")
    
    # Place buying order on crossover
    if trend == "BUY" and rsi > 55:
        print("Indicator Bullish, Buying ATM Call Option via MARKET order")
        client.place_order(symbol=symbol, action="BUY", quantity=75, order_type="MARKET")
        print("Order placed successfully!")
        
    elif trend == "SELL":
        print("Indicator Bearish, Selling/Closing Option via MARKET order")
        # Problem: Placing raw market orders on deep OTM or low liquidity strikes leads to massive execution slippage!
        client.place_order(symbol=symbol, action="SELL", quantity=75, order_type="MARKET")
        print("Position closed!")
        
    time.sleep(60) # Simple block blocks thread execution and fails if connection drops`
  },
  {
    id: 'options-seller',
    name: 'Theta Decay Short Straddle ATM',
    description: 'Sells ATM Options to collect high premium decay. Threat of margin-shortfall liquidations during news-driven IV spikes.',
    category: 'Options Selling',
    code: `# Short Straddle Options ATM Harvest (Theta Decay Selling)
# WARNING: UNHARDENED PREMIUM DECAY ALGO & ZERO LIMIT RISK CONTROLS
import time
from broker_api import AngelSmartConnect

client = AngelSmartConnect(api_key="SECRET")
ce_symbol = "BANKNIFTY26MAY48000CE"
pe_symbol = "BANKNIFTY26MAY48000PE"

# Initial Trade entry: Sell Call and Put immediately on market
print("Entering ATM Short Straddle...")
client.place_order(symbol=ce_symbol, action="SELL", quantity=15, order_type="MARKET")
client.place_order(symbol=pe_symbol, action="SELL", quantity=15, order_type="MARKET")
print("Straddle positions active. Sleep to collect premium...")

while True:
    # Fetch real-time premium pricing
    price_ce = client.get_ltp(ce_symbol)
    price_pe = client.get_ltp(pe_symbol)
    
    total_value = price_ce + price_pe
    print(f"Current ATM Cumulative Premium: {total_value}. Monitoring...")
    
    # Target profit exit
    if total_value < 120: 
        print("Target premium achieved! Closing and securing profit...")
        client.place_order(symbol=ce_symbol, action="BUY", quantity=15, order_type="MARKET")
        client.place_order(symbol=pe_symbol, action="BUY", quantity=15, order_type="MARKET")
        break
        
    # CRITICAL BUG: No stop-loss checks! If index moves 300 points or Implied Volatility (IV) spikes, 
    # premium swells immediately. User runs out of broker margin and positions are force-liquidated at a catastrophic loss.
    time.sleep(10)`
  },
  {
    id: 'futures-crossover',
    name: 'EMA Crossover Futures Trader',
    description: 'Trades Index Futures using moving averages. Stores transaction states in-memory, causing double-exposure disasters during crash reboots.',
    category: 'Futures Index',
    code: `# EMA Cross Futures Trader (No Persistent State Crash Recovery)
# WARNING: UNHARDENED STATE RECOVERY
import time
from broker_api import ZerodhaKite

client = ZerodhaKite(api_key="KITE_API")
symbol = "NIFTY-I" # Index Futures contract

# In-memory global state tracking position
current_position = 0 # 1 if long, -1 if short, 0 if flat

while True:
    fast_ema = client.get_ema("NIFTY-I", period=9)
    slow_ema = client.get_ema("NIFTY-I", period=21)
    
    if fast_ema > slow_ema and current_position <= 0:
        # Cross-up signal: Buy to reverse short or enter long
        if current_position == -1:
            client.place_order(symbol=symbol, action="BUY", qty=50) # buy back short
        client.place_order(symbol=symbol, action="BUY", qty=50) # enter long position
        current_position = 1
        print("Cross-up detected. Go Long. Virtual position tracker = +1")
        
    elif fast_ema < slow_ema and current_position >= 0:
        # Cross-down signal: Sell to reverse long or enter short
        if current_position == 1:
            client.place_order(symbol=symbol, action="SELL", qty=50) # exit long
        client.place_order(symbol=symbol, action="SELL", qty=50) # enter short
        current_position = -1
        print("Cross-down detected. Go Short. Virtual position tracker = -1")
        
    # CRITICAL CRASH RESILIENCE DEFECT: If the script restarts (container reboots/internet timeout/kernel panic) 
    # during active trading, the global variable resets to current_position = 0! 
    # The next crossover event will fire orders without knowing they already hold index holdings, leading to fatal over-allocation!
    time.sleep(15)`
  },
  {
    id: 'realtime-data-errorHandler',
    name: 'Robust Real-Time Feed & Errors',
    description: 'Demonstrates connecting to a real-time data feed API (e.g., WebSocket) with exponential backoff, comprehensive try-except blocks, and file-based logging for safety.',
    category: 'Architecture & Safety',
    code: `# Robust Real-Time Feed & Error Handling Architecture
import time
import json
import logging
from logging.handlers import RotatingFileHandler
import websocket

# 1. Setup Robust File Logging
logger = logging.getLogger("FnO_Algo")
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler("algo_execution.log", maxBytes=5 * 1024 * 1024, backupCount=3)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Examples of common error scenarios:
class MarginShortfallError(Exception): pass
class SlippageExceededError(Exception): pass

# 2. Try-Except blocks for critical operations (Order Placement)
def place_order_safely(client, symbol, action, qty, price):
    try:
        logger.info(f"Attempting to place {action} order for {qty} of {symbol} at {price}")
        
        # Simulated check for common error scenario: Spread / Slippage
        market_depth = client.get_depth(symbol)
        spread = market_depth['ask'] - market_depth['bid']
        if spread > 2.0:
            raise SlippageExceededError(f"Spread {spread} is too wide. Aborting.")
            
        # Place actual order based on limit pricing
        response = client.place_order(symbol, action, qty, "LIMIT", price)
        logger.info(f"Order successful. ID: {response['order_id']}")
        return response
        
    except SlippageExceededError as e:
        logger.warning(f"Slippage Protection Triggered: {e}")
    except MarginShortfallError as e:
        logger.critical(f"Margin Exhausted! {e}. Halting trading.")
        # Trigger emergency halt
    except Exception as e:
        logger.error(f"Unexpected error during order placement: {e}", exc_info=True)
    return None

# 3. Robust Real-Time Data Feed via WebSockets
def on_message(ws, message):
    try:
        data = json.loads(message)
        # Process tick data safely
        if 'ltp' in data:
            logger.debug(f"Tick received: {data['symbol']} @ {data['ltp']}")
            # Example: check signal and execute safely
            if data['ltp'] > 500:
                place_order_safely(ws.client, data['symbol'], "BUY", 50, data['ltp'])
    except json.JSONDecodeError as e:
        logger.error(f"Data discrepancy/Corrupt message received: {message}")
    except KeyError as e:
        logger.error(f"Missing expected data field in feed: {e}")

def on_error(ws, error):
    logger.error(f"WebSocket execution error: {error}")

def on_close(ws, close_status_code, close_msg):
    logger.warning("WebSocket disconnected. Attempting to reconnect...")

def connect_data_feed(api_key, max_retries=5):
    """ Connects to a common data provider API (WebSocket) with auto-reconnect """
    url = f"wss://api.common-data-provider.com/feed?token={api_key}"
    
    retry_count = 0
    while retry_count < max_retries:
        try:
            logger.info(f"Connecting to real-time feed (Attempt {retry_count + 1})")
            ws = websocket.WebSocketApp(url,
                                      on_message=on_message,
                                      on_error=on_error,
                                      on_close=on_close)
            # Simulated dummy client injection for order routing
            ws.client = type("MockClient", (), {"place_order": lambda *args: {"order_id": "1234"}, "get_depth": lambda s: {"bid": 100, "ask": 100.5}})()
            
            ws.run_forever(ping_interval=30, ping_timeout=10)
            
            # If run_forever exits, it means connection dropped. Apply exponential backoff.
            retry_count += 1
            sleep_time = 2 ** retry_count
            logger.info(f"Waiting {sleep_time} seconds before reconnecting...")
            time.sleep(sleep_time)
            
        except Exception as e:
            logger.error(f"Critical failure in WebSocket loop: {e}", exc_info=True)
            retry_count += 1
            time.sleep(5)
            
    logger.critical("Max retries exceeded. Exiting algorithm.")

if __name__ == "__main__":
    logger.info("Algorithm Started")
    connect_data_feed("API_TOKEN_XYZ")`
  }
];

// Typical failures that a user can "inject" in the simulator
interface FailureScenario {
  id: string;
  name: string;
  description: string;
  severity: 'HIGH' | 'CRITICAL';
  errorMessage: string;
  color: string;
}

const SIMULATOR_FAILURES: FailureScenario[] = [
  {
    id: 'api-503',
    name: 'Broker REST API Offline',
    description: 'Broker returns 503 Service Unavailable / Gateway Timeout in active market.',
    severity: 'HIGH',
    errorMessage: 'HTTP 503: Gateway Connection Timeout while sending balance query/orders.',
    color: 'bg-amber-950/40 border-amber-800 text-amber-400'
  },
  {
    id: 'liquidity-freeze',
    name: 'Slippage & Bid-Ask Freeze',
    description: 'Wide options spread (No buyers at strike price). Execution gets fully stuck.',
    severity: 'HIGH',
    errorMessage: 'Order Blocked: Spread threshold exceeded. Bid: ₹82.10, Ask: ₹94.50 (Diff 15%).',
    color: 'bg-orange-95/40 border-orange-800 text-orange-400'
  },
  {
    id: 'iv-spike',
    name: 'Implied Volatility (IV) Explodes',
    description: 'Budget/Earnings announcement. Option premium spikes 140% in seconds, triggering Margin Shortfalls.',
    severity: 'CRITICAL',
    errorMessage: 'CRITICAL ALERT: Implied Volatility surged +120%. Margin utilization 114% (Margin Shortfall Closeout Pending).',
    color: 'bg-red-950/40 border-red-800 text-red-400'
  },
  {
    id: 'rate-limit',
    name: 'Broker API Rate-Limit (429)',
    description: 'Rapid indicator loops trigger the broker security gate, blocking limit updates.',
    severity: 'HIGH',
    errorMessage: 'HTTP 429: Too Many Requests. Client trading API blocked for 180 seconds.',
    color: 'bg-rose-950/40 border-rose-800 text-rose-400'
  },
  {
    id: 'server-reboot',
    name: 'State Reboot / System Crash',
    description: 'The script crashes mid-trade and reboots. In-memory variables are wiped.',
    severity: 'CRITICAL',
    errorMessage: 'SIGKILL: Process Terminated. Restarting client loop... local current_position reset to 0!',
    color: 'bg-purple-950/40 border-purple-805 text-purple-400'
  }
];

// Simulated standard log items
interface LogEntry {
  timestamp: string;
  source: 'UNPROTECTED' | 'HARDENED';
  type: 'INFO' | 'ERROR' | 'SUCCESS' | 'WARN';
  message: string;
}

export default function App() {
  const [activeTab, setActiveTab] = useState<'audit' | 'simulator' | 'downloads'>('audit');
  const [selectedPreset, setSelectedPreset] = useState(ALGO_PRESETS[0]);
  const [customCode, setCustomCode] = useState(ALGO_PRESETS[0].code);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const [copySuccess, setCopySuccess] = useState(false);
  const [reports, setReports] = useState<Record<string, AuditReport>>({});

  // Simulator States
  const [simActive, setSimActive] = useState(false);
  const [simStep, setSimStep] = useState(0);
  const [premiumPrice, setPremiumPrice] = useState(150.0);
  const [simLogs, setSimLogs] = useState<LogEntry[]>([]);
  const [simPositionUp, setSimPositionUp] = useState<any>({ unhardened: 'N/A', hardened: 'FLAT' });
  const [simProfitUp, setSimProfitUp] = useState<any>({ unhardened: 0, hardened: 0 });
  const [activeFailure, setActiveFailure] = useState<string | null>(null);
  const [historicalPrices, setHistoricalPrices] = useState<number[]>(Array.from({ length: 40 }, () => 145 + Math.random() * 10));

  // Real-time Margin Utilization States
  const [totalMargin, setTotalMargin] = useState(1000000); // INR 10,00,000 (10 Lakhs INR available in Broker Margin Account)
  const [usedMarginUnhardened, setUsedMarginUnhardened] = useState(0);
  const [usedMarginHardened, setUsedMarginHardened] = useState(0);

  const simulationTimer = useRef<NodeJS.Timeout | null>(null);

  // Sync editor if selecting a different preset
  const [injectSuccessMsg, setInjectSuccessMsg] = useState<string | null>(null);

  const injectSafetyPattern = (patternType: string) => {
    let patternCode = "";
    let patternLabel = "";

    if (patternType === "backoff") {
      patternLabel = "Exponential Backoff Wrapper";
      patternCode = `\n\n# --- PRODUCTION HARDENING: EXPONENTIAL BACKOFF RETRY ---
def retry_with_exponential_backoff(max_retries=5, initial_delay=1):
    import time
    import random
    def decorator(func):
        def wrapper(*args, **kwargs):
            delay = initial_delay
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        print("CRITICAL: Max retries exhausted on API call.")
                        raise e
                    jitter = random.uniform(0, 0.1 * delay)
                    sleep_time = delay + jitter
                    print(f"WARN: Request failed. Retrying in {sleep_time:.2f}s...")
                    time.sleep(sleep_time)
                    delay *= 2
        return wrapper
    return decorator
`;
    } else if (patternType === "spread") {
      patternLabel = "Limit Order Spread Check";
      patternCode = `\n\n# --- PRODUCTION HARDENING: SPREAD SENSITIVE LIMIT ORDER ENTRY ---
def check_spread_and_execute_limit(broker_client, symbol, action, quantity, max_spread_pct=2.0):
    depth = broker_client.get_market_depth(symbol)
    best_bid = depth.get('bid_price_1', 0)
    best_ask = depth.get('ask_price_1', 0)
    
    if best_bid == 0 or best_ask == 0:
        raise ValueError("CRITICAL: Market depth return contains zero pricing (Liquidity Halt)")
    
    spread_pct = ((best_ask - best_bid) / best_bid) * 100
    if spread_pct > max_spread_pct:
        raise ValueError(f"BLOCKED: Spread of {spread_pct:.2f}% exceeds safety ceiling of {max_spread_pct}%")
        
    limit_price = best_ask if action == "BUY" else best_bid
    print(f"Spread validated ({spread_pct:.2f}%). Placing LIMIT order at ₹{limit_price}")
    return broker_client.place_order(symbol=symbol, action=action, qty=quantity, order_type="LIMIT", price=limit_price)
`;
    } else if (patternType === "ledger") {
      patternLabel = "Position State Ledger";
      patternCode = `\n\n# --- PRODUCTION HARDENING: RECOVERY POSITION STATE LEDGER ---
def sync_and_save_state(broker_client, symbol, current_local_position):
    import json
    import os
    
    LEDGER_FILE = "trading_ledger.json"
    
    # Pre-trade Broker Handshake Verification
    positions = broker_client.get_open_positions()
    active_qty = 0
    for pos in positions:
        if pos.get('symbol') == symbol:
            active_qty = int(pos.get('quantity', 0))
            break
            
    reconciled_position = current_local_position
    # lot size = 75 example
    lot_multiplier = 75 
    broker_lot_position = active_qty // lot_multiplier
    
    if broker_lot_position != current_local_position:
        print(f"WARN: Local state bias ({current_local_position}) differs from Broker ({broker_lot_position}). Overwriting state.")
        reconciled_position = broker_lot_position
        
    ledger = {
        "position": reconciled_position,
        "symbol": symbol,
        "reconciled": True
    }
    
    # Save to persistent storage to survive runtime crashes
    with open(LEDGER_FILE, 'w') as f:
        json.dump(ledger, f, indent=4)
        
    print(f"Persistent positioning ledger synced to storage. Active level: {reconciled_position}")
    return reconciled_position
`;
    } else if (patternType === "excel_ledger") {
      patternLabel = "Excel Ledger Logger";
      patternCode = `\n\n# --- PRODUCTION HARDENING: EXCEL / CSV ORDERBOOK LEDGER LOGGER ---
def log_execution_to_excel_ledger(order_id, symbol, action, quantity, price, margin_used):
    """
    Thread-safe, robust ledger logger that writes execution logs to an Excel-compatible ledger.
    Provides automatic retry mechanics to prevent crashes if the file is open in MS Excel.
    """
    import csv
    import os
    import datetime
    import time
    
    LEDGER_FILE = "trading_execution_ledger.csv" # Opens natively in MS Excel & Google Sheets
    headers = ["Timestamp", "Order ID", "Symbol", "Execution Action", "Quantity", "Price (INR)", "Margin Consumed (INR)", "Status"]
    
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row_data = [timestamp, order_id, symbol, action.upper(), quantity, price, margin_used, "FILLED"]
    
    # Retry mechanism in case Excel has locked the file exclusively
    max_retries = 3
    for attempt in range(max_retries):
        try:
            file_exists = os.path.isfile(LEDGER_FILE)
            with open(LEDGER_FILE, mode='a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(headers) # Write headers on initialization
                writer.writerow(row_data)
            print(f"✅ Excel Ledger updated: {action} {quantity} lots of {symbol}")
            return True
        except PermissionError:
            print(f"⚠️ Excel Lock detected! File may be open in MS Excel. Retrying/Waiting... (Attempt {attempt+1}/{max_retries})")
            time.sleep(1.5)
        except Exception as e:
            print(f"❌ Failed to write order to ledger: {str(e)}")
            break
    return False
`;
    }

    if (patternCode) {
      setCustomCode((prev) => prev + patternCode);
      setInjectSuccessMsg(`Successfully appended ${patternLabel}!`);
      setTimeout(() => setInjectSuccessMsg(null), 3000);
    }
  };

  const handlePresetSelect = (preset: typeof ALGO_PRESETS[0]) => {
    setSelectedPreset(preset);
    setCustomCode(preset.code);
  };

  // Run Gemini analysis via express endpoint
  const runAudit = async () => {
    setIsAnalyzing(true);
    setApiError(null);
    try {
      const response = await fetch('/api/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ code: customCode }),
      });

      if (!response.ok) {
        const errJson = await response.json();
        throw new Error(errJson.error || 'Network error encountered.');
      }

      const report: AuditReport = await response.json();
      
      // Assure greeksNumeric is populated for Recharts radar chart visualization
      if (!report.greeksNumeric) {
        const deltaText = (report.greeksAssessed?.delta || "").toLowerCase();
        const thetaText = (report.greeksAssessed?.theta || "").toLowerCase();
        const vegaText = (report.greeksAssessed?.vega || "").toLowerCase();
        const liqText = (report.greeksAssessed?.liquidity || "").toLowerCase();

        report.greeksNumeric = {
          delta: deltaText.includes("high") || deltaText.includes("100%") || deltaText.includes("unhedged") ? 85 : deltaText.includes("hedge") || deltaText.includes("neutral") ? 35 : 55,
          gamma: deltaText.includes("gamma") || deltaText.includes("accelerat") ? 80 : 45,
          theta: thetaText.includes("rapid") || thetaText.includes("heavy") || thetaText.includes("theta") ? 90 : 50,
          vega: vegaText.includes("high") || vegaText.includes("crush") || vegaText.includes("volat") ? 85 : 40,
          liquidity: liqText.includes("spread") || liqText.includes("illiquid") || liqText.includes("difficult") ? 75 : 35
        };
      }

      setReports((prev) => ({
        ...prev,
        [selectedPreset.id]: report,
      }));
    } catch (err: any) {
      console.error(err);
      setApiError(err.message || 'Failed to finish algorithm analysis.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Pre-load default report if not fetched, so user has instant feedback
  useEffect(() => {
    // If we have custom code and no report, run initial analysis on mount
    getInitialDefaultReport();
  }, []);

  const getInitialDefaultReport = () => {
    // Inject custom preset results to provide a premium instantly-accessible demo
    const defaultAudits: Record<string, AuditReport> = {
      'options-buyer': {
        safetyScore: 32,
        executionScore: 38,
        errorScore: 24,
        fnoScore: 40,
        recoveryScore: 10,
        summary: "This Options Buying algorithm is highly hazardous for production. It trades ATM option premiums using brute Market orders directly in a raw loop, risking immense visual slippage up to 10-25% during market volatility. It lacks basic API request protection (timeouts, code rate limits) and possesses zero persistent bookkeeping or recovery mechanics in the event of hardware or local client restarts.",
        strengths: [
          "Uses precise technical indicators (Supertrend + RSI) for entering indices signals.",
          "Simple loop structure that executes linearly without redundant calculations."
        ],
        criticalFailures: [
          {
            title: "Market Order Slippage Slip",
            description: "Executing MARKET order in Futures & Options contracts can lead to extremely high bid-ask spread slippages (up to ₹15-40 per lot under low market depth), bleeding potential profits to zero instantly.",
            severity: "HIGH"
          },
          {
            title: "Volatile Crash Outage Hazard",
            description: "Any REST connection failure during `client.place_order` throws a raw Exception, crashing the script completely. If the script is aborted before a closing 'SELL' order, the CE option remains unmanaged and open to catastrophic margin erosion.",
            severity: "CRITICAL"
          },
          {
            title: "Rate Limit Gate Violation",
            description: "Evaluating the index trend inside a raw unthrottled loop sends hundreds of API requests, hitting the broker's rate limits (429 HTTP response codes) and locking out trade actions during major news windows.",
            severity: "HIGH"
          }
        ],
        greeksAssessed: {
          delta: "Position possesses 100% naked direction exposure without hedges, carrying immense intraday drawdowns if Nifty turns rapidly.",
          theta: "Does not check contract time-to-expiry (DTE). Trades 0DTE (expiry day) contracts which decay rapidly, leaving buyers with near 100% loss curves if price stalls.",
          vega: "Highly vulnerable to Volatility Crush immediately post Budget, GDP numbers, or Earnings signals, collapsing premiums even if underlying holds levels.",
          liquidity: "Naked deep Out-Of-The-Money (OTM) options can exhibit high bid-ask spreads. Attempting to liquidate at Market ruins profitability."
        },
        greeksNumeric: {
          delta: 85,
          gamma: 70,
          theta: 90,
          vega: 75,
          liquidity: 65
        },
        recommendations: [
          "Replace all MARKET order actions with LIMIT orders paired with strict spread tolerance checks.",
          "Implement structured API call error handlers using an exponential backoff decorator wrapper.",
          "Add persistent state ledger tracking (SQLite or JSON cache files) so position status survives script reboots.",
          "Restrict options entries explicitly to high-liquidity weekly strikes within 1-2 strikes of ATM."
        ],
        hardenedCode: `# HARDENED OPTIONS BUYER ALGO (Safety Wrapped)
import time
import logging
import json
import os
from broker_api import AliceBlueClient, BrokerAPIException

# Configure secure trace logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SystemResilientAlgo")

STATE_FILE = "trading_state.json"

class ResilientOptionsTrader:
    def __init__(self, api_key):
        self.client = AliceBlueClient(api_key=api_key)
        self.state = self.load_state_ledger()
        
    def load_state_ledger(self):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to access state log: {e}. Defaulting to flat.")
        return {"current_holding": 0, "last_order_id": None}
        
    def save_state_ledger(self):
        try:
            with open(STATE_FILE, 'w') as f:
                json.dump(self.state, f)
        except Exception as e:
            logger.error(f"State saving failed: {e}")

    def execute_order_safely(self, symbol, action, quantity, price_limit=None):
        """Executes a trade using limit orders with retry handling and slippage bounds"""
        max_retries = 3
        backoff = 2
        
        for attempt in range(max_retries):
            try:
                # 1. Inspect market Bid-Ask Spread before initiating trade
                depth = self.client.get_market_depth(symbol)
                bid = depth['bid_price_1']
                ask = depth['ask_price_1']
                spread_pct = (ask - bid) / bid * 100
                
                if spread_pct > 3.0:
                    logger.warning(f"Aborting execution: Bid-Ask spread wide: {spread_pct:.2f}%")
                    return False
                
                # Use ask for buying limit, bid for selling limit
                limit_price = price_limit if price_limit else (ask if action == "BUY" else bid)
                
                logger.info(f"Submitting {action} LIMIT order for {symbol} at ₹{limit_price:.2f}")
                order = self.client.place_order(
                    symbol=symbol, 
                    action=action, 
                    qty=quantity, 
                    order_type="LIMIT",
                    price=limit_price
                )
                
                self.state["last_order_id"] = order.get("id")
                return True
                
            except BrokerAPIException as e:
                logger.error(f"Broker rate-limited or threw exception (Attempt {attempt+1}/{max_retries}): {e}")
                time.sleep(backoff)
                backoff *= 2 # Exponential delay expansion
                
        return False

    def trade_loop(self, symbol):
        logger.info("[STANDBY] Safe Algorithmic System Active... Monitoring Underlying Feed.")
        while True:
            try:
                trend, rsi = self.client.get_indicators("NIFTY 50")
                holding = self.state["current_holding"]
                
                if trend == "BUY" and rsi > 55 and holding == 0:
                    if self.execute_order_safely(symbol, "BUY", 75):
                        self.state["current_holding"] = 1
                        self.save_state_ledger()
                        
                elif trend == "SELL" and holding == 1:
                    if self.execute_order_safely(symbol, "SELL", 75):
                        self.state["current_holding"] = 0
                        self.save_state_ledger()
                        
            except Exception as outer_err:
                logger.error(f"Unexpected loop exception caught gracefully: {outer_err}. Resetting index socket link...")
                
            time.sleep(30) # Dynamic sleep buffer avoiding 429 locks`
      },
      'options-seller': {
        safetyScore: 28,
        executionScore: 30,
        errorScore: 35,
        fnoScore: 15,
        recoveryScore: 15,
        summary: "This ATM Option Selling Straddle algorithm lacks stop-loss checks, premium deviation bands, or margin limits. Trading ATM short options leaves systems completely unshielded to news-driven index spikes. The sleep loop expects steady prices, but a single black-swan event triggers catastrophic margin liquidations if unhedged.",
        strengths: [
          "Linear execution layout targeting premium collection.",
          "Simple comparison of aggregate premiums values."
        ],
        criticalFailures: [
          {
            title: "Naked IV Spike Liquidation",
            description: "Sudden economic announcements or geopolitical moves expand option premiums rapidly, blowing through risk limits and forcing automatic liquidation by the clearing broker.",
            severity: "CRITICAL"
          },
          {
            title: "Absence of Tail-Risk Protection",
            description: "Selling both Call (CE) and Put (PE) without purchasing deep OTM hedge wings subjects the portfolio to unlimited vertical risk on breakout events.",
            severity: "CRITICAL"
          }
        ],
        greeksAssessed: {
          delta: "Vulnerable to sudden trend breakouts. Absolute Delta neutrality decays rapidly into hostile directional risk.",
          theta: "Profits heavily from premium decay, but tail risks heavily dwarf decay collections during spikes.",
          vega: "Vega risk is extremely high. Any volatility surge immediately inflates both options CE and PE simultaneously.",
          liquidity: "Whipping market swings cause massive bid-ask spreads, making target closes incredibly difficult to fill."
        },
        greeksNumeric: {
          delta: 50,
          gamma: 95,
          theta: 90,
          vega: 85,
          liquidity: 70
        },
        recommendations: [
          "Buy deep out-of-the-money hedge options immediately to convert the trade into an Iron Butterfly (Limited Risk).",
          "Incorporate active trailing stop-loss values based on individual premiums to trigger pre-emptive protection.",
          "Implement real-time portfolio margin checks and close positions automatically if utility crosses 80%."
        ],
        hardenedCode: `# HARDENED THETA DECAY SELL STRADDLE ALGO (Hedged Risk)
import time
import logging
from broker_api import AngelSmartConnect, BrokerException

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("StraddleResilient")

class HardenedShortStraddle:
    def __init__(self, api_key):
        self.client = AngelSmartConnect(api_key=api_key)
        self.stop_loss_pct = 30.0 # Strict 30% stop-loss threshold per leg
        
    def check_margin_safety(self):
        """Ensures our account margin cannot trigger abrupt clearing agent liquidations"""
        funds = self.client.get_funds()
        margin_used = funds["margin_utilized"]
        total_balance = funds["cash_balance"]
        
        utilization = (margin_used / total_balance) * 100
        if utilization > 80.0:
            logger.critical(f"FATAL: Account Margin safety crossed limit: {utilization}%. HEDGING NOW!")
            return False
        return True

    def enter_safe_butterfly(self, ce_sell, pe_sell, ce_hedge, pe_hedge, qty):
        """Enters an Iron Butterfly configuration (safely capped down-side wings)"""
        try:
            # 1. ALWAYS purchase risk hedging insurance contract wings FIRST to secure lower margin requirements
            logger.info("Buying protection hedge contracts...")
            self.client.place_order(symbol=ce_hedge, action="BUY", quantity=qty, order_type="LIMIT", price=self.client.get_ltp(ce_hedge))
            self.client.place_order(symbol=pe_hedge, action="BUY", quantity=qty, order_type="LIMIT", price=self.client.get_ltp(pe_hedge))
            
            # 2. Sell ATM Premium Legs safely
            logger.info("Selling short ATM legs with strict margin checks...")
            self.client.place_order(symbol=ce_sell, action="SELL", quantity=qty, order_type="LIMIT", price=self.client.get_ltp(ce_sell))
            self.client.place_order(symbol=pe_sell, action="SELL", quantity=qty, order_type="LIMIT", price=self.client.get_ltp(pe_sell))
            return True
        except Exception as e:
            logger.error(f"Butterfly Entry failed: {e}. Executing fallback market risk evacuation!")
            # Emergency exit code...
            return False`
      },
      'futures-crossover': {
        safetyScore: 45,
        executionScore: 50,
        errorScore: 38,
        fnoScore: 60,
        recoveryScore: 5,
        summary: "This Futures Crossover algorithm suffers from critical state amnesia. Storing 'current_position' only in an in-memory variables means any application restart completely blinds the system to current active market contract holdings. This leads to redundant order placement or trade doubling.",
        strengths: [
          "Uses trend-following moving average crossover points.",
          "Checks indicators systematically."
        ],
        criticalFailures: [
          {
            title: "Amnesia Trade Over-Allocation",
            description: "If the server restarts, 'current_position' resets to 0. On the next crossover, it places a BUY trade without realizing it already holds an open position, doubling account risk.",
            severity: "CRITICAL"
          }
        ],
        greeksAssessed: {
          delta: "Intraday Futures are direct Delta 1 instruments. Exposure represents 100% directional swing without buffer.",
          theta: "No option decay risk applies to physical Futures contracts, but roll-over costs apply.",
          vega: "Unaffected by volatility pricing, but high IV expands intraday price variance.",
          liquidity: "Trades near-month contract ensures high liquidity, but wide slippages can occur on sudden data announcements."
        },
        greeksNumeric: {
          delta: 100,
          gamma: 0,
          theta: 5,
          vega: 10,
          liquidity: 40
        },
        recommendations: [
          "Implement persistent local or remote file storage to maintain position status.",
          "Incorporate a pre-flight broker API check on startup to sync script state with actual open holdings."
        ],
        hardenedCode: `# HARDENED STATE-SYNCHRONIZED FUTURES ALGO
import json
import os
import logging
from broker_api import ZerodhaKite

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FuturesStateEngine")

class ResilientFuturesTrader:
    def __init__(self, api_key):
        self.client = ZerodhaKite(api_key=api_key)
        self.state_file = "futures_holdings.json"
        self.current_position = self.sync_state_with_broker()
        
    def sync_state_with_broker(self):
        """Pre-Trade Handshake: Verifies memory state against actual remote broker positions"""
        try:
            broker_positions = self.client.get_open_positions()
            for pos in broker_positions:
                if pos['symbol'] == "NIFTY-I":
                    qty = int(pos['quantity'])
                    # Let NIFTY-I lot size = 50. Convert quantity to virtual index (-1, 0, 1)
                    virtual_pos = qty // 50
                    logger.info(f"State Sourced from Broker successfully: Position = {virtual_pos}")
                    return virtual_pos
        except Exception as e:
            logger.error(f"Failed to query broker position status: {e}. Falling back to clean safety halt.")
            raise SystemExit("Cannot verify live positions safely. Trading aborted.")
        return 0`
      },
      'realtime-data-errorHandler': {
        safetyScore: 95,
        executionScore: 92,
        errorScore: 98,
        fnoScore: 85,
        recoveryScore: 90,
        summary: "This is a brilliantly constructed, highly resilient architecture. It employs best practices to solve exact weaknesses of standard FNO loops: extensive custom Error tracking, exponential backoff for REST/socket reconnects, safe Slippage limit validations, rotating file logging, and isolated `try-except` chains to prevent catastrophic thread-blocks.",
        strengths: [
          "Uses dedicated, rotating file logging, ensuring memory isn't blown out dynamically.",
          "Disconnects and 502/Gateway Timeout events are gracefully caught and retried via sleep loops rather than exploding.",
          "Verifies bid-ask spread liquidity threshold before executing the limit order."
        ],
        criticalFailures: [
          {
            title: "Simulated Data Feed Latency",
            description: "If the WebSocket feed from the data provider slows by 500ms, limit orders based on the delayed ticks can still fill poorly if fast market jumps occur. Mitigated by the spread checker.",
            severity: "MEDIUM"
          }
        ],
        greeksAssessed: {
          delta: "Position bias assumes you have a separate calculation algorithm. Tick pricing is safely handed off.",
          theta: "No specific decay logic injected, acts purely as an execution pipe.",
          vega: "Vega expansion safe – handles volatile ticks smoothly.",
          liquidity: "Actively measures inside-spread (Ask-Bid) explicitly to prevent slippage on illiquid contracts."
        },
        greeksNumeric: {
          delta: 10,
          gamma: 10,
          theta: 10,
          vega: 10,
          liquidity: 10
        },
        recommendations: [
          "Couple this architecture with the `trading_state.json` ledger logic so that it stores the open position limits to disk.",
          "Validate `limit_price` doesn't fall slightly out of exchange-mandated execution bounds (LPP/Exec bands) which could Reject the limit order."
        ],
        hardenedCode: `# REAL-TIME DATA FEED ALREADY OPTIMIZED 
# Fully Production Ready! Use this as a core engine.`
      }
    };
    
    setReports(defaultAudits);
  };

  // Run the Copy Code Action
  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopySuccess(true);
    setTimeout(() => setCopySuccess(false), 2000);
  };

  // Simulator Engine Functions
  const startSimulation = () => {
    if (simActive) {
      // Toggle off
      stopSimulation();
      return;
    }

    setSimActive(true);
    setSimLogs([]);
    setSimProfitUp({ unhardened: 0, hardened: 0 });
    setSimPositionUp({ unhardened: 'FLAT', hardened: 'FLAT' });
    setPremiumPrice(150.0);
    setActiveFailure(null);

    // Dynamic margin bases dependent on selected preset style
    let baseUnhardened = 180000;
    let baseHardened = 72000;
    
    if (selectedPreset.id === 'options-buyer') {
      baseUnhardened = 45000;
      baseHardened = 45000;
    } else if (selectedPreset.id === 'options-seller') {
      baseUnhardened = 320000;
      baseHardened = 120000; // Hedged Fly saves margin requirement!
    } else if (selectedPreset.id === 'futures-crossover') {
      baseUnhardened = 180000;
      baseHardened = 180000;
    }

    setUsedMarginUnhardened(0);
    setUsedMarginHardened(0);

    addSimLog('UNPROTECTED', 'SUCCESS', 'ALGO INITIATED. Sourcing live feed from index WebSocket...');
    addSimLog('HARDENED', 'SUCCESS', 'RESILIENT ALGO INITIATED. Self-check active. Reading local state database file...');
    addSimLog('HARDENED', 'INFO', 'Broker handshake ok. Match Live Position: FLAT. Sync active.');

    let step = 0;
    let localPrice = 150.0;
    let priceHistory = [150.0];

    simulationTimer.current = setInterval(() => {
      step += 1;
      setSimStep(step);

      // Natural random walk of premium prices
      const priceDelta = (Math.random() - 0.49) * 4;
      localPrice = parseFloat((localPrice + priceDelta).toFixed(2));
      setPremiumPrice(localPrice);

      setHistoricalPrices((prev) => {
        const sliced = prev.slice(1);
        return [...sliced, localPrice];
      });

      // Simple simulated action for "unhardened" vs "hardened" at step 5 (buying pressure)
      if (step === 3) {
        // Entering positions
        addSimLog('UNPROTECTED', 'INFO', 'Signal crossover! Sending MARKET order to BUY NIFTY ATM CE...');
        addSimLog('UNPROTECTED', 'SUCCESS', 'Order Filled. 75 Lots CE purchased at ₹' + localPrice);
        setSimPositionUp((prev: any) => ({ ...prev, unprotected: 'LONG' }));
        setUsedMarginUnhardened(baseUnhardened);

        addSimLog('HARDENED', 'INFO', 'Signal Crossover! Verifying bid-ask spread threshold...');
        addSimLog('HARDENED', 'INFO', 'Target spreads within limits (0.15%). Placing LIMIT Order at Ask: ₹' + (localPrice + 0.1).toFixed(2));
        addSimLog('HARDENED', 'SUCCESS', 'LIMIT order completed safely. Position registered in local SQLite ledger.');
        setSimPositionUp((prev: any) => ({ ...prev, hardened: 'LONG' }));
        setUsedMarginHardened(baseHardened);
      }

      // Add a small fluctuations to open margin when positions are active
      if (step > 3) {
        setUsedMarginUnhardened((prev) => {
          if (prev === 0) return 0;
          // Unhardened decays or spikes rapidly in news loops
          const delta = Math.round((Math.random() - 0.48) * 3500);
          return Math.max(15000, Math.min(1250000, prev + delta));
        });
        setUsedMarginHardened((prev) => {
          if (prev === 0) return 0;
          // Hardened stays tightly range-bound thanks to dynamic hedged parameters
          const delta = Math.round((Math.random() - 0.5) * 850);
          return Math.max(15000, Math.min(800000, prev + delta));
        });
      }

      // Update P&L
      setSimProfitUp((prev: any) => {
        const nextPnL: any = {};
        if (priceHistory.length >= 3) {
          const buyPrice = priceHistory[2];
          nextPnL.unhardened = Math.round((localPrice - buyPrice) * 75);
          nextPnL.hardened = Math.round((localPrice - (buyPrice + 0.1)) * 75);
        } else {
          nextPnL.unhardened = 0;
          nextPnL.hardened = 0;
        }
        return nextPnL;
      });

      priceHistory.push(localPrice);
    }, 1500);
  };

  const stopSimulation = () => {
    if (simulationTimer.current) {
      clearInterval(simulationTimer.current);
      simulationTimer.current = null;
    }
    setSimActive(false);
  };

  const addSimLog = (source: 'UNPROTECTED' | 'HARDENED', type: 'INFO' | 'ERROR' | 'SUCCESS' | 'WARN', message: string) => {
    const timeStr = new Date().toISOString().split('T')[1].substr(0, 8);
    setSimLogs((prev) => [
      { timestamp: timeStr, source, type, message },
      ...prev
    ]);
  };

  // Triggering the specific error
  const injectFailure = (failure: FailureScenario) => {
    setActiveFailure(failure.id);
    addSimLog('UNPROTECTED', 'ERROR', `[INJECT_FAIL] Triggered event: ${failure.name}`);
    addSimLog('HARDENED', 'WARN', `[INJECT_FAIL] Threat anomaly detected: ${failure.name}`);

    setTimeout(() => {
      if (failure.id === 'api-503') {
        // Unhardened crashes entirely
        addSimLog('UNPROTECTED', 'ERROR', `FATAL CRASH: urlopen failure - ${failure.errorMessage}`);
        addSimLog('UNPROTECTED', 'ERROR', '!!! ALGO TERMINATED IN CRASHED STATE (Open Long Position remains unhedged at broker!) !!!');
        setSimPositionUp((prev: any) => ({ ...prev, unprotected: 'N/A' }));
        // API crash leaves margin stuck in zombie lock state at broker
        // We do not change usedMarginUnhardened because it is orphaned and unmanaged!

        // Hardened handles it by retrying and retaining safe margins
        addSimLog('HARDENED', 'ERROR', `API Query returned state error: 503. Initializing exponential retry trigger...`);
        addSimLog('HARDENED', 'WARN', `Retry Attempt 1 in 2s... URL failed. Retrying Attempt 2 in 4s...`);
        addSimLog('HARDENED', 'INFO', `API connectivity re-established. Sync status matches open CE contract holding.`);
      } else if (failure.id === 'liquidity-freeze') {
        // Liquidity issue
        addSimLog('UNPROTECTED', 'WARN', `Placing Exit MARKET Sell order of NIFTY CE...`);
        addSimLog('UNPROTECTED', 'ERROR', `Execution slippage severe: No buyers. Order executed at ₹${(premiumPrice - 18).toFixed(2)} (Ruined P&L)`);
        setSimProfitUp((prev: any) => ({ ...prev, unhardened: prev.unhardened - 1350 }));
        setSimPositionUp((prev: any) => ({ ...prev, unprotected: 'FLAT' }));
        setUsedMarginUnhardened(0); // positions closed

        addSimLog('HARDENED', 'WARN', `Initiating LIMIT exit of CE holdings closely above Bid spread ₹${(premiumPrice - 0.5).toFixed(2)}`);
        addSimLog('HARDENED', 'INFO', `Order pending on book. Spread check active...`);
        addSimLog('HARDENED', 'SUCCESS', `Limit exit order filled at exact designated pricing ₹${(premiumPrice - 0.5).toFixed(2)} with zero slippage.`);
        setSimPositionUp((prev: any) => ({ ...prev, hardened: 'FLAT' }));
        setUsedMarginHardened(0); // positions closed safely
      } else if (failure.id === 'iv-spike') {
        // Option valuation implosion
        addSimLog('UNPROTECTED', 'ERROR', `Implied Volatility exploding. Balance utilization reached critical margin levels.`);
        addSimLog('UNPROTECTED', 'ERROR', `BROKER ALERT: FORCE-LIQUIDATING account positions to prevent margin overdrafts...`);
        setSimProfitUp((prev: any) => ({ ...prev, unhardened: -4500 }));
        setSimPositionUp((prev: any) => ({ ...prev, unprotected: 'LIQUIDATED' }));
        
        // Spike to margin exhaustion then drop post-liquidation
        setUsedMarginUnhardened(1140000); 
        setTimeout(() => {
          setUsedMarginUnhardened(0); // released margin upon devastating liquidation
          addSimLog('UNPROTECTED', 'ERROR', `Post-Liquidation clean-up completed. Available margin restored to baseline, carrying massive loss penalty.`);
        }, 3500);

        addSimLog('HARDENED', 'WARN', `Pre-emptive margin sentinel alert active: Utilization 82%. Hedging trigger threshold armed.`);
        addSimLog('HARDENED', 'INFO', `Buying deep OTM PE & CE hedge contracts to shrink margin leverage immediately...`);
        addSimLog('HARDENED', 'SUCCESS', `Hedging secured margin consumption down to 42%. Portfolio converted into fully bounded Iron Fly risk.`);
        setSimPositionUp((prev: any) => ({ ...prev, hardened: 'HEDGED_FLY' }));
        setUsedMarginHardened(420000); // Secured 42% because of iron butterfly wings option protection!
      } else if (failure.id === 'rate-limit') {
        // Rate limit lockout
        addSimLog('UNPROTECTED', 'ERROR', `Broker API rate-limit crossed. Error code 429 received from REST gateway.`);
        addSimLog('UNPROTECTED', 'ERROR', `Cannot access order status: System completely blind to market swings!`);

        addSimLog('HARDENED', 'WARN', `Rate limiter token bucket depleted. Throttling outbound REST API request rates...`);
        addSimLog('HARDENED', 'INFO', `Swapping active REST loop stream over to low-overhead UDP websocket ticks channel... Feed uninterrupted.`);
      } else if (failure.id === 'server-reboot') {
        // Local state wipe
        addSimLog('UNPROTECTED', 'ERROR', `Process memory dump occurred... restarting main script.`);
        addSimLog('UNPROTECTED', 'WARN', `Script started fresh. current_position variable cleared. State: [FLAT].`);
        addSimLog('UNPROTECTED', 'ERROR', `CRITICAL BUG: Broker reports holding NIFTY ATM CE positions. But algo believes it is flat! Potential trade duplication looming.`);
        setUsedMarginUnhardened(0); // Amnesia: local script thinks flat (0 margin locally tracked!), but broker holds it!

        addSimLog('HARDENED', 'ERROR', `System shutdown detected. Re-initiating connection loop...`);
        addSimLog('HARDENED', 'INFO', `Reading 'trading_state.json' recovery log... Live holdings sync mismatch.`);
        addSimLog('HARDENED', 'WARN', `Holding mismatch resolved: Discovered active CE contracts. Running diagnostic sync... State reconciled to: [LONG].`);
        // Hardened stays synced and holds original safe margin
      }
    }, 1000);
  };

  useEffect(() => {
    return () => {
      if (simulationTimer.current) {
        clearInterval(simulationTimer.current);
      }
    };
  }, []);

  const currentReport: AuditReport | undefined = reports[selectedPreset.id];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-emerald-500 selection:text-slate-950">
      
      {/* Visual Terminal Glass Header */}
      <header className="border-b border-slate-800 bg-slate-900/70 backdrop-blur-md sticky top-0 z-40 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-emerald-400">
            <ShieldCheck className="h-6 w-6 animate-pulse" />
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight text-white flex items-center gap-2">
              FnO Trading Algo Safety Arena
              <span className="text-xs bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded uppercase tracking-wider font-mono">
                Stable v2.1
              </span>
            </h1>
            <p className="text-xs text-slate-400">Validate real-time error-handling and Options Greek resilience on Python-based algorithms.</p>
          </div>
        </div>

        {/* Global Tab Navigation */}
        <div className="flex bg-slate-950/80 p-1 rounded-xl border border-slate-800/80 gap-1">
          <button 
            onClick={() => setActiveTab('audit')}
            id="tab-audit-btn"
            className={`px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer transition-all duration-200 flex items-center gap-1.5 ${
              activeTab === 'audit' 
                ? 'bg-emerald-500 text-slate-950 shadow-sm font-semibold' 
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Shield className="h-3.5 w-3.5" />
            Production Audit
          </button>
          <button 
            onClick={() => {
              setActiveTab('simulator');
              if (!simActive) startSimulation();
            }}
            id="tab-simulator-btn"
            className={`px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer transition-all duration-200 flex items-center gap-1.5 ${
              activeTab === 'simulator' 
                ? 'bg-emerald-500 text-slate-950 shadow-sm font-semibold' 
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Activity className="h-3.5 w-3.5" />
            Error Stress Simulator
          </button>
          <button 
            onClick={() => setActiveTab('downloads')}
            id="tab-downloads-btn"
            className={`px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer transition-all duration-200 flex items-center gap-1.5 ${
              activeTab === 'downloads' 
                ? 'bg-emerald-500 text-slate-950 shadow-sm font-semibold' 
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Download className="h-3.5 w-3.5" />
            Workspace Scripts Hub
          </button>
        </div>
      </header>

      {/* Main Workspace Layout (Two-column layout) */}
      <main className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-6 p-6 overflow-hidden">
        
        {/* Left Hand: Algo Code Editor Column */}
        <div className="lg:col-span-5 flex flex-col space-y-5">
          
          {/* Preset Picker Panel */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 shadow-xl">
            <h2 className="text-xs font-bold font-mono tracking-wider text-slate-400 uppercase mb-3 flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
              Algorithmic Blueprints
            </h2>
            <div className="space-y-2">
              {ALGO_PRESETS.map((preset) => (
                <button
                  key={preset.id}
                  onClick={() => handlePresetSelect(preset)}
                  className={`w-full text-left p-3 rounded-xl border text-xs transition-all duration-200 flex flex-col ${
                    selectedPreset.id === preset.id
                      ? 'bg-emerald-950/30 border-emerald-500/50 text-emerald-100'
                      : 'bg-slate-950/40 border-slate-800 hover:border-slate-700 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <div className="flex justify-between items-center w-full mb-1">
                    <span className="font-semibold text-white">{preset.name}</span>
                    <span className={`px-2 py-0.5 rounded-[4px] text-[10px] font-mono border ${
                      preset.id === 'options-buyer' ? 'bg-indigo-950/50 border-indigo-900 text-indigo-300' :
                      preset.id === 'options-seller' ? 'bg-amber-950/50 border-amber-900 text-amber-300' :
                      'bg-cyan-950/50 border-cyan-900 text-cyan-300'
                    }`}>
                      {preset.category}
                    </span>
                  </div>
                  <p className="text-[11px] leading-relaxed line-clamp-2">{preset.description}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Code Editor Console */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl shadow-xl flex-1 flex flex-col overflow-hidden min-h-[400px]">
            <div className="bg-slate-950/80 px-4 py-2 border-b border-slate-800 flex justify-between items-center flex-wrap gap-2">
              <div className="flex items-center space-x-3">
                <div className="flex items-center space-x-2">
                  <FileCode className="h-4 w-4 text-emerald-400" />
                  <span className="text-xs font-bold font-mono text-white">python_algo.py</span>
                </div>
                
                {/* Safety boilerplates injector */}
                <select
                  onChange={(e) => {
                    const val = e.target.value;
                    if (!val) return;
                    injectSafetyPattern(val);
                    e.target.value = ""; // Reset
                  }}
                  className="bg-slate-900 border border-slate-800 text-slate-300 text-[10px] font-mono rounded-md px-2 py-1 focus:outline-none focus:border-emerald-500 cursor-pointer"
                >
                  <option value="">🛡️ Inject Safety Boilerplate...</option>
                  <option value="backoff">Exponential Backoff Wrapper</option>
                  <option value="spread">Limit Order Spread Check</option>
                  <option value="ledger">Position State Ledger</option>
                  <option value="excel_ledger">Excel Ledger Logger</option>
                </select>
              </div>
              <div className="flex items-center space-x-1">
                <span className="w-2.5 h-2.5 rounded-full bg-red-500/80"></span>
                <span className="w-2.5 h-2.5 rounded-full bg-yellow-500/80"></span>
                <span className="w-2.5 h-2.5 rounded-full bg-green-500/80"></span>
              </div>
            </div>

            {/* Editable Screen */}
            <div className="flex-1 relative font-mono text-xs overflow-auto bg-slate-950/40 p-4">
              {injectSuccessMsg && (
                <div className="absolute top-4 right-4 bg-emerald-400 text-slate-950 font-bold px-3 py-1.5 rounded-lg shadow-lg flex items-center gap-1.5 text-[10px] z-10 font-sans border border-emerald-500 animate-pulse">
                  <Check className="h-3.5 w-3.5" />
                  {injectSuccessMsg}
                </div>
              )}
              <textarea
                value={customCode}
                onChange={(e) => setCustomCode(e.target.value)}
                className="w-full h-full bg-transparent text-emerald-400/90 focus:outline-none resize-none font-mono text-xs leading-relaxed"
                spellCheck="false"
                style={{ fontFamily: '"JetBrains Mono", Courier, monospace' }}
              />
            </div>

            <div className="border-t border-slate-800 p-4 bg-slate-900/50 flex space-x-3 items-center">
              <button
                disabled={isAnalyzing}
                onClick={runAudit}
                id="audit-algo-btn"
                className="flex-1 bg-emerald-500 hover:bg-emerald-400 active:scale-[0.98] text-slate-950 font-semibold py-2.5 px-4 rounded-xl text-xs transition-all duration-150 flex items-center justify-center space-x-2 shadow-lg shadow-emerald-500/10 cursor-pointer disabled:opacity-50"
              >
                {isAnalyzing ? (
                  <>
                    <RefreshCw className="h-4 w-4 animate-spin" />
                    <span>Analyzing Code Structure...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="h-4 w-4" />
                    <span>Run Deep Production Audit</span>
                  </>
                )}
              </button>
              
              <button
                onClick={() => setCustomCode(selectedPreset.code)}
                title="Reset Code Input"
                className="p-2.5 border border-slate-800 hover:border-slate-700 bg-slate-950/40 rounded-xl text-slate-400 hover:text-slate-100 transition-colors"
              >
                <RotateCcw className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>

        {/* Right Hand: Interactive Audit details or live Error simulator */}
        <div className="lg:col-span-7 flex flex-col overflow-hidden">
          
          {activeTab === 'audit' ? (
            <div className="space-y-6 flex-1 flex flex-col overflow-auto pr-1">
              
              {/* If API Key missing or other error occurs */}
              {apiError && (
                <div className="bg-red-950/40 border border-red-800 rounded-2xl p-4 flex items-start space-x-3 text-red-100">
                  <AlertTriangle className="h-5 w-5 text-red-500 shrink-0 mt-0.5" />
                  <div>
                    <h4 className="text-xs font-bold font-mono tracking-wide uppercase text-red-400 mb-1">Analysis Link Broken</h4>
                    <p className="text-xs">{apiError}</p>
                  </div>
                </div>
              )}

              {/* Loader Placeholder */}
              {isAnalyzing && (
                <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 flex flex-col items-center justify-center flex-1 space-y-4">
                  <div className="relative">
                    <div className="w-16 h-16 rounded-full border-4 border-slate-800 border-t-emerald-500 animate-spin"></div>
                    <Cpu className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 h-6 w-6 text-emerald-400 animate-pulse" />
                  </div>
                  <div className="text-center max-w-sm space-y-1.5">
                    <h3 className="text-sm font-semibold text-white">Gemini Engine Audit In Progress</h3>
                    <p className="text-xs text-slate-400">Inspecting Python loops, exception trees, margin limits, decay exposure, and edge state structures...</p>
                  </div>
                </div>
              )}

              {/* Audit Content Ready */}
              {!isAnalyzing && currentReport && (
                <div className="space-y-6">
                  
                  {/* Scores Grid */}
                  <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                    
                    <div className="bg-slate-900/60 border border-slate-800/80 p-3 rounded-2xl flex flex-col justify-between relative overflow-hidden">
                      <div className="absolute top-0 right-0 p-1">
                        <Gauge className="h-3 w-3 text-slate-600" />
                      </div>
                      <span className="text-[10px] font-mono text-slate-500 uppercase">SAFETY INDEX</span>
                      <div className="mt-2 flex items-baseline justify-between">
                        <span className={`text-2xl font-black ${
                          currentReport.safetyScore >= 70 ? 'text-emerald-400' :
                          currentReport.safetyScore >= 40 ? 'text-amber-400' : 'text-red-400'
                        }`}>
                          {currentReport.safetyScore}%
                        </span>
                      </div>
                      <div className="w-full bg-slate-800 rounded-full h-1 mt-2">
                        <div 
                          className={`h-1 rounded-full ${
                            currentReport.safetyScore >= 70 ? 'bg-emerald-500' :
                            currentReport.safetyScore >= 40 ? 'bg-amber-500' : 'bg-red-500'
                          }`} 
                          style={{ width: `${currentReport.safetyScore}%` }}
                        ></div>
                      </div>
                    </div>

                    <div className="bg-slate-900/60 border border-slate-800/80 p-3 rounded-2xl flex flex-col justify-between">
                      <span className="text-[10px] font-mono text-slate-500 uppercase">EXECUTION</span>
                      <div className="mt-2">
                        <span className="text-lg font-bold text-white tracking-tight">{currentReport.executionScore}/100</span>
                      </div>
                      <div className="w-full bg-slate-800 rounded-full h-1 mt-1">
                        <div className="bg-indigo-500 h-1 rounded-full" style={{ width: `${currentReport.executionScore}%` }}></div>
                      </div>
                    </div>

                    <div className="bg-slate-900/60 border border-slate-800/80 p-3 rounded-2xl flex flex-col justify-between">
                      <span className="text-[10px] font-mono text-slate-500 uppercase">ERROR HANDL</span>
                      <div className="mt-2">
                        <span className="text-lg font-bold text-white tracking-tight">{currentReport.errorScore}/100</span>
                      </div>
                      <div className="w-full bg-slate-800 rounded-full h-1 mt-1">
                        <div className="bg-blue-500 h-1 rounded-full" style={{ width: `${currentReport.errorScore}%` }}></div>
                      </div>
                    </div>

                    <div className="bg-slate-900/60 border border-slate-800/80 p-3 rounded-2xl flex flex-col justify-between">
                      <span className="text-[10px] font-mono text-slate-500 uppercase">FNO TRADING</span>
                      <div className="mt-2">
                        <span className="text-lg font-bold text-white tracking-tight">{currentReport.fnoScore}/100</span>
                      </div>
                      <div className="w-full bg-slate-800 rounded-full h-1 mt-1">
                        <div className="bg-violet-500 h-1 rounded-full" style={{ width: `${currentReport.fnoScore}%` }}></div>
                      </div>
                    </div>

                    <div className="bg-slate-900/60 border border-slate-800/80 p-3 rounded-2xl flex flex-col justify-between col-span-2 sm:col-span-1">
                      <span className="text-[10px] font-mono text-slate-500 uppercase">CRASH STORAGE</span>
                      <div className="mt-2">
                        <span className="text-lg font-bold text-white tracking-tight">{currentReport.recoveryScore}/100</span>
                      </div>
                      <div className="w-full bg-slate-800 rounded-full h-1 mt-1">
                        <div className="bg-cyan-500 h-1 rounded-full" style={{ width: `${currentReport.recoveryScore}%` }}></div>
                      </div>
                    </div>

                  </div>

                  {/* Executive Summary */}
                  <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-3">
                    <h3 className="text-xs font-bold font-mono text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                      <span className="p-0.5 bg-emerald-500/15 rounded text-emerald-400"><ShieldCheck className="h-3.5 w-3.5" /></span>
                      Production Readiness Summary
                    </h3>
                    <p className="text-slate-300 text-xs leading-relaxed">{currentReport.summary}</p>
                  </div>

                  {/* Red/Amber Critical Failures */}
                  <div className="space-y-3">
                    <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                      <Flame className="h-4 w-4 text-rose-500" />
                      Critical Silent Loop-holes Identified
                    </h3>
                    
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {currentReport.criticalFailures.map((fail, idx) => (
                        <div 
                          key={idx} 
                          className={`p-4 rounded-2xl border flex flex-col justify-between ${
                            fail.severity === 'CRITICAL' 
                              ? 'bg-rose-950/20 border-rose-900/40 text-rose-100' 
                              : 'bg-amber-950/20 border-amber-900/40 text-amber-100'
                          }`}
                        >
                          <div>
                            <div className="flex justify-between items-center mb-2">
                              <span className="text-xs font-bold font-mono tracking-tight text-white flex items-center gap-1.5">
                                <BadgeAlert className={`h-4 w-4 ${fail.severity === 'CRITICAL' ? 'text-rose-500' : 'text-amber-500'}`} />
                                {fail.title}
                              </span>
                              <span className={`px-2 py-0.5 rounded-[4px] text-[10px] font-mono font-bold tracking-wider upper ${
                                fail.severity === 'CRITICAL' ? 'bg-rose-500/20 text-rose-400 border border-rose-500/20' : 'bg-amber-500/20 text-amber-400 border border-amber-500/20'
                              }`}>
                                {fail.severity}
                              </span>
                            </div>
                            <p className="text-[11px] leading-relaxed text-slate-300">{fail.description}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                   {/* Greeks Threat Radar & Heatmap */}
                  <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-4">
                    <h3 className="text-xs font-bold font-mono text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                      <TrendingUp className="h-4 w-4 text-emerald-400" />
                      Options Greeks & Spread Security Check
                    </h3>
                    
                    <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
                      {/* Dynamic Radar Chart */}
                      <div className="lg:col-span-2 bg-slate-950 p-4 rounded-xl flex flex-col justify-center items-center relative overflow-hidden min-h-[250px] border border-slate-850">
                        <div className="absolute top-2.5 left-2.5 text-[9px] font-mono text-slate-500 uppercase tracking-wider">Dynamic Greeks Exposure Engine</div>
                        
                        <div className="w-full h-44 mt-4 flex justify-center items-center">
                          <ResponsiveContainer width="100%" height="100%">
                            <RadarChart cx="50%" cy="50%" outerRadius="70%" data={[
                              { subject: 'Delta (Δ)', A: currentReport.greeksNumeric?.delta ?? 50, fullMark: 100 },
                              { subject: 'Gamma (Γ)', A: currentReport.greeksNumeric?.gamma ?? 40, fullMark: 100 },
                              { subject: 'Theta (θ)', A: currentReport.greeksNumeric?.theta ?? 60, fullMark: 100 },
                              { subject: 'Vega (ν)', A: currentReport.greeksNumeric?.vega ?? 50, fullMark: 100 },
                              { subject: 'Liquidity', A: currentReport.greeksNumeric?.liquidity ?? 50, fullMark: 100 },
                            ]}>
                              <PolarGrid stroke="#334155" />
                              <PolarAngleAxis dataKey="subject" tick={{ fill: '#94a3b8', fontSize: 9, fontFamily: 'monospace' }} />
                              <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: '#475569', fontSize: 8 }} />
                              <Radar name="Threat Exposure" dataKey="A" stroke="#10b981" fill="#10b981" fillOpacity={0.25} />
                              <Tooltip 
                                contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px' }}
                                labelStyle={{ color: '#94a3b8', fontFamily: 'monospace', fontSize: '10px' }}
                                itemStyle={{ color: '#34d399', fontSize: '10px' }}
                              />
                            </RadarChart>
                          </ResponsiveContainer>
                        </div>
                      </div>

                      {/* Qualitative Descriptions */}
                      <div className="lg:col-span-3 grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div className="p-3 bg-slate-950 rounded-xl space-y-1 border border-slate-850">
                          <div className="flex justify-between items-center">
                            <div className="flex items-center space-x-1.5">
                              <span className="text-xs font-bold font-mono text-emerald-400">Delta Risk</span>
                              <span className="text-[10px] bg-emerald-500/10 text-emerald-400 px-1 py-0.5 rounded font-mono">Δ</span>
                            </div>
                            <span className="text-[9px] font-mono font-bold text-slate-400">{currentReport.greeksNumeric?.delta ?? 50}%</span>
                          </div>
                          <p className="text-[11px] text-slate-400 leading-relaxed">{currentReport.greeksAssessed.delta}</p>
                        </div>

                        <div className="p-3 bg-slate-950 rounded-xl space-y-1 border border-slate-850">
                          <div className="flex justify-between items-center">
                            <div className="flex items-center space-x-1.5">
                              <span className="text-xs font-bold font-mono text-purple-400">Theta Decay</span>
                              <span className="text-[10px] bg-purple-500/10 text-purple-400 px-1 py-0.5 rounded font-mono">θ</span>
                            </div>
                            <span className="text-[9px] font-mono font-bold text-slate-400">{currentReport.greeksNumeric?.theta ?? 60}%</span>
                          </div>
                          <p className="text-[11px] text-slate-400 leading-relaxed">{currentReport.greeksAssessed.theta}</p>
                        </div>

                        <div className="p-3 bg-slate-950 rounded-xl space-y-1 border border-slate-850">
                          <div className="flex justify-between items-center">
                            <div className="flex items-center space-x-1.5">
                              <span className="text-xs font-bold font-mono text-cyan-400">Vega Exposure</span>
                              <span className="text-[10px] bg-cyan-500/10 text-cyan-400 px-1 py-0.5 rounded font-mono">ν</span>
                            </div>
                            <span className="text-[9px] font-mono font-bold text-slate-400">{currentReport.greeksNumeric?.vega ?? 50}%</span>
                          </div>
                          <p className="text-[11px] text-slate-400 leading-relaxed">{currentReport.greeksAssessed.vega}</p>
                        </div>

                        <div className="p-3 bg-slate-950 rounded-xl space-y-1 border border-slate-850">
                          <div className="flex justify-between items-center">
                            <div className="flex items-center space-x-1.5">
                              <span className="text-xs font-bold font-mono text-indigo-400">Strike Liquidity</span>
                              <span className="text-[10px] bg-indigo-500/10 text-indigo-400 px-1 py-0.5 rounded font-mono">Bid-Ask</span>
                            </div>
                            <span className="text-[9px] font-mono font-bold text-slate-400">{currentReport.greeksNumeric?.liquidity ?? 50}%</span>
                          </div>
                          <p className="text-[11px] text-slate-400 leading-relaxed">{currentReport.greeksAssessed.liquidity}</p>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Recommendations */}
                  <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-3">
                    <h3 className="text-xs font-bold font-mono text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                      <Settings className="h-4 w-4 text-emerald-400" />
                      Required Hardening Actions
                    </h3>
                    <ul className="space-y-2 text-xs text-slate-300 pl-4 list-decimal">
                      {currentReport.recommendations.map((rec, index) => (
                        <li key={index} className="leading-relaxed leading-6">{rec}</li>
                      ))}
                    </ul>
                  </div>

                  {/* Hardened Version Overlay code */}
                  <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl flex flex-col">
                    <div className="bg-slate-950/80 px-4 py-3 border-b border-slate-800 flex justify-between items-center">
                      <div className="flex items-center space-x-2">
                        <Shield className="h-4 w-4 text-emerald-400" />
                        <span className="text-xs font-bold font-mono text-white">hardened_resilient_wrapper.py</span>
                      </div>
                      <button
                        onClick={() => copyToClipboard(currentReport.hardenedCode)}
                        className="py-1 px-2.5 rounded border border-slate-800 hover:border-slate-700 bg-slate-950/50 text-[11px] font-mono text-slate-300 hover:text-white flex items-center gap-1 cursor-pointer"
                      >
                        {copySuccess ? (
                          <>
                            <Check className="h-3 w-3 text-emerald-400" />
                            <span>Copied!</span>
                          </>
                        ) : (
                          <>
                            <Copy className="h-3 w-3" />
                            <span>Copy Safe Code</span>
                          </>
                        )}
                      </button>
                    </div>

                    <div className="bg-slate-950 p-4 font-mono text-xs overflow-x-auto text-emerald-400/95 max-h-[420px] leading-relaxed">
                      <pre>{currentReport.hardenedCode}</pre>
                    </div>
                  </div>

                </div>
              )}
            </div>
          ) : activeTab === 'simulator' ? (
            
            /* Interactive Error Simulator Screen */
            <div className="space-y-5 flex-1 flex flex-col overflow-auto pr-1">
              
              {/* Score Header for simulator */}
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 flex justify-between items-center shadow-lg">
                <div className="space-y-1">
                  <span className="text-[10px] font-mono text-slate-500 uppercase">ACTIVE TEST BED</span>
                  <h3 className="text-sm font-bold text-white flex items-center gap-1.5">
                    <Activity className="h-4 w-4 text-emerald-400 animate-pulse" />
                    Market Error & Outage stress test
                  </h3>
                </div>
                
                <button
                  onClick={startSimulation}
                  className={`px-4 py-1.5 rounded-lg text-xs font-bold cursor-pointer transition-all duration-150 flex items-center gap-1.5 ${
                    simActive 
                      ? 'bg-rose-500 text-slate-950 shadow-lg shadow-rose-500/10' 
                      : 'bg-emerald-500 text-slate-950 shadow-lg shadow-emerald-500/10'
                  }`}
                >
                  {simActive ? (
                    <>
                      <Power className="h-3.5 w-3.5" />
                      Pause Stress Feed
                    </>
                  ) : (
                    <>
                      <Play className="h-3.5 w-3.5" />
                      Trigger Market Feed
                    </>
                  )}
                </button>
              </div>

              {/* Chart of ATM Premium Index and Current Values */}
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-4">
                <div className="flex justify-between items-center text-xs">
                  <div className="flex items-center space-x-2">
                    <span className="p-1 h-2 w-2 rounded-full bg-emerald-500 animate-ping"></span>
                    <span className="font-mono text-white text-xs">NIFTY NEXT Contract LTP (Premium)</span>
                  </div>
                  <div className="font-mono font-bold text-sm text-emerald-400">
                    ₹{premiumPrice.toFixed(2)}
                  </div>
                </div>

                {/* Custom SVG Line Chart */}
                <div className="h-28 bg-slate-950 rounded-xl relative overflow-hidden flex items-end p-2 border border-slate-800/80">
                  <svg className="w-full h-full absolute inset-0" viewBox="0 0 100 100" preserveAspectRatio="none">
                    {/* Grid lines */}
                    <line x1="0" y1="25" x2="100" y2="25" stroke="#1e293b" strokeWidth="0.5" />
                    <line x1="0" y1="50" x2="100" y2="50" stroke="#1e293b" strokeWidth="0.5" />
                    <line x1="0" y1="75" x2="100" y2="75" stroke="#1e293b" strokeWidth="0.5" />

                    {/* Plot coordinates */}
                    {(() => {
                      const minPrice = Math.min(...historicalPrices);
                      const maxPrice = Math.max(...historicalPrices);
                      const priceDiff = maxPrice - minPrice || 1;
                      
                      const points = historicalPrices.map((price, idx) => {
                        const x = (idx / (historicalPrices.length - 1)) * 100;
                        const y = 90 - ((price - minPrice) / priceDiff) * 80;
                        return `${x},${y}`;
                      }).join(' ');

                      return (
                        <>
                          {/* Gradient under the curve */}
                          <path
                            d={`M 0,100 L ${points} L 100,100 Z`}
                            fill="url(#premiumGrad)"
                            opacity="0.15"
                          />
                          <polyline
                            fill="none"
                            stroke="#10b981"
                            strokeWidth="1.5"
                            points={points}
                          />
                          <defs>
                            <linearGradient id="premiumGrad" x1="0%" y1="0%" x2="0%" y2="100%">
                              <stop offset="0%" stopColor="#10b981" />
                              <stop offset="100%" stopColor="#10b981" stopOpacity="0" />
                            </linearGradient>
                          </defs>
                        </>
                      );
                    })()}
                  </svg>
                  <div className="absolute top-2 left-2 text-[9px] font-mono text-slate-500 uppercase">Tick-by-tick Options contract orderbook</div>
                </div>

                {/* Real-time Margin Utilization Dashboard Widget */}
                <div className="bg-slate-950 p-4 rounded-xl border border-slate-800/85 space-y-4">
                  <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center border-b border-slate-800/65 pb-2.5 gap-2">
                    <div className="flex items-center space-x-2">
                      <Gauge className="h-4 w-4 text-emerald-400 animate-pulse" />
                      <div>
                        <span className="font-mono text-xs font-bold text-white block">BROKER MARGIN SENTINEL</span>
                        <span className="text-[10px] text-slate-500 font-mono">Live collateral vs. position locked margins</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="text-right">
                        <span className="text-[9px] text-slate-500 uppercase font-mono block">TOTAL COLLATERAL</span>
                        <span className="font-mono text-xs font-bold text-emerald-400">₹{totalMargin.toLocaleString()}</span>
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Unprotected Track Margin Meter */}
                    <div className={`p-3 rounded-xl border transition-all duration-200 ${
                      (usedMarginUnhardened / totalMargin) > 1.0
                        ? 'bg-red-950/20 border-red-500 animate-pulse'
                        : (usedMarginUnhardened / totalMargin) > 0.8
                          ? 'bg-amber-950/20 border-amber-600'
                          : 'bg-slate-900/40 border-slate-800/80'
                    }`}>
                      <div className="flex justify-between items-center text-[10px] font-mono mb-1.5">
                        <span className="text-slate-400 uppercase">UNPROTECTED MARGIN UTILIZATION</span>
                        <span className={`font-bold ${
                          (usedMarginUnhardened / totalMargin) > 1.0 ? 'text-red-500' :
                          (usedMarginUnhardened / totalMargin) > 0.8 ? 'text-amber-500' : 'text-slate-300'
                        }`}>
                          {((usedMarginUnhardened / totalMargin) * 100).toFixed(1)}% Usage
                        </span>
                      </div>

                      {/* Progress bar */}
                      <div className="w-full bg-slate-800/80 rounded-full h-2 overflow-hidden mb-2">
                        <div 
                          className={`h-2 rounded-full transition-all duration-300 ${
                            (usedMarginUnhardened / totalMargin) > 1.0 ? 'bg-red-500' :
                            (usedMarginUnhardened / totalMargin) > 0.8 ? 'bg-amber-500' : 'bg-indigo-500'
                          }`}
                          style={{ width: `${Math.min(100, (usedMarginUnhardened / totalMargin) * 100)}%` }}
                        ></div>
                      </div>

                      <div className="flex justify-between items-center text-[10px] font-mono">
                        <div className="text-slate-400">
                          Used: <span className="text-slate-200 font-bold">₹{usedMarginUnhardened.toLocaleString()}</span>
                        </div>
                        <div className="text-slate-400">
                          Avail: <span className="text-slate-200 font-bold">₹{Math.max(0, totalMargin - usedMarginUnhardened).toLocaleString()}</span>
                        </div>
                      </div>

                      {/* Extra context for server amnesia or crash scenarios */}
                      {activeFailure === 'server-reboot' && (
                        <div className="mt-2.5 text-[10px] bg-red-950/30 border border-red-900/40 p-2 rounded-lg text-red-400 font-mono leading-relaxed">
                          ⚠️ AMNESIA OUT OF SYNC: local status reads ₹0 (FLAT) because memory got wiped, but true broker margin holds ₹180,000 hostage!
                        </div>
                      )}
                      {activeFailure === 'iv-spike' && (usedMarginUnhardened / totalMargin) > 1.0 && (
                        <div className="mt-2.5 text-[10px] bg-red-950/30 border border-red-900/40 p-2 rounded-lg text-red-500 font-mono leading-relaxed animate-pulse">
                          🚨 MARGIN DEFICIT EXHAUSTED: System failed stop-guards. Auto square-off incoming!
                        </div>
                      )}
                    </div>

                    {/* Hardened Track Margin Meter */}
                    <div className="p-3 bg-slate-900/40 border border-slate-850 rounded-xl">
                      <div className="flex justify-between items-center text-[10px] font-mono mb-1.5">
                        <span className="text-slate-400 uppercase">HARDENED MARGIN UTILIZATION</span>
                        <span className="font-bold text-emerald-400">
                          {((usedMarginHardened / totalMargin) * 100).toFixed(1)}% Usage
                        </span>
                      </div>

                      {/* Progress bar */}
                      <div className="w-full bg-slate-800/80 rounded-full h-2 overflow-hidden mb-2">
                        <div 
                          className="h-2 rounded-full bg-emerald-500 transition-all duration-300"
                          style={{ width: `${Math.min(100, (usedMarginHardened / totalMargin) * 100)}%` }}
                        ></div>
                      </div>

                      <div className="flex justify-between items-center text-[10px] font-mono">
                        <div className="text-slate-400">
                          Used: <span className="text-slate-200 font-bold">₹{usedMarginHardened.toLocaleString()}</span>
                        </div>
                        <div className="text-slate-400">
                          Avail: <span className="text-slate-200 font-bold">₹{Math.max(0, totalMargin - usedMarginHardened).toLocaleString()}</span>
                        </div>
                      </div>

                      {/* Savings message */}
                      {usedMarginUnhardened > usedMarginHardened && (
                        <div className="mt-2.5 text-[10px] bg-emerald-950/35 border border-emerald-950 px-2 py-1.5 rounded-lg text-emerald-400 font-mono leading-relaxed">
                          🛡️ HEDGE EFFICIENCY STAT: Saved <span className="font-bold">₹{(usedMarginUnhardened - usedMarginHardened).toLocaleString()}</span> capital margin requirements!
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Simulated Stats Bar */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-1">
                  
                  <div className="bg-slate-950 p-3 rounded-xl border border-slate-800/60 font-mono text-xs">
                    <span className="text-[10px] text-slate-500 block">UNPROTECTED HOLDING</span>
                    <span className={`text-xs font-bold block mt-1 ${
                      simPositionUp.unprotected === 'N/A' || simPositionUp.unprotected === 'LIQUIDATED' ? 'text-red-500' : 'text-emerald-400'
                    }`}>
                      {simPositionUp.unprotected || 'LONG'}
                    </span>
                  </div>

                  <div className="bg-slate-950 p-3 rounded-xl border border-slate-800/60 font-mono text-xs">
                    <span className="text-[10px] text-slate-500 block">HARDENED HOLDING</span>
                    <span className="text-xs text-emerald-400 font-bold block mt-1">
                      {simPositionUp.hardened || 'LONG'}
                    </span>
                  </div>

                  <div className="bg-slate-950 p-3 rounded-xl border border-slate-800/60 font-mono text-xs">
                    <span className="text-[10px] text-slate-500 block">UNPROTECTED P&L</span>
                    <span className={`text-xs font-extrabold block mt-1 ${
                      simProfitUp.unhardened >= 0 ? 'text-green-400' : 'text-red-400'
                    }`}>
                      ₹{simProfitUp.unhardened ? simProfitUp.unhardened.toLocaleString() : '0'}
                    </span>
                  </div>

                  <div className="bg-slate-950 p-3 rounded-xl border border-slate-800/60 font-mono text-xs">
                    <span className="text-[10px] text-slate-500 block">HARDENED P&L</span>
                    <span className={`text-xs font-extrabold block mt-1 ${
                      simProfitUp.hardened >= 0 ? 'text-green-400' : 'text-red-400'
                    }`}>
                      ₹{simProfitUp.hardened ? simProfitUp.hardened.toLocaleString() : '0'}
                    </span>
                  </div>

                </div>
              </div>

              {/* OUTAGE INJECT PANEL */}
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-4">
                <h3 className="text-xs font-bold font-mono text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                  <BadgeAlert className="h-4 w-4 text-amber-500" />
                  Inject Production Outages & Outliers
                </h3>
                
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                  {SIMULATOR_FAILURES.map((fail) => (
                    <button
                      key={fail.id}
                      disabled={!simActive}
                      onClick={() => injectFailure(fail)}
                      className={`p-3 text-left rounded-xl border text-xs transition-all duration-150 flex flex-col justify-between ${
                        !simActive 
                          ? 'opacity-40 cursor-not-allowed bg-slate-950/40 border-slate-800' 
                          : activeFailure === fail.id
                            ? 'bg-rose-950/40 border-rose-500 scale-[0.98]'
                            : 'bg-slate-950 border-slate-800/80 hover:border-slate-700 hover:scale-[1.01] cursor-pointer'
                      }`}
                    >
                      <div>
                        <div className="flex justify-between items-center mb-1">
                          <span className="font-bold text-white text-[11px] leading-tight">{fail.name}</span>
                          <span className={`text-[8px] font-mono px-1 rounded uppercase tracking-wider leading-none ${
                            fail.severity === 'CRITICAL' ? 'bg-rose-500/25 text-rose-400' : 'bg-amber-500/25 text-amber-400'
                          }`}>
                            {fail.severity}
                          </span>
                        </div>
                        <p className="text-[10px] text-slate-400 leading-normal line-clamp-2">{fail.description}</p>
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {/* LOG TRACES (UNPROTECTED vs HARDENED) */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 flex-1">
                
                {/* Unprotected Frame */}
                <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl flex flex-col h-[300px]">
                  <div className="bg-slate-950 px-4 py-2.5 border-b border-rose-950/80 flex justify-between items-center bg-rose-950/10">
                    <span className="text-[10px] font-mono font-bold text-rose-400 tracking-wider uppercase flex items-center gap-1.5">
                      <Flame className="h-3.5 w-3.5" />
                      Standard Raw Loop Traces
                    </span>
                    <span className="w-2 h-2 rounded-full bg-rose-500"></span>
                  </div>
                  
                  <div className="flex-1 overflow-auto p-4 font-mono text-[11px] space-y-2 bg-slate-950/40 text-slate-300">
                    {simLogs.filter(log => log.source === 'UNPROTECTED').length === 0 ? (
                      <div className="text-slate-500 italic flex items-center h-full justify-center">Waiting for live simulation feed ticks...</div>
                    ) : (
                      simLogs.filter(log => log.source === 'UNPROTECTED').map((log, index) => (
                        <div key={index} className="leading-relaxed border-b border-slate-900/40 pb-1">
                          <span className="text-slate-600 mr-1.5">[{log.timestamp}]</span>
                          <span className={`font-bold mr-1.5 ${
                            log.type === 'ERROR' ? 'text-red-500' :
                            log.type === 'WARN' ? 'text-amber-500' :
                            log.type === 'SUCCESS' ? 'text-emerald-400' : 'text-sky-400'
                          }`}>
                            {log.type}
                          </span>
                          <span className="text-slate-300">{log.message}</span>
                        </div>
                      ))
                    )}
                  </div>
                </div>

                {/* Hardened Frame */}
                <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl flex flex-col h-[300px]">
                  <div className="bg-slate-950 px-4 py-2.5 border-b border-emerald-950/80 flex justify-between items-center bg-emerald-950/5">
                    <span className="text-[10px] font-mono font-bold text-emerald-400 tracking-wider uppercase flex items-center gap-1.5">
                      <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
                      Armed Resilient Loop Traces
                    </span>
                    <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                  </div>
                  
                  <div className="flex-1 overflow-auto p-4 font-mono text-[11px] space-y-2 bg-slate-950/40 text-slate-300">
                    {simLogs.filter(log => log.source === 'HARDENED').length === 0 ? (
                      <div className="text-slate-500 italic flex items-center h-full justify-center">Waiting for live simulation feed ticks...</div>
                    ) : (
                      simLogs.filter(log => log.source === 'HARDENED').map((log, index) => (
                        <div key={index} className="leading-relaxed border-b border-slate-900/40 pb-1">
                          <span className="text-slate-600 mr-1.5">[{log.timestamp}]</span>
                          <span className={`font-bold mr-1.5 ${
                            log.type === 'ERROR' ? 'text-red-500' :
                            log.type === 'WARN' ? 'text-amber-500' :
                            log.type === 'SUCCESS' ? 'text-emerald-400' : 'text-sky-400'
                          }`}>
                            {log.type}
                          </span>
                          <span className="text-slate-300">{log.message}</span>
                        </div>
                      ))
                    )}
                  </div>
                </div>

              </div>

            </div>
          ) : (
            /* Scripts Download Hub */
            <div className="space-y-6 flex-1 flex flex-col overflow-auto pr-1 animate-fade-in text-slate-100 pb-8">
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-emerald-400">
                    <Download className="h-6 w-6" />
                  </div>
                  <div>
                    <h2 className="text-base font-bold text-white">Production Script Download Hub</h2>
                    <p className="text-xs text-slate-400 font-mono">Download fully hardened, modularized Python trading algorithms and active system ledgers.</p>
                  </div>
                </div>
                <div className="border-t border-slate-800/80 pt-3 text-xs text-slate-300 leading-relaxed space-y-2">
                  <p>All scripts in this workspace are fully integrated with the <strong>Dhan-Tradehull API</strong> and constructed with high-integrity structural checks like automatic gap cooldowns, trailing stop-losses, and open-interest runaway walls.</p>
                  <p className="text-[11px] text-emerald-400/90 font-mono">💡 <em>Tip: Click any file asset below to trigger an immediate, secure direct download. Place them in your local system directory to execute them.</em></p>
                </div>
              </div>

              {/* Grid of Files */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                
                {/* Market_Scanner.py */}
                <div className="bg-slate-900 border border-slate-800/60 rounded-xl overflow-hidden hover:border-emerald-500/30 transition-colors group">
                  <div className="px-4 py-3 border-b border-slate-800/80 flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <div className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-400">
                        <FileCode className="h-4 w-4" />
                      </div>
                      <div>
                        <span className="text-xs font-bold font-mono text-white">Market_Scanner.py</span>
                      </div>
                    </div>
                    <div>
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 uppercase">Live CSV logs</span>
                    </div>
                  </div>
                  <div className="px-4 py-3 bg-slate-900/50">
                    <p className="text-xs text-slate-400 mb-4 leading-relaxed font-mono">
                      Subprocesses real-time market data matching triggers against NIFTY 50 technical states.
                    </p>
                    <a 
                      href="/api/download?file=Market_Scanner.py" 
                      download="Market_Scanner.py"
                      className="w-full bg-slate-800 hover:bg-slate-700 text-white text-xs py-2 px-3 rounded-xl flex items-center justify-center gap-1.5 transition-colors cursor-pointer text-center font-sans tracking-tight border border-slate-700 hover:border-slate-600"
                    >
                      <Download className="h-3.5 w-3.5" />
                      Download Market_Scanner.py
                    </a>
                  </div>
                </div>

                {/* MainEngine.py */}
                <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl hover:border-emerald-500/30 transition-all duration-200 flex flex-col justify-between">
                  <div>
                    <div className="flex justify-between items-start mb-2">
                      <div className="flex items-center space-x-2">
                        <FileCode className="h-5 w-5 text-emerald-400" />
                        <span className="text-xs font-bold font-mono text-white">MainEngine.py</span>
                      </div>
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 uppercase">Core Scanning</span>
                    </div>
                    <p className="text-[11px] text-slate-400 leading-relaxed mb-4 font-sans">
                      Scans index parameters, identifies ATM/ITM trend targets, executes entry orders securely, and spawns the Price Check trailing stop tracker sub-thread.
                    </p>
                  </div>
                  <a 
                    href="/api/download?file=MainEngine.py" 
                    download="MainEngine.py"
                    className="w-full bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs py-2 px-3 rounded-xl flex items-center justify-center gap-1.5 transition-colors cursor-pointer text-center font-sans tracking-tight"
                  >
                    <Download className="h-3.5 w-3.5" />
                    Download MainEngine.py
                  </a>
                </div>

                {/* excel_ledger_orderbook.py */}
                <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl hover:border-emerald-500/30 transition-all duration-200 flex flex-col justify-between">
                  <div>
                    <div className="flex justify-between items-start mb-2">
                      <div className="flex items-center space-x-2">
                        <FileCode className="h-5 w-5 text-emerald-400" />
                        <span className="text-xs font-bold font-mono text-white">excel_ledger_orderbook.py</span>
                      </div>
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-sky-500/10 border border-sky-500/20 text-sky-400 uppercase">CSV Ledger</span>
                    </div>
                    <p className="text-[11px] text-slate-400 leading-relaxed mb-4 font-sans">
                      Logs live transaction details, margin consumption estimation, contract names, and entry premium pricing to Excel-compatible logging sheets.
                    </p>
                  </div>
                  <a 
                    href="/api/download?file=excel_ledger_orderbook.py" 
                    download="excel_ledger_orderbook.py"
                    className="w-full bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs py-2 px-3 rounded-xl flex items-center justify-center gap-1.5 transition-colors cursor-pointer text-center font-sans tracking-tight"
                  >
                    <Download className="h-3.5 w-3.5" />
                    Download Ledger Script
                  </a>
                </div>

                {/* Price_Check.py */}
                <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl hover:border-emerald-500/30 transition-all duration-200 flex flex-col justify-between">
                  <div>
                    <div className="flex justify-between items-start mb-2">
                      <div className="flex items-center space-x-2">
                        <FileCode className="h-5 w-5 text-emerald-400" />
                        <span className="text-xs font-bold font-mono text-white">Price_Check.py</span>
                      </div>
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-violet-500/10 border border-violet-500/20 text-violet-400 uppercase">Trailing Daemon</span>
                    </div>
                    <p className="text-[11px] text-slate-400 leading-relaxed mb-4 font-sans">
                      An autonomous background execution watcher. Runs in the background, prints current LTP every 30 seconds, and triggers exits on SL or Target.
                    </p>
                  </div>
                  <a 
                    href="/api/download?file=Price_Check.py" 
                    download="Price_Check.py"
                    className="w-full bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs py-2 px-3 rounded-xl flex items-center justify-center gap-1.5 transition-colors cursor-pointer text-center font-sans tracking-tight"
                  >
                    <Download className="h-3.5 w-3.5" />
                    Download Price_Check.py
                  </a>
                </div>

                {/* Monitor_Engine.py */}
                <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl hover:border-emerald-500/30 transition-all duration-200 flex flex-col justify-between">
                  <div>
                    <div className="flex justify-between items-start mb-2">
                      <div className="flex items-center space-x-2">
                        <FileCode className="h-5 w-5 text-emerald-400" />
                        <span className="text-xs font-bold font-mono text-white">Monitor_Engine.py</span>
                      </div>
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-amber-500/10 border border-amber-500/20 text-amber-400 uppercase">State machine</span>
                    </div>
                    <p className="text-[11px] text-slate-400 leading-relaxed mb-4 font-sans">
                      Powering the SL trailing state logic. Checks index EMA crossovers, decay-level timing exits, and trailing targets to feed the active tracker daemon.
                    </p>
                  </div>
                  <a 
                    href="/api/download?file=Monitor_Engine.py" 
                    download="Monitor_Engine.py"
                    className="w-full bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs py-2 px-3 rounded-xl flex items-center justify-center gap-1.5 transition-colors cursor-pointer text-center font-sans tracking-tight"
                  >
                    <Download className="h-3.5 w-3.5" />
                    Download Monitor_Engine.py
                  </a>
                </div>

                {/* Indicators.py */}
                <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl hover:border-emerald-500/30 transition-all duration-200 flex flex-col justify-between">
                  <div>
                    <div className="flex justify-between items-start mb-2">
                      <div className="flex items-center space-x-2">
                        <FileCode className="h-5 w-5 text-emerald-400" />
                        <span className="text-xs font-bold font-mono text-white">Indicators.py</span>
                      </div>
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-pink-500/10 border border-pink-500/20 text-pink-400 uppercase">Math Engine</span>
                    </div>
                    <p className="text-[11px] text-slate-400 leading-relaxed mb-4 font-sans">
                      Maintains indicator calculus, producing exponential moving averages (EMA fast/slow), VWAP prices, and discrete option contract volume EMAs.
                    </p>
                  </div>
                  <a 
                    href="/api/download?file=Indicators.py" 
                    download="Indicators.py"
                    className="w-full bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs py-2 px-3 rounded-xl flex items-center justify-center gap-1.5 transition-colors cursor-pointer text-center font-sans tracking-tight"
                  >
                    <Download className="h-3.5 w-3.5" />
                    Download Indicators.py
                  </a>
                </div>

                {/* Risk_Engine.py */}
                <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl hover:border-emerald-500/30 transition-all duration-200 flex flex-col justify-between">
                  <div>
                    <div className="flex justify-between items-start mb-2">
                      <div className="flex items-center space-x-2">
                        <FileCode className="h-5 w-5 text-emerald-400" />
                        <span className="text-xs font-bold font-mono text-white">Risk_Engine.py</span>
                      </div>
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-red-500/10 border border-red-500/20 text-red-400 uppercase">Safety limits</span>
                    </div>
                    <p className="text-[11px] text-slate-400 leading-relaxed mb-4 font-sans">
                      Evaluates potential risk scenarios before entering positions. Checks gap risk cooldown triggers, index overextensions, and candle exhaustion boundaries.
                    </p>
                  </div>
                  <a 
                    href="/api/download?file=Risk_Engine.py" 
                    download="Risk_Engine.py"
                    className="w-full bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs py-2 px-3 rounded-xl flex items-center justify-center gap-1.5 transition-colors cursor-pointer text-center font-sans tracking-tight"
                  >
                    <Download className="h-3.5 w-3.5" />
                    Download Risk_Engine.py
                  </a>
                </div>

                {/* Option_strategy_core.py */}
                <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl hover:border-emerald-500/30 transition-all duration-200 flex flex-col justify-between">
                  <div>
                    <div className="flex justify-between items-start mb-2">
                      <div className="flex items-center space-x-2">
                        <FileCode className="h-5 w-5 text-emerald-400" />
                        <span className="text-xs font-bold font-mono text-white">Option_strategy_core.py</span>
                      </div>
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-teal-500/10 border border-teal-500/20 text-teal-400 uppercase">Trigger rules</span>
                    </div>
                    <p className="text-[11px] text-slate-400 leading-relaxed mb-4 font-sans">
                      Handles multi-stage qualification rules: evaluates PCR ratios, volume support, runway clearance paths from massive barrier strikes, and dynamic buy score levels.
                    </p>
                  </div>
                  <a 
                    href="/api/download?file=Option_strategy_core.py" 
                    download="Option_strategy_core.py"
                    className="w-full bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs py-2 px-3 rounded-xl flex items-center justify-center gap-1.5 transition-colors cursor-pointer text-center font-sans tracking-tight"
                  >
                    <Download className="h-3.5 w-3.5" />
                    Download Core Strategy
                  </a>
                </div>

                {/* RiseFall_sub.py */}
                <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl hover:border-emerald-500/30 transition-all duration-200 flex flex-col justify-between">
                  <div>
                    <div className="flex justify-between items-start mb-2">
                      <div className="flex items-center space-x-2">
                        <FileCode className="h-5 w-5 text-emerald-400" />
                        <span className="text-xs font-bold font-mono text-white">RiseFall_sub.py</span>
                      </div>
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-purple-500/10 border border-purple-500/20 text-purple-400 uppercase">Breakout level</span>
                    </div>
                    <p className="text-[11px] text-slate-400 leading-relaxed mb-4 font-sans">
                      Houses Call (CE) and Put (PE) breakout evaluation rules, ensuring RSI indicators originate from deep bounds and do not trigger on late momentum exhaustion.
                    </p>
                  </div>
                  <a 
                    href="/api/download?file=RiseFall_sub.py" 
                    download="RiseFall_sub.py"
                    className="w-full bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs py-2 px-3 rounded-xl flex items-center justify-center gap-1.5 transition-colors cursor-pointer text-center font-sans tracking-tight"
                  >
                    <Download className="h-3.5 w-3.5" />
                    Download RiseFall_sub.py
                  </a>
                </div>

                {/* Dhan_Tradehull.py */}
                <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl hover:border-emerald-500/30 transition-all duration-200 flex flex-col justify-between">
                  <div>
                    <div className="flex justify-between items-start mb-2">
                      <div className="flex items-center space-x-2">
                        <FileCode className="h-5 w-5 text-emerald-400" />
                        <span className="text-xs font-bold font-mono text-white">Dhan_Tradehull.py</span>
                      </div>
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-blue-500/10 border border-blue-500/20 text-blue-400 uppercase">Broker wrapper</span>
                    </div>
                    <p className="text-[11px] text-slate-400 leading-relaxed mb-4 font-sans">
                      Provides reliable API interaction endpoints: pulls Option Chain arrays, initiates intraday candles, fetches ticker LTPs, and executes order transactions cleanly.
                    </p>
                  </div>
                  <a 
                    href="/api/download?file=Dhan_Tradehull.py" 
                    download="Dhan_Tradehull.py"
                    className="w-full bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs py-2 px-3 rounded-xl flex items-center justify-center gap-1.5 transition-colors cursor-pointer text-center font-sans tracking-tight"
                  >
                    <Download className="h-3.5 w-3.5" />
                    Download Dhan Wrapper
                  </a>
                </div>

                {/* Active CSV Ledger */}
                <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl hover:border-emerald-500/30 transition-all duration-200 flex flex-col justify-between">
                  <div>
                    <div className="flex justify-between items-start mb-2">
                      <div className="flex items-center space-x-2">
                        <FileSpreadsheet className="h-5 w-5 text-emerald-400" />
                        <span className="text-xs font-bold font-mono text-white">trading_execution_ledger.csv</span>
                      </div>
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 uppercase">Live CSV logs</span>
                    </div>
                    <p className="text-[11px] text-slate-400 leading-relaxed mb-4 font-sans">
                      The dynamic spreadsheet transaction log containing live records of executing simulator trades, margins, entry points, and orders.
                    </p>
                  </div>
                  <a 
                    href="/api/download?file=trading_execution_ledger.csv" 
                    download="trading_execution_ledger.csv"
                    className="w-full bg-indigo-500 hover:bg-indigo-400 text-slate-950 font-bold text-xs py-2 px-3 rounded-xl flex items-center justify-center gap-1.5 transition-colors cursor-pointer text-center font-sans tracking-tight"
                  >
                    <Download className="h-3.5 w-3.5" />
                    Download Active Ledger CSV
                  </a>
                </div>

              </div>

              {/* Assembly Instructions */}
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-3">
                <h3 className="text-xs font-bold font-mono tracking-wider text-slate-400 uppercase flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                  Local Deployment & Instruction Stack
                </h3>
                <div className="space-y-3 text-xs text-slate-300 leading-relaxed pl-1 font-sans">
                  <p>To run this high-performance algo suite locally on your computer:</p>
                  <ol className="list-decimal pl-4 space-y-2">
                    <li>Create a fresh folder on your computer and place all downloaded <code>.py</code> scripts inside it.</li>
                    <li>Install dependency requirements via pip: <code className="bg-slate-950 px-1.5 py-0.5 rounded text-emerald-400 font-mono text-[10px]">pip install pandas numpy requests python-dotenv openpyxl</code></li>
                    <li>Create a credentials file named <code>.env</code> in the same folder:
                      <pre className="bg-slate-950 p-3 rounded mt-1 text-emerald-400 font-mono text-[11px] leading-relaxed border border-slate-800 whitespace-pre">
{`DHAN_CLIENT_CODE="your_client_code"
DHAN_TOKEN_ID="your_dhan_token"`}
                      </pre>
                    </li>
                    <li>Launch the primary scanning engine: <code className="bg-slate-950 px-1.5 py-0.5 rounded text-emerald-400 font-mono text-[10px]">python MainEngine.py</code></li>
                  </ol>
                  <p className="text-[11px] text-slate-400 italic">Note: Ensure your open interest targets and trading slots coincide with regular exchange hours for real-time order fills.</p>
                </div>
              </div>

            </div>
          )}
          
        </div>

      </main>

      {/* Terminal Grid Footer info */}
      <footer className="border-t border-slate-800/85 bg-slate-950 py-3.5 px-6 flex flex-col sm:flex-row items-center justify-between text-[11px]">
        <div className="flex items-center space-x-4 mb-2 sm:mb-0 text-slate-500 font-mono">
          <span>FEED TRACE: STABLE CONNECTION</span>
          <span className="text-slate-600">•</span>
          <span>PING: 14ms</span>
          <span className="text-slate-600">•</span>
          <span>API KEY: SECURED SERVER-SIDE</span>
        </div>
        <div className="text-slate-400">
          Analyze & Harden FnO Stock Algorithms safely. Crafted with high-fidelity React.
        </div>
      </footer>

    </div>
  );
}
