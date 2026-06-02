import os
from dotenv import load_dotenv
import Broker_Dhan

load_dotenv("cred.env")
tsl = Broker_Dhan.Tradehull(client_code=os.getenv("DHAN_CLIENT_CODE"), token_id=os.getenv("DHAN_TOKEN_ID"))

# Find any NIFTY option ID from NSE_FNO to test
print("Starting qty tests on Nifty Options...")
print("Testing 1 (Lot):", tsl.Dhan.place_order(security_id="42932", exchange_segment=tsl.Dhan.NSE_FNO, transaction_type=tsl.Dhan.BUY, quantity=1, order_type=tsl.Dhan.MARKET, product_type=tsl.Dhan.INTRA, price=0))
print("Testing 25 (Shares):", tsl.Dhan.place_order(security_id="42932", exchange_segment=tsl.Dhan.NSE_FNO, transaction_type=tsl.Dhan.BUY, quantity=25, order_type=tsl.Dhan.MARKET, product_type=tsl.Dhan.INTRA, price=0))
print("Testing 75 (Shares):", tsl.Dhan.place_order(security_id="42932", exchange_segment=tsl.Dhan.NSE_FNO, transaction_type=tsl.Dhan.BUY, quantity=75, order_type=tsl.Dhan.MARKET, product_type=tsl.Dhan.INTRA, price=0))
