import os
from dotenv import load_dotenv
from Dhan_Tradehull import Tradehull

load_dotenv("cred.env")
client_code = os.getenv("DHAN_CLIENT_CODE")
token_id = os.getenv("DHAN_TOKEN_ID")

Dhan = Tradehull(client_code, token_id)

df = Dhan.get_historical_data("RELIANCE", "NSE", 365)
if df is not None:
    print("SUCCESS")
    print(df.head())
else:
    print("FAILED")
