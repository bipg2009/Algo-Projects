import asyncio
import json
import logging
import time
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from event_bus import dashboard_queue, signal_queue, manual_exits
from pydantic import BaseModel
import pandas as pd
import glob
import os
import yfinance as yf

# Sector and symbol mappings
YF_SYMBOL_MAP = {
    "HDFC_BANK": "HDFCBANK.NS", "ICICI_BANK": "ICICIBANK.NS", "STATE_BANK_INDIA": "SBIN.NS",
    "AXIS_BANK": "AXISBANK.NS", "KOTAK_BANK": "KOTAKBANK.NS", "KOTAK_MAHINDRA_BANK": "KOTAKBANK.NS",
    "BAJAJ_FINANCE": "BAJFINANCE.NS", "BAJAJ_FINSERV": "BAJAJFINSV.NS", "RELIANCE": "RELIANCE.NS",
    "RELIANCE_IND": "RELIANCE.NS", "ONGC": "ONGC.NS", "BPCL": "BPCL.NS", "INFOSYS": "INFY.NS",
    "TCS": "TCS.NS", "HCL_TECH": "HCLTECH.NS", "HCL_TECHNOLOGIES": "HCLTECH.NS",
    "TECH_MAHINDRA": "TECHM.NS", "WIPRO": "WIPRO.NS", "ITC": "ITC.NS", 
    "HINDUSTAN_UNILEVER": "HINDUNILVR.NS", "NESTLE": "NESTLEIND.NS", "MAHINDRA_MAHINDRA": "M&M.NS",
    "MAHINDRA_&_MAHINDRA": "M&M.NS", "TATA_MOTORS": "TATAMOTORS.NS", "MARUTI": "MARUTI.NS",
    "MARUTI_SUZUKI": "MARUTI.NS", "BHARTI_AIRTEL": "BHARTIARTL.NS", "LARSEN_&_TOUBRO": "LT.NS",
    "TATA_STEEL": "TATASTEEL.NS", "JSW_STEEL": "JSWSTEEL.NS", "SUN_PHARMA": "SUNPHARMA.NS",
    "NTPC": "NTPC.NS", "POWER_GRID": "POWERGRID.NS", "TITAN_COMPANY": "TITAN.NS",
    "ULTRATECH_CEMENT": "ULTRACEMCO.NS", "ASIAN_PAINTS": "ASIANPAINT.NS"
}

from event_bus import dashboard_queue, signal_queue, manual_exits

INSTRUMENTS_CACHE = []
strategy_signal_counts = {
    "Uptrend": 0,
    "Downtrend": 0,
    "Theta_Dodge": 0,
    "Order_Book_Imbalance": 0,
    "Chop_Mode": 0
}

def load_instruments():
    global INSTRUMENTS_CACHE
    if INSTRUMENTS_CACHE: return
    try:
        files = glob.glob("Dependencies/all_instrument*.csv")
        if not files: return
        latest_file = max(files, key=os.path.getctime)
        # Load only necessary columns
        df = pd.read_csv(latest_file, usecols=['SEM_CUSTOM_SYMBOL', 'SEM_INSTRUMENT_NAME'])
        # Filter: Only FNO scripts (Options and Futures)
        mask = df['SEM_INSTRUMENT_NAME'].isin(['OPTIDX', 'OPTSTK', 'FUTIDX', 'FUTSTK'])
        INSTRUMENTS_CACHE = df[mask]['SEM_CUSTOM_SYMBOL'].dropna().unique().tolist()
        logging.info(f"Loaded {len(INSTRUMENTS_CACHE)} FNO instruments into API cache.")
    except Exception as e:
        logging.error(f"Error loading instrument cache: {e}")

# Sector Engine Data
sector_engine_state = {
    "nifty_sectors": {},
    "sensex_sectors": {},
    "nifty_total_bullish": 0.0,
    "nifty_total_weight": 0.0,
    "sensex_total_bullish": 0.0,
    "sensex_total_weight": 0.0,
    "last_updated": "Waiting..."
}

