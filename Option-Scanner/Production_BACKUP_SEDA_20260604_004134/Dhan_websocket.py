import pandas as pd
import datetime
import os
import time
import xlwings as xw
import psutil
import json
import logging
import traceback
from logging.handlers import RotatingFileHandler
from dhanhq import dhanhq, marketfeed

from System_Config import SENSEX_CHAIN_ENABLED
import SafetyLogger

def setup_websocket_logger():
    if not os.path.exists('Dependencies/log_files'):
        os.makedirs('Dependencies/log_files')
    logger = logging.getLogger('DhanWebsocket')
    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler('Dependencies/log_files/websocket.log', maxBytes=2000000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

log = setup_websocket_logger()

# Maintain the workbook globally if needed
wb_global = None

def get_client_credentials():
    try:
        from dotenv import load_dotenv
        load_dotenv()
        client_code = os.getenv('DHAN_CLIENT_ID')
        token = os.getenv('DHAN_ACCESS_TOKEN')
        return client_code, token
    except Exception as e:
        SafetyLogger.log_error("Dhan_websocket", "get_client_credentials", e)
        return None, None

def initialize_websocket_excel():
    global wb_global
    excel_file = "Websocket.xlsx"
    
    try:
        if os.path.exists(excel_file):
             log.info(f"Connecting to existing {excel_file}")
             # try to attach
             wb = xw.Book(excel_file)
        else:
             log.info(f"Creating new {excel_file}")
             wb = xw.Book()
             wb.save(excel_file)
             
        sheet = wb.sheets["LTP"] if "LTP" in [s.name for s in wb.sheets] else wb.sheets.add("LTP")
        
        # Verify Headers
        if sheet.range("A1").value != "Script Name":
            sheet.range("A1").value = ["Script Name", "Exchange", "LTP"]
            
        wb_global = wb
        return wb_global, sheet
    except Exception as e:
         log.error(f"Excel creation error: {e}")
         SafetyLogger.log_error("Dhan_websocket", "initialize_websocket_excel", e)
         return None, None

def read_symbols_from_sheet(sheet):
    try:
        col_A = sheet.range('A2:A100').value
        col_B = sheet.range('B2:B100').value
        
        symbols = []
        for name, exch in zip(col_A, col_B):
            if name and str(name).strip() != "":
                symbols.append((str(name).strip(), str(exch).strip()))
        return symbols
    except Exception as e:
         log.error(f"Error reading symbols: {e}")
         return []

def run_websocket():
    client, token = get_client_credentials()
    if not client or not token:
        log.error("Missing Dhan credentials.")
        return
        
    wb, sheet = initialize_websocket_excel()
    if not sheet:
        return
        
    import Dhan_Tradehull as dth
    tradehull_api = dth.Tradehull(client, token)
    
    # We poll the sheet for new symbols to subscribe
    subscribed_symbols = set()
    
    instrument_df = tradehull_api.get_instrument_file()
    
    # Websocket subscription map (Security ID -> row_index in Excel)
    security_to_row = {}
    
    # Start Market Feed
    feed = None
    
    def on_connect(instance):
        log.info("Dhan Websocket Connected")
        
    def on_message(instance, message):
        try:
             # Look for LTP
             if "LTP" in message or "last_price" in message:
                 sec_id = message.get("security_id")
                 ltp = message.get("LTP") or message.get("last_price")
                 
                 if sec_id and sec_id in security_to_row:
                     row_idx = security_to_row[sec_id]
                     sheet.range(f"C{row_idx}").value = float(ltp)
        except Exception as e:
             pass
    
    def on_error(instance, error):
        log.error(f"Websocket Error: {error}")
        SafetyLogger.log_info(f"Websocket Error: {error}")
        
    def on_close(instance):
        log.warning("Websocket Closed")
    
    try:
        devices = []
        # Connect
        # According to original API
        # Dhan context is needed for MarketFeed
        from dhanhq import DhanContext
        dhan_ctx = DhanContext(client, token)
        
        feed = marketfeed.DhanFeed(
            client_id=client,
            access_token=token,
            instruments=[], # will subscribe later
            subscription_code=marketfeed.Ticker,
            on_connect=on_connect,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        feed.run_in_background()
        
        # Exponential backoff loop
        backoff = 1
        while True:
            try:
                symbols = read_symbols_from_sheet(sheet)
                instruments_to_sub = []
                
                for idx, (sym, exch) in enumerate(symbols):
                    row_idx = idx + 2
                    
                    if sym not in subscribed_symbols:
                        # Find Security ID
                        # Example: NSE F&O
                        exch_id = "NSE" if (exch in ["NFO", "NSE", "NSE_IDX"]) else "BSE"
                        
                        match = instrument_df[
                            ((instrument_df['SEM_CUSTOM_SYMBOL'] == sym) | (instrument_df['SEM_TRADING_SYMBOL'] == sym)) &
                            (instrument_df['SEM_EXM_EXCH_ID'] == exch_id)
                        ]
                        
                        if not match.empty:
                            sec_id = int(match.iloc[-1]['SEM_SMST_SECURITY_ID'])
                            segment = int(match.iloc[-1]['SEM_EXM_EXCH_ID']) # This might need mapping to marketfeed enum
                            
                            # Just an approximation
                            if exch == "NFO": seg_val = feed.NSE_FNO
                            elif exch == "BFO": seg_val = feed.BSE_FNO
                            elif exch == "NSE_IDX": seg_val = feed.NSE_IDX
                            else: seg_val = feed.NSE
                            
                            instruments_to_sub.append((seg_val, sec_id))
                            security_to_row[sec_id] = row_idx
                            subscribed_symbols.add(sym)
                
                if instruments_to_sub:
                     log.info(f"Subscribing to {len(instruments_to_sub)} new instruments")
                     feed.subscribe_symbols(marketfeed.Ticker, instruments_to_sub)
                     
                time.sleep(2)
                backoff = 1 # reset on success
                
            except Exception as e:
                 log.error(f"Error in Websocket polling thread: {e}")
                 time.sleep(backoff)
                 backoff = min(backoff * 2, 60)
                 
    except Exception as top_e:
        SafetyLogger.log_error("Dhan_websocket", "run_websocket_outer", top_e)
        log.error(f"Outer exception: {top_e}")

if __name__ == "__main__":
    run_websocket()
