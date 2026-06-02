import sys
import os
from dotenv import load_dotenv

for cred_file in ["credentials.env", "cred.env", "credentials.crd"]:
    if os.path.exists(cred_file):
        load_dotenv(cred_file, override=True)
        break

from broker_client import get_live_client
tsl = get_live_client()

try:
    print("Testing place_order for NIFTY 02 JUN 24000 PUT...")
    
    # 24000 PUT is a dummy symbol, DhanHQ needs security_id
    # let's find the security id for NIFTY 02 JUN 24000 PUT
    sym = "NIFTY 02 JUN 24000 PUT"
    df_match = tsl.instrument_df[((tsl.instrument_df['SEM_TRADING_SYMBOL']==sym)|(tsl.instrument_df['SEM_CUSTOM_SYMBOL']==sym))&(tsl.instrument_df['SEM_EXM_EXCH_ID']=="NSE")]
    if df_match.empty:
        print("Could not find", sym)
        sys.exit(1)
        
    security_id = str(df_match.iloc[-1]['SEM_SMST_SECURITY_ID'])
    print(f"Found security_id {security_id} for {sym}")
    
    raw_response = tsl.Dhan.place_order(
        security_id=security_id, 
        exchange_segment=tsl.Dhan.NSE_FNO,
        transaction_type=tsl.Dhan.BUY, 
        quantity=75,
        order_type=tsl.Dhan.LIMIT, 
        product_type=tsl.Dhan.INTRA, 
        price=300.0,
        trigger_price=0
    )
    print("Response:", raw_response)
except Exception as e:
    print("Error:", e)
