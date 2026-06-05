import os
from dotenv import load_dotenv
from Dhan_Tradehull import Tradehull
from STRATEGies.analytics.timeframe_manager import CandleAggregator

load_dotenv("cred.env")
tsl = Tradehull(os.getenv("DHAN_CLIENT_CODE"), os.getenv("DHAN_TOKEN_ID"))
df_1m = tsl.get_intraday_data("NIFTY", "NSE", 1)

print(f"df_1m rows: {len(df_1m)}")
if not df_1m.empty:
    print(df_1m.head(1))
    multi = CandleAggregator.resample_1m_to_multi(df_1m)
    print("3m rows:", len(multi['3m']))
    print("5m rows:", len(multi['5m']))
    print("10m rows:", len(multi['10m']))
    if multi['10m'].empty:
        print("Why is 10m empty?")