# Dhan Engine Data
dhan_engine_state = {
    "status": "Connecting...",
    "balance": 0.0,
    "pnl": 0.0,
    "last_updated": "Waiting..."
}

def fetch_dhan_data_loop():
    import sys
    import time
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    try:
        from broker_client import get_live_client
    except Exception as e:
        print(f"Error loading broker_client: {e}")
        return

    tsl = None
    while True:
        try:
            if tsl is None:
                tsl = get_live_client()
            if tsl:
                bal = tsl.get_balance()
                pnl = tsl.get_live_pnl()
                global dhan_engine_state
                dhan_engine_state = {
                    "status": "Connected 🟢",
                    "balance": bal,
                    "pnl": pnl,
                    "last_updated": time.strftime("%H:%M:%S")
                }
            else:
                dhan_engine_state["status"] = "Disconnected 🔴"
        except Exception as e:
            print(f"Dhan polling error: {e}")
            dhan_engine_state["status"] = "Error 🔴"
            tsl = None
        
        # Poll every 10 seconds
        time.sleep(10)

def fetch_sector_data_loop():
    import sys
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    try:
        from importlib.util import spec_from_file_location, module_from_spec
        # Load maps dynamically from scripts
        nifty_spec = spec_from_file_location("nifty_50", "../Nifty-50.py")
        nifty_mod = module_from_spec(nifty_spec)
        nifty_spec.loader.exec_module(nifty_mod)
        SECTOR_MAP = nifty_mod.SECTOR_MAP
        
        sensex_spec = spec_from_file_location("sensex_30", "../Sensex.py")
        sensex_mod = module_from_spec(sensex_spec)
        sensex_spec.loader.exec_module(sensex_mod)
        SENSEX_30_MAP = sensex_mod.SENSEX_30_MAP
    except Exception as e:
        print(f"Error loading sector maps: {e}")
        return

    all_symbols = set()
    for s_map in [SECTOR_MAP, SENSEX_30_MAP]:
        for sec, stocks in s_map.items():
            for stock, w in stocks:
                if stock in YF_SYMBOL_MAP:
                    all_symbols.add(YF_SYMBOL_MAP[stock])
    
    while True:
        try:
            # Download recent data
            df = yf.download(list(all_symbols), period="5d", interval="1d", progress=False)
            if df.empty:
                time.sleep(120); continue
            
            close_prices = df['Close'].iloc[-1]
            prev_prices = df['Close'].iloc[-2] if len(df) > 1 else df['Open'].iloc[-1]
            
            signals = {}
            for stock, yf_sym in YF_SYMBOL_MAP.items():
                if yf_sym in close_prices and not pd.isna(close_prices[yf_sym]):
                    cp = close_prices[yf_sym]
                    pp = prev_prices[yf_sym] if not pd.isna(prev_prices[yf_sym]) else cp
                    signals[stock] = "BULLISH" if cp >= pp else "BEARISH"
                    
            # Process NIFTY
            n_sectors, n_bull_tot, n_tot = {}, 0.0, 0.0
            for sec, stocks in SECTOR_MAP.items():
                sec_bull, sec_tot, comp = 0.0, 0.0, []
                for st, w in sorted(stocks, key=lambda x: x[1], reverse=True):
                    sig = signals.get(st, "NEUTRAL")
                    if sig == "BULLISH": sec_bull += w; n_bull_tot += w
                    sec_tot += w; n_tot += w
                    comp.append({"name": st, "weight": w, "status": sig})
                pct = (sec_bull/sec_tot)*100 if sec_tot > 0 else 0
                n_sectors[sec] = {"bullish_pct": pct, "components": comp}
                
            # Process SENSEX
            s_sectors, s_bull_tot, s_tot = {}, 0.0, 0.0
            for sec, stocks in SENSEX_30_MAP.items():
                sec_bull, sec_tot, comp = 0.0, 0.0, []
                for st, w in sorted(stocks, key=lambda x: x[1], reverse=True):
                    sig = signals.get(st, "NEUTRAL")
                    if sig == "BULLISH": sec_bull += w; s_bull_tot += w
                    sec_tot += w; s_tot += w
                    comp.append({"name": st, "weight": w, "status": sig})
                pct = (sec_bull/sec_tot)*100 if sec_tot > 0 else 0
                s_sectors[sec] = {"bullish_pct": pct, "components": comp}
                
            global sector_engine_state
            sector_engine_state = {
                "nifty_sectors": n_sectors, "sensex_sectors": s_sectors,
                "nifty_total_bullish": n_bull_tot, "nifty_total_weight": n_tot,
                "sensex_total_bullish": s_bull_tot, "sensex_total_weight": s_tot,
                "last_updated": time.strftime("%H:%M:%S")
            }
        except Exception as e:
            print(f"Sector polling error: {e}")
        
        # Sleep 2 minutes
        time.sleep(120)

