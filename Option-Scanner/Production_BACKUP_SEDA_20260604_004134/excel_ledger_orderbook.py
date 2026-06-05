import pandas as pd
import datetime
import os
import SafetyLogger

LEDGER_FILE = "Ledger.xlsx"

def log_execution_to_excel_ledger(order_id, symbol, action, quantity, price, margin_used, **kwargs):
    trade_data = {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "order_id": order_id,
        "symbol": symbol,
        "action": action,
        "quantity": quantity,
        "price": price,
        "margin_used": margin_used
    }
    trade_data.update(kwargs)
    record_trade(trade_data)

def record_trade(trade_data):
    """
    Appends a completed trade (or initial order) to the Ledger.xlsx file.
    Ensures that critical columns exist and the data is safely persisted.
    """
    try:
        df = pd.DataFrame([trade_data])
        
        # Make sure directory exists if saving to a subfolder
        # os.makedirs(os.path.dirname(LEDGER_FILE), exist_ok=True)
        
        if os.path.exists(LEDGER_FILE):
             existing_df = pd.read_excel(LEDGER_FILE)
             combined_df = pd.concat([existing_df, df], ignore_index=True)
             combined_df.to_excel(LEDGER_FILE, index=False)
        else:
             df.to_excel(LEDGER_FILE, index=False)
             
        SafetyLogger.log_info(f"Recorded trade in ledger: {trade_data.get('symbol')}")
    except Exception as e:
        SafetyLogger.log_error_with_context(
             "excel_ledger", "record_trade", e, {"trade_data": trade_data}
        )
        # Fallback to local csv if excel fails
        try:
             df.to_csv("Ledger_fallback.csv", mode='a', header=not os.path.exists("Ledger_fallback.csv"), index=False)
        except Exception as e:
             SafetyLogger.log_error_with_context("excel_ledger", "csv_fallback_write", e)
