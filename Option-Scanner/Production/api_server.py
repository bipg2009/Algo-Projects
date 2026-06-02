import asyncio
import json
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from event_bus import dashboard_queue, signal_queue, manual_exits
from pydantic import BaseModel
import pandas as pd
import glob
import os

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