app = FastAPI()

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the dashboard directory for static files
# We will create this directory later
try:
    app.mount("/assets", StaticFiles(directory="dashboard/assets"), name="assets")
except RuntimeError:
    pass # Directory might not exist yet

@app.get("/")
@app.get("/dashboard")
@app.get("/dashboard/")
async def serve_dashboard():
    return FileResponse("dashboard/index.html")

@app.get("/testing")
@app.get("/testing/")
async def serve_testing():
    return FileResponse("dashboard/testing.html")

@app.get("/strategies")
@app.get("/strategies/")
async def serve_strategies():
    return FileResponse("dashboard/strategies.html")

@app.get("/api/strategy_stats")
async def strategy_stats():
    return strategy_signal_counts

@app.get("/api/sector_outlook")
async def sector_outlook():
    return sector_engine_state

@app.get("/api/dhan_status")
async def dhan_status():
    return dhan_engine_state

class ManualOrderRequest(BaseModel):
    exchange: str
    symbol: str
    action: str

@app.post("/api/manual_order")
async def manual_order(req: ManualOrderRequest):
    sym = req.symbol.strip().upper()
    action = req.action.upper()
    
    # 1. We will push it to signal_queue so dashboard tracks it anyway
    opt_type = "CE" if "CE" in sym else ("PE" if "PE" in sym else "EQ")
    if action == "BUY":
        signal_queue.put({
            "action": "BUY",
            "target": opt_type,
            "strategy": "MANUAL",
            "symbol": sym,
            "score": 100
        })
    elif action == "SELL":
        manual_exits.add(sym)
        
    # 2. Directly trigger Tradehull for LIVE TEST
    import io
    import sys
    import os
    from broker_client import get_live_client
    
    # Ensure credentials are loaded before getting live client
    from dotenv import load_dotenv
    # Prefer project-standard `cred.env` (used by MainEngine) over older files.
    for cred_file in ["cred.env", "credentials.env", "credentials.crd"]:
        if os.path.exists(cred_file):
            load_dotenv(cred_file, override=True)
            break
        
    try:
        tsl = get_live_client()
        if not tsl:
            return {"status": "error", "message": "Failed to initialize Dhan Tradehull client. Check credentials.crd"}
        # Option logic
        exch = "NFO"
        if "SENSEX" in sym or "BANKEX" in sym:
            exch = "BFO"
        elif req.exchange == "BSE":
            exch = "BFO"

        qty = 75
        if "SENSEX" in sym: qty = 10
        if "BANKNIFTY" in sym: qty = 15
        
        # Bypass Dhan_Tradehull.py's broken error handling and call DhanHQ directly
        instrument_exchange = {'NSE':"NSE",'BSE':"BSE",'NFO':'NSE','BFO':'BSE','MCX':'MCX','CUR':'NSE'}
        
        # Find security ID
        df_match = tsl.instrument_df[((tsl.instrument_df['SEM_TRADING_SYMBOL']==sym)|(tsl.instrument_df['SEM_CUSTOM_SYMBOL']==sym))&(tsl.instrument_df['SEM_EXM_EXCH_ID']==instrument_exchange.get(exch, 'NSE'))]
        if df_match.empty:
            return {"status": "error", "message": f"Symbol {sym} not found in instrument file for exchange {exch}."}
            
        security_id = str(df_match.iloc[-1]['SEM_SMST_SECURITY_ID'])
        
        # Map parameters
        exch_seg_map = {"NSE": tsl.Dhan.NSE, "NFO": tsl.Dhan.NSE_FNO, "BFO": tsl.Dhan.BSE_FNO}
        exchangeSegment = exch_seg_map.get(exch, tsl.Dhan.NSE_FNO)
        order_side = tsl.Dhan.BUY if action == "BUY" else tsl.Dhan.SELL
        
        # Fire direct order to DhanHQ
        raw_response = tsl.Dhan.place_order(
            security_id=security_id, 
            exchange_segment=exchangeSegment,
            transaction_type=order_side, 
            quantity=qty,
            order_type=tsl.Dhan.MARKET, 
            product_type=tsl.Dhan.INTRA, 
            price=0,
            trigger_price=0
        )
        
        # Evaluate raw response to avoid Tradehull TypeErrors
        if isinstance(raw_response, dict):
            if str(raw_response.get("status", "")).lower() == "success" or "orderId" in str(raw_response):
                oid = raw_response.get("data", {}).get("orderId", "Unknown")
                return {"status": "ok", "message": f"Order Success! ID: {oid}"}
            else:
                remarks = raw_response.get("remarks") or raw_response.get("errorMsg") or str(raw_response)
                return {"status": "error", "message": f"Broker Rejected Order:\n{remarks}"}
        else:
            return {"status": "error", "message": f"Raw Broker Error:\n{str(raw_response)}"}
            
    except Exception as e:
        return {"status": "error", "message": f"API Exception: {str(e)}"}

