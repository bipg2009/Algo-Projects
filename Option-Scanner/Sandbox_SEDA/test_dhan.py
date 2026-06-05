from Dhan_Tradehull import Tradehull
import os
from dotenv import load_dotenv
import datetime

load_dotenv('cred.env')
tsl = Tradehull(os.getenv('DHAN_CLIENT_CODE'), os.getenv('DHAN_TOKEN_ID'))
print("Fetching NIFTY...")
to_date = datetime.datetime.now().strftime('%Y-%m-%d')
from_date = (datetime.datetime.now() - datetime.timedelta(days=7)).strftime('%Y-%m-%d')
res = tsl.Dhan.intraday_minute_data("13", tsl.Dhan.INDEX, "INDEX", from_date, to_date)
print("Result:")
print(res)