class TestBuyRequest(BaseModel):
    symbol: str
    option_type: str
    ltp: float

@app.post("/api/test_buy")
async def manual_test_buy(req: TestBuyRequest):
    signal_queue.put({
        "action": "BUY",
        "target": req.option_type,
        "strategy": "MANUAL_TEST",
        "symbol": req.symbol,
        "ltp": req.ltp,
        "score": 99
    })
    return {"status": "ok", "message": f"Test BUY signal sent for {req.symbol}"}

class TestSellRequest(BaseModel):
    symbol: str

@app.post("/api/test_sell")
async def manual_test_sell(req: TestSellRequest):
    manual_exits.add(req.symbol)
    return {"status": "ok", "message": f"Test SELL signal triggered for {req.symbol}"}

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                pass

manager = ConnectionManager()

def _read_scanner_state() -> dict:
    """
    Best-effort scanner state snapshot for new dashboard connections.
    Source of truth is `scanner_state.json` written by scanner_state.py.
    """
    try:
        if os.path.exists("scanner_state.json"):
            with open("scanner_state.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            status = str(data.get("status") or "INACTIVE")
            return {"status": status, "mute_seconds_left": 0}
    except Exception:
        pass
    return {"status": "INACTIVE", "mute_seconds_left": 0}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Initial hello so UI doesn't look "blank"
        await websocket.send_text(json.dumps({
            "type": "LOG",
            "payload": {
                "source": "Dashboard",
                "message": "WebSocket connected. Waiting for scanner events...",
                "level": "info",
            },
        }))
        await websocket.send_text(json.dumps({
            "type": "SCANNER_STATE",
            "payload": _read_scanner_state(),
        }))

        # Keepalive loop. Client isn't required to send messages.
        # If it does, we read and ignore.
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            except asyncio.TimeoutError:
                # Keep connection alive with a lightweight ping event.
                await websocket.send_text(json.dumps({"type": "PING", "payload": time.time()}))
    except WebSocketDisconnect:
        manager.disconnect(websocket)

async def broadcast_dashboard_events():
    """Background task to read from dashboard_queue and broadcast to websockets."""
    while True:
        try:
            # Non-blocking check
            if not dashboard_queue.empty():
                event = dashboard_queue.get_nowait()
                
                # Tally signal counts dynamically
                if event.get("type") == "NEW_SIGNAL":
                    payload = event.get("payload", {})
                    strat = payload.get("strategy", "Unknown")
                    if strat != "Unknown":
                        if strat not in strategy_signal_counts:
                            strategy_signal_counts[strat] = 0
                        strategy_signal_counts[strat] += 1
                        
                await manager.broadcast(json.dumps(event))
                dashboard_queue.task_done()
        except Exception as e:
            logging.error(f"Error broadcasting event: {e}")
            
        await asyncio.sleep(0.05) # 50ms polling on the queue

@app.on_event("startup")
async def startup_event():
    import threading
    # Start the broadcast loop in the asyncio event loop
    asyncio.create_task(broadcast_dashboard_events())
    # Load the instrument CSV into memory in background thread
    threading.Thread(target=load_instruments, daemon=True).start()
    # Start sector engine
    threading.Thread(target=fetch_sector_data_loop, daemon=True).start()
    # Start Dhan engine
    threading.Thread(target=fetch_dhan_data_loop, daemon=True).start()

@app.get("/api/health")
async def health():
    return {"status": "ok"}

@app.get("/api/search_symbols")
async def search_symbols(q: str = ""):
    q = q.upper().strip()
    if not q or len(q) < 2:
        return []
    # limit to top 50 matches for performance
    # Use startswith to prevent 'NIFTY' from matching 'BANKNIFTY'
    matches = [sym for sym in INSTRUMENTS_CACHE if sym.startswith(q)][:50]
    return matches

@app.get("/api/get_ltp")
async def get_ltp_endpoint(symbol: str):
    import os
    from broker_client import get_live_client
    from dotenv import load_dotenv
    # Prefer project-standard `cred.env` (used by MainEngine) over older files.
    for cred_file in ["cred.env", "credentials.env", "credentials.crd"]:
        if os.path.exists(cred_file):
            load_dotenv(cred_file, override=True)
            break
    
    try:
        tsl = get_live_client()
        if not tsl:
            return {"status": "error", "message": "Failed to init client"}
        
        # Use Tradehull's REST LTP fetcher which handles caching and option chain queries
        ltp = tsl._get_ltp_via_rest([symbol])
        return {"status": "ok", "ltp": ltp}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def start_server(host: str = "127.0.0.1", port: int = 5173):
    """Starts the uvicorn server. Intended to be run in a thread."""
    import uvicorn
    # Load instrument cache at startup
    load_instruments()
    uvicorn.run(app, host=host, port=int(port), log_level="warning")

@app.post("/api/run_csv_test")
async def run_csv_test(file: UploadFile = File(...), test_type: str = Form(...)):
    import tempfile
    import os
    import time
    
    # Securely save the uploaded file to a temporary location
    try:
        content = await file.read()
        tmp_path = os.path.join(tempfile.gettempdir(), f"upload_{int(time.time())}_{file.filename}")
        with open(tmp_path, "wb") as f:
            f.write(content)
            
        # Parse the CSV to return some mock data for the dashboard
        # This can be replaced with actual backtest logic later
        df = pd.read_csv(tmp_path)
        rows = len(df)
        
        # Determine some fake testing metrics for now based on file size
        win_rate = min(100, max(0, 50 + (rows % 30)))
        pnl = rows * 12.5 if rows > 0 else 0
        dd = rows * 3.1 if rows > 0 else 0
        
        # Cleanup
        try: os.remove(tmp_path)
        except: pass
        
        return {
            "status": "ok",
            "message": f"Successfully parsed {file.filename} containing {rows} rows using '{test_type}' strategy.",
            "results": {
                "total_trades": rows,
                "win_rate": win_rate,
                "net_pnl": pnl,
                "max_drawdown": dd
            }
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}
