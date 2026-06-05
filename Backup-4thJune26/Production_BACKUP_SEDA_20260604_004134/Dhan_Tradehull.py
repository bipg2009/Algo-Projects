import mibian
import datetime
import pandas as pd
import traceback
import xlwings as xw
import requests
import pdb
import os
import time
import json
from pprint import pprint
import logging
import warnings
from typing import Tuple, Dict
from dhanhq import DhanContext, dhanhq

warnings.filterwarnings("ignore", category=FutureWarning)

class Tradehull:    
	clientCode                                      : str
	interval_parameters                             : dict
	instrument_file                                 : pd.core.frame.DataFrame
	step_df                                         : pd.core.frame.DataFrame
	index_step_dict                                 : dict
	index_underlying                                : dict
	call                                            : str
	put                                             : str

	def __init__(self,ClientCode:str,token_id:str):
		'''
		Clientcode                              = The ClientCode in string 
		token_id                                = The token_id in string 
		'''
		date_str = str(datetime.datetime.now().today().date())
		if not os.path.exists('Dependencies/log_files'):
			os.makedirs('Dependencies/log_files')
		file = 'Dependencies/log_files/logs' + date_str + '.log'
		logging.basicConfig(filename=file, level=logging.DEBUG,format='%(levelname)s:%(asctime)s:%(threadName)-10s:%(message)s') 
		self.logger = logging.getLogger()
		logging.info('Dhan.py  started system')
		logging.getLogger("requests").setLevel(logging.WARNING)
		logging.getLogger("urllib3").setLevel(logging.WARNING)
		self.logger.info("STARTED THE PROGRAM")

		try:
			self.status 							= dict()
			self.token_and_exchange 				= dict()
			self.get_login(ClientCode,token_id)
			# Websocket.xlsx is opened by Dhan_websocket.py; attach on demand in get_ltp()
			self.wb                                 = None
			self.sheet 								= None
			self.token_and_exchange 				= {}
			self.interval_parameters                = {'minute':  60,'2minute':  120,'3minute':  180,'4minute':  240,'5minute':  300,'day':  86400,'10minute':  600,'15minute':  900,'30minute':  1800,'60minute':  3600,'day':86400}
			self.index_underlying                   = {"NIFTY 50":"NIFTY","NIFTY BANK":"BANKNIFTY","NIFTY FIN SERVICE":"FINNIFTY","NIFTY MID SELECT":"MIDCPNIFTY"}
			self.segment_dict                       = {"NSECM": 1, "NSEFO": 2, "NSECD": 3, "BSECM": 11, "BSEFO": 12, "MCXFO": 51}
			self.index_step_dict                    = {'MIDCPNIFTY':25,'SENSEX':100,'BANKEX':100,'NIFTY': 50, 'NIFTY 50': 50, 'NIFTY BANK': 100, 'BANKNIFTY': 100, 'NIFTY FIN SERVICE': 50, 'FINNIFTY': 50}
			self.token_dict 						= {'NIFTY':{'token':26000,'exchange':'NSECM'},'NIFTY 50':{'token':26000,'exchange':'NSECM'},'BANKNIFTY':{'token':26001,'exchange':'NSECM'},'NIFTY BANK':{'token':26001,'exchange':'NSECM'},'FINNIFTY':{'token':26034,'exchange':'NSECM'},'NIFTY FIN SERVICE':{'token':26034,'exchange':'NSECM'},'MIDCPNIFTY':{'token':26121,'exchange':'NSECM'},'NIFTY MID SELECT':{'token':26121,'exchange':'NSECM'},'SENSEX':{'token':26065,'exchange':'BSECM'},'BANKEX':{'token':26118,'exchange':'BSECM'}}
			self.intervals_dict 					= {'minute': 3, '2minute':4, '3minute': 4, '5minute': 5, '10minute': 10,'15minute': 15, '30minute': 25, '60minute': 40, 'day': 80}
			self.stock_step_df						= {'NIFTY': 50, 'NIFTY 50': 50, 'NIFTY BANK': 100, 'BANKNIFTY': 100, 'NIFTY FIN SERVICE': 50, 'FINNIFTY': 50, 'AARTIIND': 5, 'ABB': 50, 'ABBOTINDIA': 250, 'ACC': 20, 'ADANIENT': 50, 'ADANIPORTS': 10, 'ALKEM': 20, 'AMBUJACEM': 10, 'APOLLOHOSP': 50, 'APOLLOTYRE': 5, 'ASHOKLEY': 1, 'ASIANPAINT': 20, 'ASTRAL': 20, 'ATUL': 50, 'AUBANK': 10, 'AUROPHARMA': 10, 'AXISBANK': 10, 'BAJAJ-AUTO': 50, 'BAJAJFINSV': 20, 'BAJFINANCE': 50, 'BALKRISIND': 20, 'BALRAMCHIN': 5, 'BATAINDIA': 10, 'BEL': 1, 'BERGEPAINT': 5, 'BHARATFORG': 10, 'BHARTIARTL': 10, 'BHEL': 1, 'BOSCHLTD': 100, 'BPCL': 5, 'BRITANNIA': 50, 'BSOFT': 10, 'CANBK': 5, 'CANFINHOME': 10, 'CHOLAFIN': 10, 'CIPLA': 10, 'COFORGE': 100, 'COLPAL': 10, 'CONCOR': 10, 'COROMANDEL': 10, 'CUB': 1, 'CUMMINSIND': 20, 'DABUR': 5, 'DALBHARAT': 20, 'DEEPAKNTR': 20, 'DELTACORP': 5, 'DIVISLAB': 50, 'DIXON': 50, 'DLF': 5, 'DRREDDY': 50, 'EICHERMOT': 50, 'ESCORTS': 20, 'FEDERALBNK': 1, 'GAIL': 1, 'GLENMARK': 10, 'GMRINFRA': 1, 'GNFC': 10, 'GODREJCP': 10, 'GODREJPROP': 20, 'GRASIM': 20, 'GUJGASLTD': 5, 'HAL': 20, 'HAVELLS': 10, 'HCLTECH': 10, 'HDFCAMC': 20, 'HDFCBANK': 10, 'HDFCLIFE': 5, 'HEROMOTOCO': 20, 'HINDALCO': 5, 'HINDCOPPER': 2.5, 'HINDUNILVR': 20, 'ICICIBANK': 10, 'ICICIGI': 10, 'ICICIPRULI': 5, 'IDEA': 1, 'IDFC': 1, 'IDFCFIRSTB': 1, 'IEX': 1, 'IGL': 5, 'INDHOTEL': 5, 'INDIAMART': 50, 'INDIGO': 20, 'INDUSINDBK': 20, 'INFY': 10, 'IOC': 1, 'IPCALAB': 10, 'IRCTC': 10, 'ITC': 5, 'JINDALSTEL': 10, 'JKCEMENT': 50, 'JSWSTEEL': 10, 'JUBLFOOD': 5, 'KOTAKBANK': 20, 'L&TFH': 1, 'LALPATHLAB': 20, 'LAURUSLABS': 5, 'LICHSGFIN': 5, 'LT': 20, 'LTIM': 50, 'LTTS': 50, 'LUPIN': 10, 'M&M': 10, 'M&MFIN': 5, 'MARICO': 5, 'MARUTI': 100, 'MCDOWELL-N': 10, 'MCX': 20, 'METROPOLIS': 20, 'MFSL': 10, 'MGL': 10, 'MOTHERSON': 1, 'MPHASIS': 20, 'MRF': 500, 'MUTHOOTFIN': 10, 'NATIONALUM': 1, 'NAUKRI': 50, 'NAVINFLUOR': 50, 'NESTLEIND': 100, 'NMDC': 1, 'NTPC': 1, 'OBEROIRLTY': 10, 'OFSS': 20, 'ONGC': 2.5, 'PAGEIND': 500, 'PEL': 10, 'PERSISTENT': 50, 'PIDILITIND': 20, 'PIIND': 50, 'PNB': 1, 'POLYCAB': 50, 'PVRINOX': 20, 'RAMCOCEM': 10, 'RELIANCE': 20, 'SAIL': 1, 'SBICARD': 10, 'SBILIFE': 10, 'SBIN': 5, 'SHREECEM': 250, 'SHRIRAMFIN': 20, 'SIEMENS': 50, 'SRF': 20, 'SUNPHARMA': 10, 'SUNTV': 5, 'SYNGENE': 10, 'TATACHEM': 10, 'TATACOMM': 20, 'TATACONSUM': 5, 'TATAMOTORS': 5, 'TATASTEEL': 1, 'TCS': 20, 'TECHM': 10, 'TITAN': 20, 'TORNTPHARM': 20, 'TRENT': 20, 'TVSMOTOR': 20, 'UBL': 10, 'ULTRACEMCO': 50, 'UPL': 5, 'VOLTAS': 10, 'ZYDUSLIFE': 5, 'ABCAPITAL': 2.5, 'ABFRL': 2.5, 'BANDHANBNK': 2.5, 'BANKBARODA': 2.5, 'BIOCON': 2.5, 'CHAMBLFERT': 5, 'COALINDIA': 2.5, 'CROMPTON': 2.5, 'EXIDEIND': 2.5, 'GRANULES': 2.5, 'HINDPETRO': 5, 'IBULHSGFIN': 2.5, 'INDIACEM': 2.5, 'INDUSTOWER': 2.5, 'MANAPPURAM': 2.5, 'PETRONET': 2.5, 'PFC': 2.5, 'POWERGRID': 2.5, 'RBLBANK': 2.5, 'RECLTD': 2.5, 'TATAPOWER': 5, 'VEDL': 2.5, 'WIPRO': 2.5, 'ZEEL': 2.5, 'AMARAJABAT': 10, 'APLLTD': 10, 'CADILAHC': 5, 'HDFC': 50, 'LTI': 100, 'MINDTREE': 20, 'MOTHERSUMI': 5, 'NAM-INDIA': 5, 'PFIZER': 50, 'PVR': 20, 'SRTRANSFIN': 20, 'TORNTPOWER': 5}

			try:
				# self.step_df                        = pd.read_excel("https://archives.nseindia.com/content/fo/sos_scheme.xls")
				step_value_dict                    = {'NIFTY': 50, 'NIFTY 50': 50, 'NIFTY BANK': 100, 'BANKNIFTY': 100, 'NIFTY FIN SERVICE': 50, 'FINNIFTY': 50, 'AARTIIND': 5, 'ABB': 50, 'ABBOTINDIA': 250, 'ACC': 20, 'ADANIENT': 50, 'ADANIPORTS': 10, 'ALKEM': 20, 'AMBUJACEM': 10, 'APOLLOHOSP': 50, 'APOLLOTYRE': 5, 'ASHOKLEY': 1, 'ASIANPAINT': 20, 'ASTRAL': 20, 'ATUL': 50, 'AUBANK': 10, 'AUROPHARMA': 10, 'AXISBANK': 10, 'BAJAJ-AUTO': 50, 'BAJAJFINSV': 20, 'BAJFINANCE': 50, 'BALKRISIND': 20, 'BALRAMCHIN': 5, 'BATAINDIA': 10, 'BEL': 1, 'BERGEPAINT': 5, 'BHARATFORG': 10, 'BHARTIARTL': 10, 'BHEL': 1, 'BOSCHLTD': 100, 'BPCL': 5, 'BRITANNIA': 50, 'BSOFT': 10, 'CANBK': 5, 'CANFINHOME': 10, 'CHOLAFIN': 10, 'CIPLA': 10, 'COFORGE': 100, 'COLPAL': 10, 'CONCOR': 10, 'COROMANDEL': 10, 'CUB': 1, 'CUMMINSIND': 20, 'DABUR': 5, 'DALBHARAT': 20, 'DEEPAKNTR': 20, 'DELTACORP': 5, 'DIVISLAB': 50, 'DIXON': 50, 'DLF': 5, 'DRREDDY': 50, 'EICHERMOT': 50, 'ESCORTS': 20, 'FEDERALBNK': 1, 'GAIL': 1, 'GLENMARK': 10, 'GMRINFRA': 1, 'GNFC': 10, 'GODREJCP': 10, 'GODREJPROP': 20, 'GRASIM': 20, 'GUJGASLTD': 5, 'HAL': 20, 'HAVELLS': 10, 'HCLTECH': 10, 'HDFCAMC': 20, 'HDFCBANK': 10, 'HDFCLIFE': 5, 'HEROMOTOCO': 20, 'HINDALCO': 5, 'HINDCOPPER': 2.5, 'HINDUNILVR': 20, 'ICICIBANK': 10, 'ICICIGI': 10, 'ICICIPRULI': 5, 'IDEA': 1, 'IDFC': 1, 'IDFCFIRSTB': 1, 'IEX': 1, 'IGL': 5, 'INDHOTEL': 5, 'INDIAMART': 50, 'INDIGO': 20, 'INDUSINDBK': 20, 'INFY': 10, 'IOC': 1, 'IPCALAB': 10, 'IRCTC': 10, 'ITC': 5, 'JINDALSTEL': 10, 'JKCEMENT': 50, 'JSWSTEEL': 10, 'JUBLFOOD': 5, 'KOTAKBANK': 20, 'L&TFH': 1, 'LALPATHLAB': 20, 'LAURUSLABS': 5, 'LICHSGFIN': 5, 'LT': 20, 'LTIM': 50, 'LTTS': 50, 'LUPIN': 10, 'M&M': 10, 'M&MFIN': 5, 'MARICO': 5, 'MARUTI': 100, 'MCDOWELL-N': 10, 'MCX': 20, 'METROPOLIS': 20, 'MFSL': 10, 'MGL': 10, 'MOTHERSON': 1, 'MPHASIS': 20, 'MRF': 500, 'MUTHOOTFIN': 10, 'NATIONALUM': 1, 'NAUKRI': 50, 'NAVINFLUOR': 50, 'NESTLEIND': 100, 'NMDC': 1, 'NTPC': 1, 'OBEROIRLTY': 10, 'OFSS': 20, 'ONGC': 2.5, 'PAGEIND': 500, 'PEL': 10, 'PERSISTENT': 50, 'PIDILITIND': 20, 'PIIND': 50, 'PNB': 1, 'POLYCAB': 50, 'PVRINOX': 20, 'RAMCOCEM': 10, 'RELIANCE': 20, 'SAIL': 1, 'SBICARD': 10, 'SBILIFE': 10, 'SBIN': 5, 'SHREECEM': 250, 'SHRIRAMFIN': 20, 'SIEMENS': 50, 'SRF': 20, 'SUNPHARMA': 10, 'SUNTV': 5, 'SYNGENE': 10, 'TATACHEM': 10, 'TATACOMM': 20, 'TATACONSUM': 5, 'TATAMOTORS': 5, 'TATASTEEL': 1, 'TCS': 20, 'TECHM': 10, 'TITAN': 20, 'TORNTPHARM': 20, 'TRENT': 20, 'TVSMOTOR': 20, 'UBL': 10, 'ULTRACEMCO': 50, 'UPL': 5, 'VOLTAS': 10, 'ZYDUSLIFE': 5, 'ABCAPITAL': 2.5, 'ABFRL': 2.5, 'BANDHANBNK': 2.5, 'BANKBARODA': 2.5, 'BIOCON': 2.5, 'CHAMBLFERT': 5, 'COALINDIA': 2.5, 'CROMPTON': 2.5, 'EXIDEIND': 2.5, 'GRANULES': 2.5, 'HINDPETRO': 5, 'IBULHSGFIN': 2.5, 'INDIACEM': 2.5, 'INDUSTOWER': 2.5, 'MANAPPURAM': 2.5, 'PETRONET': 2.5, 'PFC': 2.5, 'POWERGRID': 2.5, 'RBLBANK': 2.5, 'RECLTD': 2.5, 'TATAPOWER': 5, 'VEDL': 2.5, 'WIPRO': 2.5, 'ZEEL': 2.5, 'AMARAJABAT': 10, 'APLLTD': 10, 'CADILAHC': 5, 'HDFC': 50, 'LTI': 100, 'MINDTREE': 20, 'MOTHERSUMI': 5, 'NAM-INDIA': 5, 'PFIZER': 50, 'PVR': 20, 'SRTRANSFIN': 20, 'TORNTPOWER': 5}
				self.step_df                        = pd.DataFrame.from_dict(step_value_dict, orient='index')
				self.step_df                        = self.step_df.reset_index()
				self.step_df.rename({"index": "Symbol", 0: "Applicable Step value"}, axis='columns', inplace =True)				
			except Exception as e:
				print("step Value DF is not generated due to Error from NSE India site: ", e)
				print("Collecting step values from program memory.")
				step_value_dict                    = {'NIFTY': 50, 'NIFTY 50': 50, 'NIFTY BANK': 100, 'BANKNIFTY': 100, 'NIFTY FIN SERVICE': 50, 'FINNIFTY': 50, 'AARTIIND': 5, 'ABB': 50, 'ABBOTINDIA': 250, 'ACC': 20, 'ADANIENT': 50, 'ADANIPORTS': 10, 'ALKEM': 20, 'AMBUJACEM': 10, 'APOLLOHOSP': 50, 'APOLLOTYRE': 5, 'ASHOKLEY': 1, 'ASIANPAINT': 20, 'ASTRAL': 20, 'ATUL': 50, 'AUBANK': 10, 'AUROPHARMA': 10, 'AXISBANK': 10, 'BAJAJ-AUTO': 50, 'BAJAJFINSV': 20, 'BAJFINANCE': 50, 'BALKRISIND': 20, 'BALRAMCHIN': 5, 'BATAINDIA': 10, 'BEL': 1, 'BERGEPAINT': 5, 'BHARATFORG': 10, 'BHARTIARTL': 10, 'BHEL': 1, 'BOSCHLTD': 100, 'BPCL': 5, 'BRITANNIA': 50, 'BSOFT': 10, 'CANBK': 5, 'CANFINHOME': 10, 'CHOLAFIN': 10, 'CIPLA': 10, 'COFORGE': 100, 'COLPAL': 10, 'CONCOR': 10, 'COROMANDEL': 10, 'CUB': 1, 'CUMMINSIND': 20, 'DABUR': 5, 'DALBHARAT': 20, 'DEEPAKNTR': 20, 'DELTACORP': 5, 'DIVISLAB': 50, 'DIXON': 50, 'DLF': 5, 'DRREDDY': 50, 'EICHERMOT': 50, 'ESCORTS': 20, 'FEDERALBNK': 1, 'GAIL': 1, 'GLENMARK': 10, 'GMRINFRA': 1, 'GNFC': 10, 'GODREJCP': 10, 'GODREJPROP': 20, 'GRASIM': 20, 'GUJGASLTD': 5, 'HAL': 20, 'HAVELLS': 10, 'HCLTECH': 10, 'HDFCAMC': 20, 'HDFCBANK': 10, 'HDFCLIFE': 5, 'HEROMOTOCO': 20, 'HINDALCO': 5, 'HINDCOPPER': 2.5, 'HINDUNILVR': 20, 'ICICIBANK': 10, 'ICICIGI': 10, 'ICICIPRULI': 5, 'IDEA': 1, 'IDFC': 1, 'IDFCFIRSTB': 1, 'IEX': 1, 'IGL': 5, 'INDHOTEL': 5, 'INDIAMART': 50, 'INDIGO': 20, 'INDUSINDBK': 20, 'INFY': 10, 'IOC': 1, 'IPCALAB': 10, 'IRCTC': 10, 'ITC': 5, 'JINDALSTEL': 10, 'JKCEMENT': 50, 'JSWSTEEL': 10, 'JUBLFOOD': 5, 'KOTAKBANK': 20, 'L&TFH': 1, 'LALPATHLAB': 20, 'LAURUSLABS': 5, 'LICHSGFIN': 5, 'LT': 20, 'LTIM': 50, 'LTTS': 50, 'LUPIN': 10, 'M&M': 10, 'M&MFIN': 5, 'MARICO': 5, 'MARUTI': 100, 'MCDOWELL-N': 10, 'MCX': 20, 'METROPOLIS': 20, 'MFSL': 10, 'MGL': 10, 'MOTHERSON': 1, 'MPHASIS': 20, 'MRF': 500, 'MUTHOOTFIN': 10, 'NATIONALUM': 1, 'NAUKRI': 50, 'NAVINFLUOR': 50, 'NESTLEIND': 100, 'NMDC': 1, 'NTPC': 1, 'OBEROIRLTY': 10, 'OFSS': 20, 'ONGC': 2.5, 'PAGEIND': 500, 'PEL': 10, 'PERSISTENT': 50, 'PIDILITIND': 20, 'PIIND': 50, 'PNB': 1, 'POLYCAB': 50, 'PVRINOX': 20, 'RAMCOCEM': 10, 'RELIANCE': 20, 'SAIL': 1, 'SBICARD': 10, 'SBILIFE': 10, 'SBIN': 5, 'SHREECEM': 250, 'SHRIRAMFIN': 20, 'SIEMENS': 50, 'SRF': 20, 'SUNPHARMA': 10, 'SUNTV': 5, 'SYNGENE': 10, 'TATACHEM': 10, 'TATACOMM': 20, 'TATACONSUM': 5, 'TATAMOTORS': 5, 'TATASTEEL': 1, 'TCS': 20, 'TECHM': 10, 'TITAN': 20, 'TORNTPHARM': 20, 'TRENT': 20, 'TVSMOTOR': 20, 'UBL': 10, 'ULTRACEMCO': 50, 'UPL': 5, 'VOLTAS': 10, 'ZYDUSLIFE': 5, 'ABCAPITAL': 2.5, 'ABFRL': 2.5, 'BANDHANBNK': 2.5, 'BANKBARODA': 2.5, 'BIOCON': 2.5, 'CHAMBLFERT': 5, 'COALINDIA': 2.5, 'CROMPTON': 2.5, 'EXIDEIND': 2.5, 'GRANULES': 2.5, 'HINDPETRO': 5, 'IBULHSGFIN': 2.5, 'INDIACEM': 2.5, 'INDUSTOWER': 2.5, 'MANAPPURAM': 2.5, 'PETRONET': 2.5, 'PFC': 2.5, 'POWERGRID': 2.5, 'RBLBANK': 2.5, 'RECLTD': 2.5, 'TATAPOWER': 5, 'VEDL': 2.5, 'WIPRO': 2.5, 'ZEEL': 2.5, 'AMARAJABAT': 10, 'APLLTD': 10, 'CADILAHC': 5, 'HDFC': 50, 'LTI': 100, 'MINDTREE': 20, 'MOTHERSUMI': 5, 'NAM-INDIA': 5, 'PFIZER': 50, 'PVR': 20, 'SRTRANSFIN': 20, 'TORNTPOWER': 5}
				self.step_df                        = pd.DataFrame.from_dict(step_value_dict, orient='index')
				self.step_df                        = self.step_df.reset_index()
				self.step_df.rename({"index": "Symbol", 0: "Applicable Step value"}, axis='columns', inplace =True)
		except Exception as e:
			print(e)
			traceback.print_exc()

	def get_login(self,ClientCode,token_id):
		try:
			self.ClientCode 									= ClientCode
			self.token_id										= token_id
			# dhanhq v2+ requires DhanContext (client_id + access_token), not two args to dhanhq()
			dhan_context = DhanContext(self.ClientCode, self.token_id)
			self.Dhan = dhanhq(dhan_context)
			self.instrument_df 									= self.get_instrument_file()
			print("-----Logged into Dhan-----")
			print('Got the instrument file')
		except Exception as e:
			print(e)
			self.logger.exception(f'got exception in get_login as {e} ')
			traceback.print_exc()
			raise

	def get_instrument_file(self):
		global instrument_df
		current_date = time.strftime("%Y-%m-%d")
		expected_file = 'all_instrument ' + str(current_date) + '.csv'
		for item in os.listdir("Dependencies"):
			path = os.path.join(item)

			if (item.startswith('all_instrument')) and (current_date not in item.split(" ")[1]):
				if os.path.isfile("Dependencies\\" + path):
					os.remove("Dependencies\\" + path)

		if expected_file in os.listdir("Dependencies"):
			try:
				print(f"reading existing file {expected_file}")
				instrument_df = pd.read_csv("Dependencies\\" + expected_file, low_memory=False)
			except Exception as e:
				print(
					"This BOT Is Instrument file is not generated completely, Picking New File from Dhan Again")
				instrument_df = pd.read_csv("https://images.dhan.co/api-data/api-scrip-master.csv", low_memory=False)
				instrument_df.to_csv("Dependencies\\" + expected_file)
		else:
			# this will fetch instrument_df file from Dhan
			print("This BOT Is Picking New File From Dhan")
			instrument_df = pd.read_csv("https://images.dhan.co/api-data/api-scrip-master.csv", low_memory=False)
			instrument_df.to_csv("Dependencies\\" + expected_file)
		return instrument_df

	def order_placement(self,tradingsymbol:str, exchange:str,quantity:int, price:int, trigger_price:int, order_type:str, transaction_type:str, trade_type:str)->str:
		try:
			script_exchange = {"NSE":self.Dhan.NSE, "NFO":self.Dhan.NSE_FNO, "BFO":self.Dhan.BSE_FNO, "CUR": self.Dhan.CUR, "BSE":self.Dhan.BSE, "MCX":self.Dhan.MCX}
			self.order_Type = {'LIMIT': self.Dhan.LIMIT, 'MARKET': self.Dhan.MARKET,'STOPLIMIT': self.Dhan.SL, 'STOPMARKET': self.Dhan.SLM}
			product = {'MIS':self.Dhan.INTRA, 'MARGIN':self.Dhan.MARGIN, 'MTF':self.Dhan.MTF, 'CO':self.Dhan.CO,'BO':self.Dhan.BO, 'CNC': self.Dhan.CNC}
			Validity = {'DAY': "DAY", 'IOC': 'IOC'}
			transactiontype = {'BUY': self.Dhan.BUY, 'SELL': self.Dhan.SELL}
			instrument_exchange = {'NSE':"NSE",'BSE':"BSE",'NFO':'NSE','BFO':'BSE','MCX':'MCX','CUR':'NSE'}

			exchangeSegment = script_exchange[exchange]
			product_Type = product[trade_type.upper()]
			order_type = self.order_Type[order_type.upper()]
			order_side = transactiontype[transaction_type.upper()]
			time_in_force = Validity['DAY']
			security_id = self.instrument_df[((self.instrument_df['SEM_TRADING_SYMBOL']==tradingsymbol)|(self.instrument_df['SEM_CUSTOM_SYMBOL']==tradingsymbol))&(self.instrument_df['SEM_EXM_EXCH_ID']==instrument_exchange[exchange])].iloc[-1]['SEM_SMST_SECURITY_ID']

			order = self.Dhan.place_order(security_id=str(security_id), exchange_segment=exchangeSegment,
											   transaction_type=order_side, quantity=quantity,
											   order_type=order_type, product_type=product_Type, price=price,
											   trigger_price=trigger_price)

			orderid = order["data"]["orderId"]
			return str(orderid)
		except Exception as e:
			self.logger.exception(f'Got exception in place_order as {e}')
			traceback.print_exc()
			return None


	def kill_switch(self,status):
		active = {'ON':'ACTIVATE','OFF':'DEACTIVATE'}
		current_status = active[status.upper()]
		killswitch_url = "https://api.dhan.co/killSwitch"
		params = {
		"killSwitchStatus":current_status, #DEACTIVATE	
		"access-token":self.token_id

		}
		headers = {
			"Content-Type": "application/json",
			"access-token":self.token_id
		}

		killswitch_response = requests.post(killswitch_url, headers=headers, params=params)

		if 'killSwitchStatus' in killswitch_response.json().keys():
			return killswitch_response.json()['killSwitchStatus']
		else:
			return killswitch_response.json()

	def get_live_pnl(self):
		"""
			use to get live pnl
			pnl()
		"""
		try:
			time.sleep(1)
			pos_book = self.Dhan.get_positions()
			pos_book_dict = pos_book['data']
			pos_book = pd.DataFrame(pos_book_dict)
			live_pnl = []

			if pos_book.empty:
				return 0
			for pos_ in pos_book_dict:
				security_id = int(pos_['securityId'])
				underlying = self.instrument_df[((self.instrument_df['SEM_SMST_SECURITY_ID']==security_id))].iloc[-1]['SEM_CUSTOM_SYMBOL']
				closePrice = self.get_ltp(underlying)
				Total_MTM = (float(pos_['daySellValue']) - float(pos_['dayBuyValue'])) + (int(pos_['netQty']) *closePrice * float(pos_['multiplier']))
				live_pnl.append(Total_MTM)
			
			return sum(live_pnl)
		except Exception as e:
			self.logger.exception(f'got exception in pnl as {e} ')
			traceback.print_exc()
			return 0

	def get_balance(self):
		try:
			response = self.Dhan.get_fund_limits()
			balance = float(response['data']['availabelBalance'])
			return balance
		except Exception as e:
			print(f"Error at Gettting balance as {e}")
			self.logger.exception(f"Error at Gettting balance as {e}")
			return 0
	

	def convert_to_date_time(self,time):
		return self.Dhan.convert_to_date_time(time)

	def get_historical_data(self,tradingsymbol,exchange,days):			
		try:
			from_date= datetime.datetime.now()-datetime.timedelta(days=days)
			from_date = from_date.strftime('%Y-%m-%d')
			to_date = datetime.datetime.now().strftime('%Y-%m-%d') 
			script_exchange = {"NSE":self.Dhan.NSE, "NFO":self.Dhan.NSE_FNO, "BFO":self.Dhan.BSE_FNO, "CUR": self.Dhan.CUR, "BSE":self.Dhan.BSE, "MCX":self.Dhan.MCX}
			instrument_exchange = {'NSE':"NSE",'BSE':"BSE",'NFO':'NSE','BFO':'BSE','MCX':'MCX','CUR':'NSE'}
			exchangeSegment = script_exchange[exchange]
			Symbol = self.instrument_df[((self.instrument_df['SEM_TRADING_SYMBOL']==tradingsymbol)|(self.instrument_df['SEM_CUSTOM_SYMBOL']==tradingsymbol))&(self.instrument_df['SEM_EXM_EXCH_ID']==instrument_exchange[exchange])].iloc[-1]['SEM_TRADING_SYMBOL']
			instrument_type = self.instrument_df[((self.instrument_df['SEM_TRADING_SYMBOL']==tradingsymbol)|(self.instrument_df['SEM_CUSTOM_SYMBOL']==tradingsymbol))&(self.instrument_df['SEM_EXM_EXCH_ID']==instrument_exchange[exchange])].iloc[-1]['SEM_INSTRUMENT_NAME']
			expiry_code = self.instrument_df[((self.instrument_df['SEM_TRADING_SYMBOL']==tradingsymbol)|(self.instrument_df['SEM_CUSTOM_SYMBOL']==tradingsymbol))&(self.instrument_df['SEM_EXM_EXCH_ID']==instrument_exchange[exchange])].iloc[-1]['SEM_EXPIRY_CODE']
			ohlc = self.Dhan.historical_daily_data(Symbol,exchangeSegment,instrument_type,str(expiry_code),from_date,to_date)
			data = ohlc.get('data') if ohlc else None
			if not data:
				return None
			# dhanhq v2: data is dict of lists
			if isinstance(data, dict):
				time_series = data.get('timestamp') or data.get('start_Time') or []
				if len(time_series) == 0:
					return None
				df = pd.DataFrame(data)
			else:
				df = pd.DataFrame(data)
			if df.empty:
				return df
			if 'timestamp' in df.columns:
				df['start_Time'] = df['timestamp'].apply(lambda x: self.convert_to_date_time(x))
				df = df.drop(columns=['timestamp'])
			else:
				df['start_Time'] = df['start_Time'].apply(lambda x: self.convert_to_date_time(x))
			return df 
		except Exception as e:
			print(e)
			self.logger.exception(f"Exception in Getting OHLC data as {e}")
			traceback.print_exc()


	def get_intraday_data(self,tradingsymbol,exchange,timeframe):			
		try:
			# pandas 2.2+ uses 'min' not deprecated 'T' for minute resampling
			available_frames = {
				2: '2min',
				3: '3min',
				5: '5min',
				10: '10min',
				15: '15min',
				30: '30min',
				60: '60min'
			}

			script_exchange = {"NSE":self.Dhan.NSE, "NFO":self.Dhan.NSE_FNO, "BFO":self.Dhan.BSE_FNO, "CUR": self.Dhan.CUR, "BSE":self.Dhan.BSE, "MCX":self.Dhan.MCX}
			
			index_ids = {
				"NIFTY": (13, "INDEX"), "NIFTY 50": (13, "INDEX"),
				"BANKNIFTY": (25, "INDEX"), "NIFTY BANK": (25, "INDEX"),
				"FINNIFTY": (27, "INDEX"), "NIFTY FIN SERVICE": (27, "INDEX"),
				"MIDCPNIFTY": (442, "INDEX"), "NIFTY MID SELECT": (442, "INDEX"),
				"SENSEX": (51, "INDEX"), "BANKEX": (69, "INDEX"),
			}
			
			if tradingsymbol.upper() in index_ids:
				security_id, instrument_type = index_ids[tradingsymbol.upper()]
				exchangeSegment = self.Dhan.INDEX
			else:
				instrument_exchange = {'NSE':"NSE",'BSE':"BSE",'NFO':'NSE','BFO':'BSE','MCX':'MCX','CUR':'NSE'}
				rows = self.instrument_df[
					((self.instrument_df['SEM_TRADING_SYMBOL']==tradingsymbol)|(self.instrument_df['SEM_CUSTOM_SYMBOL']==tradingsymbol))
					&(self.instrument_df['SEM_EXM_EXCH_ID']==instrument_exchange[exchange])
				]
				if "SEM_SERIES" in rows.columns and exchange in ("NSE", "BSE"):
					eq = rows[rows["SEM_SERIES"] == "EQ"]
					if not eq.empty:
						rows = eq
				row = rows.iloc[-1]
				security_id = row['SEM_SMST_SECURITY_ID']
				instrument_type = row['SEM_INSTRUMENT_NAME']
				# Index (NIFTY, BANKNIFTY, …) must use Dhan INDEX segment — NSE segment returns 1 bad bar
				if str(row.get("SEM_SEGMENT", "")) == "I" or instrument_type == "INDEX":
					exchangeSegment = self.Dhan.INDEX
				else:
					exchangeSegment = script_exchange[exchange]

			# dhanhq v2+ requires from_date and to_date (YYYY-MM-DD); API returns up to last 5 trading days
			to_date = datetime.datetime.now().strftime('%Y-%m-%d')
			from_date = (datetime.datetime.now() - datetime.timedelta(days=7)).strftime('%Y-%m-%d')
			ohlc = self.Dhan.intraday_minute_data(str(security_id), exchangeSegment, instrument_type, from_date, to_date)
			data = ohlc.get('data') if ohlc else None
			if not data:
				return None
			# dhanhq v2: data is dict of lists with 'timestamp'; older SDK used list of dicts with 'start_Time'
			if isinstance(data, dict):
				time_series = data.get('timestamp') or data.get('start_Time') or []
				if len(time_series) == 0:
					return None
				df = pd.DataFrame(data)
			else:
				if len(data) == 0:
					return None
				df = pd.DataFrame(data)
			if df.empty:
				return None
			if 'timestamp' in df.columns:
				df['start_Time'] = df['timestamp'].apply(lambda x: self.convert_to_date_time(x))
				df = df.drop(columns=['timestamp'])
			else:
				df['start_Time'] = df['start_Time'].apply(lambda x: self.convert_to_date_time(x))
			if timeframe == 1:
				return df.dropna(subset=['close'])
			df = self.resample_timeframe(df, available_frames[timeframe])
			return df 
		except Exception as e:
			print(e)
			self.logger.exception(f"Exception in Getting OHLC data as {e}")
			traceback.print_exc()

	def add_supertrend(self, df, period=10, multiplier=3):
		"""TradingView-style Supertrend; adds columns supertrend + st_color (GREEN/RED)."""
		work = df.copy()
		if work is None or work.empty:
			return work
		high = work["high"].astype(float)
		low = work["low"].astype(float)
		close = work["close"].astype(float)
		tr = pd.concat(
			[high - low, (high - close.shift()).abs(), (low - close.shift()).abs()],
			axis=1,
		).max(axis=1)
		atr = tr.rolling(period).mean()
		hl2 = (high + low) / 2
		upper = hl2 + multiplier * atr
		lower = hl2 - multiplier * atr
		st = [float(lower.iloc[0])]
		direction = [1]
		ub = upper.tolist()
		lb = lower.tolist()
		closes = close.tolist()
		for i in range(1, len(work)):
			if closes[i] > ub[i - 1]:
				direction.append(1)
			elif closes[i] < lb[i - 1]:
				direction.append(-1)
			else:
				direction.append(direction[-1])
				if direction[-1] == 1 and lb[i] < st[-1]:
					lb[i] = st[-1]
				elif direction[-1] == -1 and ub[i] > st[-1]:
					ub[i] = st[-1]
			st.append(lb[i] if direction[-1] == 1 else ub[i])
		work["supertrend"] = st
		work["st_color"] = ["GREEN" if d == 1 else "RED" for d in direction]
		return work

	def check_full_day(self, stock, timeframe, exchange='NSE'):
		"""
		Quick diagnostic: verify latest trading session has a full day of candles.

		Usage (after Tradehull login):
		    tsl.check_full_day('RELIANCE', 30)
		    tsl.check_full_day('HDFCBANK', 5, exchange='NSE')

		Returns a dict with counts and ok/not-ok status.
		"""
		# NSE cash session ~375 minutes (09:15-15:30)
		expected_per_day = {1: 375, 2: 188, 3: 125, 5: 75, 10: 38, 15: 25, 30: 13, 60: 7}
		if timeframe not in expected_per_day:
			print(f"Invalid timeframe {timeframe}. Use one of: {sorted(expected_per_day.keys())}")
			return {'ok': False, 'error': 'invalid_timeframe'}

		chart = self.get_intraday_data(stock, exchange, timeframe)
		if chart is None or chart.empty:
			print(f"{stock} ({exchange}, {timeframe}m): NO DATA - check symbol, token, or market hours")
			return {'ok': False, 'stock': stock, 'timeframe': timeframe, 'error': 'no_data'}

		latest_session = pd.to_datetime(chart['start_Time']).max().date()
		day = chart[pd.to_datetime(chart['start_Time']).dt.date == latest_session]
		count = len(day)
		expected = expected_per_day[timeframe]
		ok = count >= int(expected * 0.85)

		print(f"\n--- check_full_day: {stock} | {exchange} | {timeframe}m ---")
		print(f"Latest session date : {latest_session}")
		print(f"Candles that day    : {count}  (expected ~{expected} for full NSE day)")
		if count >= 2:
			print(f"First candle        : {day['start_Time'].iloc[0]}")
			print(f"Last candle         : {day['start_Time'].iloc[-1]}")
		print(f"Total rows (multi-day history): {len(chart)}")
		if ok:
			print("Status              : OK - full day data looks complete")
		else:
			print("Status              : WARNING - fewer candles than expected")
			print("  Fixes: run on/after market hours; check token; try timeframe 5 or 1")
		print()

		return {
			'ok': ok,
			'stock': stock,
			'exchange': exchange,
			'timeframe': timeframe,
			'session_date': str(latest_session),
			'candles': count,
			'expected': expected,
			'total_rows': len(chart),
		}

	def check_rsi_report(self, stock, timeframe=60, exchange='NSE', rsi_period=14):
		"""
		Print candle-by-candle RSI for the latest session (use timeframe=60 for hourly).

		Usage:
		    tsl.check_rsi_report('RELIANCE', 60)   # hourly RSI table
		    tsl.check_rsi_report('RELIANCE', 15)   # 15-minute RSI table
		"""
		import talib

		chart = self.get_intraday_data(stock, exchange, timeframe)
		if chart is None or chart.empty:
			print(f"{stock}: no data for RSI report")
			return None

		chart = chart.copy()
		chart['rsi'] = talib.RSI(chart['close'], timeperiod=rsi_period)
		latest_session = pd.to_datetime(chart['start_Time']).max().date()
		day = chart[pd.to_datetime(chart['start_Time']).dt.date == latest_session].copy()

		def rsi_signal(v):
			if pd.isna(v):
				return 'warming up'
			if v > 60:
				return 'UPTREND'
			if v < 40:
				return 'DOWNTREND'
			return 'neutral'

		day['signal'] = day['rsi'].apply(rsi_signal)

		print(f"\n{'='*72}")
		print(f"RSI REPORT | {stock} | {exchange} | {timeframe}-minute candles | RSI({rsi_period})")
		print(f"Latest session: {latest_session} | Candles today: {len(day)} | History rows: {len(chart)}")
		print(f"{'='*72}")
		print(f"{'Time':<22} {'Close':>10} {'RSI':>8} {'Signal':<12}")
		print('-' * 72)
		for _, row in day.iterrows():
			t = pd.Timestamp(row['start_Time']).strftime('%Y-%m-%d %H:%M')
			rsi_val = row['rsi']
			rsi_str = f"{rsi_val:>8.1f}" if not pd.isna(rsi_val) else '     n/a'
			print(f"{t:<22} {row['close']:>10.2f} {rsi_str} {row['signal']:<12}")

		print('-' * 72)
		if len(day) >= 2:
			lcc = day.iloc[-2]
			print(f"Last COMPLETE candle (used in algo): {pd.Timestamp(lcc['start_Time']).strftime('%Y-%m-%d %H:%M')}")
			print(f"  Close={lcc['close']:.2f}  RSI={lcc['rsi']:.1f}  Signal={lcc['signal']}")
		else:
			print("Not enough candles for last-complete-candle (need at least 2).")

		print(f"\nHow to read:")
		print(f"  - RSI > 60  -> uptrend   |  RSI < 40 -> downtrend   |  else neutral")
		print(f"  - 'warming up' = not enough prior candles for RSI({rsi_period}) yet that day")
		print(f"  - Algo uses iloc[-2] = second-last row above (last *complete* bar)\n")

		return day

	def resample_timeframe(self, df, timeframe='5min'):
		df['start_Time'] = pd.to_datetime(df['start_Time'])
		df.set_index('start_Time', inplace=True)
		earliest_time = df.index.min()
		desired_start_time = earliest_time.replace(hour=9, minute=15, second=0, microsecond=0)
		bar_minutes = int(''.join(c for c in timeframe if c.isdigit()) or '5')
		
		if earliest_time < desired_start_time:
			adjusted_start_time = desired_start_time
		else:
			adjusted_start_time = desired_start_time + pd.DateOffset(minutes=(earliest_time - desired_start_time).seconds // 60 // bar_minutes * bar_minutes)
		
		resampled_df = df.resample(timeframe, origin=adjusted_start_time).agg({
			'open': 'first',
			'high': 'max',
			'low': 'min',
			'close': 'last',
			'volume': 'sum'
		})
		
		resampled_df.reset_index(inplace=True)
		# Drop empty bars (overnight/weekends) so RSI and other indicators get valid close prices
		return resampled_df.dropna(subset=['close'])

	
	def get_lot_size(self,tradingsymbol: str):
		data = self.instrument_df[((self.instrument_df['SEM_TRADING_SYMBOL']==tradingsymbol)|(self.instrument_df['SEM_CUSTOM_SYMBOL']==tradingsymbol))]
		if len(data) == 0:
			self.logger.exception("Enter valid Script Name")
			return 0
		else:
			return int(data.iloc[0]['SEM_LOT_UNITS'])
		
	def _attach_websocket_sheet(self):
		"""Attach to Websocket.xlsx if already open (does not start Excel)."""
		if self.sheet is not None:
			return
		try:
			self.wb = xw.books["Websocket.xlsx"]
			self.sheet = self.wb.sheets["LTP"]
		except Exception:
			raise RuntimeError(
				"Websocket.xlsx is not open. Run Dhan_websocket.py first, or open "
				"Websocket.xlsx manually (sheet LTP: Script Name / Exchange / LTP)."
			)

	def get_ltp(self,name):
		single_name = None
		if isinstance(name, list):
			if len(name) == 1:
				single_name = str(name[0]).strip()
		else:
			single_name = str(name).strip()
		try:
			self._attach_websocket_sheet()
			exchange_index = {"BANKNIFTY": "NSE_IDX","NIFTY":"NSE_IDX","MIDCPNIFTY":"NSE_IDX", "FINNIFTY":"NSE_IDX","SENSEX":"BSE_IDX","BANKEX":"BSE_IDX"}
			NFO = ["BANKNIFTY","NIFTY","MIDCPNIFTY","FINNIFTY"]
			BFO = ['SENSEX','BANKEX']
			equity = ['CALL','PUT','FUT']
			if type(name)!=list:
				nfo_check = ["NFO" for nfo in NFO if nfo in name]
				bfo_check = ["BFO" for bfo in BFO if bfo in name]
				exchange_nfo ="NFO" if len(nfo_check)!=0 else False
				exchange_bfo = 'BFO' if len(bfo_check)!=0 else False
				if not exchange_nfo and not exchange_bfo:
					eq_check =["NFO" for nfo in equity if nfo in name]
					exchange_eq ="NFO" if len(eq_check)!=0 else "NSE"
				else:
					exchange_eq="NSE"
				exchange_segment ="NFO" if exchange_nfo else ("BFO" if exchange_bfo else exchange_eq)
				exchange = exchange_index[name] if name in exchange_index else exchange_segment
				name = [name]
				df = self.sheet.range('A1').expand().options(pd.DataFrame, header=1, index=False).value
				data = df[df['Script Name'].isin(name)]
				if data.empty:
					new_name = self.instrument_df[((self.instrument_df['SEM_CUSTOM_SYMBOL']==name[0])|(self.instrument_df['SEM_TRADING_SYMBOL']==name[0]))].iloc[-1]['SEM_TRADING_SYMBOL']
					new_name = [new_name]
					df = self.sheet.range('A1').expand().options(pd.DataFrame, header=1, index=False).value
					data = df[df['Script Name'].isin(new_name)]
				if data.empty:
					df = self.sheet.range('A1').expand().options(pd.DataFrame, header=1, index=False).value
					if len(df)<100:
						add = list()
						row = len(df)+2
						add.extend(name)
						add.append(exchange)
						self.sheet.range(f'A{row}').value = add
						df = self.sheet.range('A1').expand().options(pd.DataFrame, header=1, index=False).value
						data = df[df['Script Name'].isin(name)]
						check = data.fillna('0').iloc[-1]['LTP']=='0'
						while check:
							df = self.sheet.range('A1').expand().options(pd.DataFrame, header=1, index=False).value
							data = df[df['Script Name'].isin(name)]
							check = data.fillna('0').iloc[-1]['LTP']=='0'
				data = data.set_index('Script Name')['LTP']
				out = data.to_dict()[name[0]] if name[0] in data else data.to_dict()[new_name[0]]
				if single_name and (not out or float(out) <= 0):
					rest = self._get_ltp_via_rest(single_name)
					if rest:
						return rest
				return out
			df = self.sheet.range('A1').expand().options(pd.DataFrame, header=1, index=False).value
			data = df[df['Script Name'].isin(name)]
			data = data.set_index('Script Name')['LTP']
			return data.to_dict()
		except Exception as e:
			msg = str(e)
			if single_name:
				rest = self._get_ltp_via_rest(single_name)
				if rest and float(rest) > 0:
					return rest
			if "Websocket" not in msg:
				print(e)
			self.logger.exception(f"Exception in getting LTP as {e}")
			return 0


	def ATM_Strike_Selection(self, Underlying, Expiry):
		try:
			Expiry = pd.to_datetime(Expiry, format='%d-%m-%Y').strftime('%Y-%m-%d')
			exchange_index = {"BANKNIFTY": "NSE","NIFTY":"NSE","MIDCPNIFTY":"NSE", "FINNIFTY":"NSE","SENSEX":"BSE","BANKEX":"BSE"}
			instrument_df = self.instrument_df.copy()

			instrument_df['SEM_EXPIRY_DATE'] = pd.to_datetime(instrument_df['SEM_EXPIRY_DATE'], errors='coerce')
			instrument_df['ContractExpiration'] = instrument_df['SEM_EXPIRY_DATE'].dt.date
			instrument_df['ContractExpiration'] = instrument_df['ContractExpiration'].astype(str)

			if Underlying in exchange_index:
				exchange = exchange_index[Underlying]
			else:
				# exchange = instrument_df[((instrument_df['SEM_TRADING_SYMBOL']==Underlying)|(instrument_df['SEM_CUSTOM_SYMBOL']==Underlying))].iloc[0]['SEM_EXM_EXCH_ID']
				exchange = "NSE"
	

			ltp = self.get_ltp(Underlying)
			if Underlying in self.index_step_dict:
				step = self.index_step_dict[Underlying]
			if Underlying in self.stock_step_df:
				step = self.stock_step_df[Underlying]
			strike = round(ltp/step) * step


			ce_condition = (instrument_df['SEM_EXM_EXCH_ID'] == exchange) & ((instrument_df['SEM_TRADING_SYMBOL'].str.contains(Underlying))|(instrument_df['SEM_CUSTOM_SYMBOL'].str.contains(Underlying))) & (instrument_df['ContractExpiration'] == Expiry) & (instrument_df['SEM_OPTION_TYPE']=='CE') 
			pe_condition = (instrument_df['SEM_EXM_EXCH_ID'] == exchange) & ((instrument_df['SEM_TRADING_SYMBOL'].str.contains(Underlying))|(instrument_df['SEM_CUSTOM_SYMBOL'].str.contains(Underlying))) & (instrument_df['ContractExpiration'] == Expiry) & (instrument_df['SEM_OPTION_TYPE']=='PE') 		
			ce_df = instrument_df[ce_condition].copy()
			pe_df = instrument_df[pe_condition].copy()

			ce_df['SEM_STRIKE_PRICE'] = ce_df['SEM_STRIKE_PRICE'].astype("int")
			pe_df['SEM_STRIKE_PRICE'] = pe_df['SEM_STRIKE_PRICE'].astype("int")

			ce_df =ce_df[ce_df['SEM_STRIKE_PRICE']==strike]
			pe_df =pe_df[pe_df['SEM_STRIKE_PRICE']==strike]

			if ce_df.empty or len(ce_df)==0:
				ce_df['diff'] = abs(ce_df['SEM_STRIKE_PRICE'] - strike)
				closest_index = ce_df['diff'].idxmin()
				strike = ce_df.loc[closest_index, 'SEM_STRIKE_PRICE']
				ce_df =ce_df[ce_df['SEM_STRIKE_PRICE']==strike]
			
			ce_df = ce_df.iloc[-1]	

			if pe_df.empty or len(pe_df)==0:
				pe_df['diff'] = abs(pe_df['SEM_STRIKE_PRICE'] - strike)
				closest_index = pe_df['diff'].idxmin()
				strike = pe_df.loc[closest_index, 'SEM_STRIKE_PRICE']
				pe_df =pe_df[pe_df['SEM_STRIKE_PRICE']==strike]
			
			pe_df = pe_df.iloc[-1]			

			ce_strike = ce_df['SEM_CUSTOM_SYMBOL']
			pe_strike = pe_df['SEM_CUSTOM_SYMBOL']

			if ce_strike== None:
				self.logger.info("No Scripts to Select from ce_spot_difference for ")
				return
			if pe_strike == None:
				self.logger.info("No Scripts to Select from pe_spot_difference for ")
				return
			
			return ce_strike, pe_strike, strike
		except Exception as e:
			traceback.print_exc()
			self.logger.exception("Got exception in ce_pe_option_df ", e)
			print('exception got in ce_pe_option_df',e)
			return None, None, strike

	def OTM_Strike_Selection(self, Underlying, Expiry,OTM_count=1):
		try:
			Expiry = pd.to_datetime(Expiry, format='%d-%m-%Y').strftime('%Y-%m-%d')
			exchange_index = {"BANKNIFTY": "NSE","NIFTY":"NSE","MIDCPNIFTY":"NSE", "FINNIFTY":"NSE","SENSEX":"BSE","BANKEX":"BSE"}
			instrument_df = self.instrument_df.copy()

			instrument_df['SEM_EXPIRY_DATE'] = pd.to_datetime(instrument_df['SEM_EXPIRY_DATE'], errors='coerce')
			instrument_df['ContractExpiration'] = instrument_df['SEM_EXPIRY_DATE'].dt.date
			instrument_df['ContractExpiration'] = instrument_df['ContractExpiration'].astype(str)

			if Underlying in exchange_index:
				exchange = exchange_index[Underlying]
			else:
				# exchange = instrument_df[((instrument_df['SEM_TRADING_SYMBOL']==Underlying)|(instrument_df['SEM_CUSTOM_SYMBOL']==Underlying))].iloc[0]['SEM_EXM_EXCH_ID']
				exchange = "NSE"
	

			ltp = self.get_ltp(Underlying)
			if Underlying in self.index_step_dict:
				step = self.index_step_dict[Underlying]
			if Underlying in self.stock_step_df:
				step = self.stock_step_df[Underlying]
			strike = round(ltp/step) * step

			if OTM_count<1:
				return "INVALID OTM DISTANCE"

			step = int(OTM_count*step)

			ce_OTM_price = strike+step
			pe_OTM_price = strike-step

			ce_condition = (instrument_df['SEM_EXM_EXCH_ID'] == exchange) & ((instrument_df['SEM_TRADING_SYMBOL'].str.contains(Underlying))|(instrument_df['SEM_CUSTOM_SYMBOL'].str.contains(Underlying))) & (instrument_df['ContractExpiration'] == Expiry) & (instrument_df['SEM_OPTION_TYPE']=='CE') 
			pe_condition = (instrument_df['SEM_EXM_EXCH_ID'] == exchange) & ((instrument_df['SEM_TRADING_SYMBOL'].str.contains(Underlying))|(instrument_df['SEM_CUSTOM_SYMBOL'].str.contains(Underlying))) & (instrument_df['ContractExpiration'] == Expiry) & (instrument_df['SEM_OPTION_TYPE']=='PE') 		
			ce_df = instrument_df[ce_condition].copy()
			pe_df = instrument_df[pe_condition].copy()

			ce_df['SEM_STRIKE_PRICE'] = ce_df['SEM_STRIKE_PRICE'].astype("int")
			pe_df['SEM_STRIKE_PRICE'] = pe_df['SEM_STRIKE_PRICE'].astype("int")

			ce_df =ce_df[ce_df['SEM_STRIKE_PRICE']==ce_OTM_price]
			pe_df =pe_df[pe_df['SEM_STRIKE_PRICE']==pe_OTM_price]

			if ce_df.empty or len(ce_df)==0:
				ce_df['diff'] = abs(ce_df['SEM_STRIKE_PRICE'] - ce_OTM_price)
				closest_index = ce_df['diff'].idxmin()
				ce_OTM_price = ce_df.loc[closest_index, 'SEM_STRIKE_PRICE']
				ce_df =ce_df[ce_df['SEM_STRIKE_PRICE']==ce_OTM_price]
			
			ce_df = ce_df.iloc[-1]	

			if pe_df.empty or len(pe_df)==0:
				pe_df['diff'] = abs(pe_df['SEM_STRIKE_PRICE'] - pe_OTM_price)
				closest_index = pe_df['diff'].idxmin()
				pe_OTM_price = pe_df.loc[closest_index, 'SEM_STRIKE_PRICE']
				pe_df =pe_df[pe_df['SEM_STRIKE_PRICE']==pe_OTM_price]
			
			pe_df = pe_df.iloc[-1]			

			ce_strike = ce_df['SEM_CUSTOM_SYMBOL']
			pe_strike = pe_df['SEM_CUSTOM_SYMBOL']

			if ce_strike== None:
				self.logger.info("No Scripts to Select from ce_spot_difference for ")
				return
			if pe_strike == None:
				self.logger.info("No Scripts to Select from pe_spot_difference for ")
				return
			
			return ce_strike, pe_strike, ce_OTM_price, pe_OTM_price
		except Exception as e:
			print(f"Getting Error at OTM strike Selection as {e}")
			return None,None,0,0


	def ITM_Strike_Selection(self, Underlying, Expiry, ITM_count=1):
		try:
			Expiry = pd.to_datetime(Expiry, format='%d-%m-%Y').strftime('%Y-%m-%d')
			exchange_index = {"BANKNIFTY": "NSE","NIFTY":"NSE","MIDCPNIFTY":"NSE", "FINNIFTY":"NSE","SENSEX":"BSE","BANKEX":"BSE"}
			instrument_df = self.instrument_df.copy()

			instrument_df['SEM_EXPIRY_DATE'] = pd.to_datetime(instrument_df['SEM_EXPIRY_DATE'], errors='coerce')
			instrument_df['ContractExpiration'] = instrument_df['SEM_EXPIRY_DATE'].dt.date
			instrument_df['ContractExpiration'] = instrument_df['ContractExpiration'].astype(str)

			if Underlying in exchange_index:
				exchange = exchange_index[Underlying]
			else:
				# exchange = instrument_df[((instrument_df['SEM_TRADING_SYMBOL']==Underlying)|(instrument_df['SEM_CUSTOM_SYMBOL']==Underlying))].iloc[0]['SEM_EXM_EXCH_ID']
				exchange = "NSE"
	

			ltp = self.get_ltp(Underlying)
			if Underlying in self.index_step_dict:
				step = self.index_step_dict[Underlying]
			if Underlying in self.stock_step_df:
				step = self.stock_step_df[Underlying]
			strike = round(ltp/step) * step

			if ITM_count<1:
				return "INVALID ITM DISTANCE"
			
			step = int(ITM_count*step)
			ce_ITM_price = strike-step
			pe_ITM_price = strike+step

			ce_condition = (instrument_df['SEM_EXM_EXCH_ID'] == exchange) & ((instrument_df['SEM_TRADING_SYMBOL'].str.contains(Underlying))|(instrument_df['SEM_CUSTOM_SYMBOL'].str.contains(Underlying))) & (instrument_df['ContractExpiration'] == Expiry) & (instrument_df['SEM_OPTION_TYPE']=='CE') 
			pe_condition = (instrument_df['SEM_EXM_EXCH_ID'] == exchange) & ((instrument_df['SEM_TRADING_SYMBOL'].str.contains(Underlying))|(instrument_df['SEM_CUSTOM_SYMBOL'].str.contains(Underlying))) & (instrument_df['ContractExpiration'] == Expiry) & (instrument_df['SEM_OPTION_TYPE']=='PE') 		
			ce_df = instrument_df[ce_condition].copy()
			pe_df = instrument_df[pe_condition].copy()

			ce_df['SEM_STRIKE_PRICE'] = ce_df['SEM_STRIKE_PRICE'].astype("int")
			pe_df['SEM_STRIKE_PRICE'] = pe_df['SEM_STRIKE_PRICE'].astype("int")

			ce_df =ce_df[ce_df['SEM_STRIKE_PRICE']==ce_ITM_price]
			pe_df =pe_df[pe_df['SEM_STRIKE_PRICE']==pe_ITM_price]

			if ce_df.empty or len(ce_df)==0:
				ce_df['diff'] = abs(ce_df['SEM_STRIKE_PRICE'] - ce_ITM_price)
				closest_index = ce_df['diff'].idxmin()
				ce_ITM_price = ce_df.loc[closest_index, 'SEM_STRIKE_PRICE']
				ce_df =ce_df[ce_df['SEM_STRIKE_PRICE']==ce_ITM_price]
			
			ce_df = ce_df.iloc[-1]	

			if pe_df.empty or len(pe_df)==0:
				pe_df['diff'] = abs(pe_df['SEM_STRIKE_PRICE'] - pe_ITM_price)
				closest_index = pe_df['diff'].idxmin()
				pe_ITM_price = pe_df.loc[closest_index, 'SEM_STRIKE_PRICE']
				pe_df =pe_df[pe_df['SEM_STRIKE_PRICE']==pe_ITM_price]
			
			pe_df = pe_df.iloc[-1]			

			ce_strike = ce_df['SEM_CUSTOM_SYMBOL']
			pe_strike = pe_df['SEM_CUSTOM_SYMBOL']

			if ce_strike== None:
				self.logger.info("No Scripts to Select from ce_spot_difference for ")
				return
			if pe_strike == None:
				self.logger.info("No Scripts to Select from pe_spot_difference for ")
				return
			
			return ce_strike, pe_strike, ce_ITM_price, pe_ITM_price
		except Exception as e:
			print(f"Getting Error at OTM strike Selection as {e}")
			return None,None,0,0

	def cancel_all_orders(self) -> dict:
		try:
			order_details=dict()
			product_detail ={'MIS':self.Dhan.INTRA, 'MARGIN':self.Dhan.MARGIN, 'MTF':self.Dhan.MTF, 'CO':self.Dhan.CO,'BO':self.Dhan.BO, 'CNC': self.Dhan.CNC}
			product = product_detail['MIS']
			time.sleep(1)
			data = self.Dhan.get_order_list()["data"]
			if data is None or len(data)==0:
				return order_details
			orders = pd.DataFrame(data)
			if orders.empty:
				return order_details
			trigger_pending_orders = orders.loc[(orders['orderStatus'] == 'PENDING') & (orders['productType'] == product)]
			open_orders = orders.loc[(orders['orderStatus'] == 'TRANSIT') & (orders['productType'] == product)]
			for index, row in trigger_pending_orders.iterrows():
				response = self.Dhan.cancel_order(row['orderId'])

			for index, row in open_orders.iterrows():
				response = self.Dhan.cancel_order(row['orderId'])
			position_dict = self.Dhan.get_positions()["data"]
			positions_df = pd.DataFrame(position_dict)
			if positions_df.empty:
				return order_details
			positions_df['netQty']=positions_df['netQty'].astype(int)
			bought = positions_df.loc[(positions_df['netQty'] > 0) & (positions_df["productType"] == product)]
			sold = positions_df.loc[(positions_df['netQty'] < 0) & (positions_df['productType'] == product)]

			for index, row in bought.iterrows():
				qty = int(row["netQty"])
				order = self.Dhan.place_order(security_id=str(row["securityId"]), exchange_segment=row["exchangeSegment"],
												transaction_type=self.Dhan.SELL, quantity=qty,
												order_type=self.Dhan.MARKET, product_type=row["productType"], price=0,
												trigger_price=0)

				tradingsymbol = row['tradingSymbol']
				sell_order_id= order["data"]["orderId"]
				order_details[tradingsymbol]=dict({'orderid':sell_order_id,'price':0})
				time.sleep(0.5)

			for index, row in sold.iterrows():
				qty = int(row["netQty"]) * -1
				order = self.Dhan.place_order(security_id=str(row["securityId"]), exchange_segment=row["exchangeSegment"],
												transaction_type=self.Dhan.BUY, quantity=qty,
												order_type=self.Dhan.MARKET, product_type=row["productType"], price=0,
												trigger_price=0)
				tradingsymbol = row['tradingSymbol']
				buy_order_id=order["data"]["orderId"]
				order_details[tradingsymbol]=dict({'orderid':buy_order_id,'price':0})
				time.sleep(1)
			if len(order_details)!=0:
				_,order_price = self.order_report()
				for key,value in order_details.items():
					orderid = str(value['orderid'])
					if orderid in order_price:
						order_details[key]['price'] = order_price[orderid] 	
			return order_details
		except Exception as e:
			print(e)
			print("problem close all trades")
			self.logger.exception("problem close all trades")
			traceback.print_exc()

	def order_report(self) -> Tuple[Dict, Dict]:
		'''
		If watchlist has more than two stock, using order_report, get the order status and order execution price
		order_report()
		'''
		try:
			order_details= dict()
			order_exe_price= dict()
			status_df = self.Dhan.get_order_list()["data"]
			status_df = pd.DataFrame(status_df)
			if not status_df.empty:
				status_df.set_index('orderId',inplace=True)
				order_details = status_df['orderStatus'].to_dict()
				order_exe_price = status_df['price'].to_dict()
			
			return order_details, order_exe_price
		except Exception as e:
			self.logger.exception(f"Exception in getting order report as {e}")
			return dict(), dict()

	def get_option_greek(self, strike: int, expiry_date: str, asset: str, interest_rate: float, flag: str, scrip_type: str):
		try:
			expiry = pd.to_datetime(expiry_date, format='%d-%m-%Y').strftime('%Y-%m-%d')
			exchange_index = {"BANKNIFTY": "NSE", "NIFTY": "NSE", "MIDCPNIFTY": "NSE", "FINNIFTY": "NSE", "SENSEX": "BSE", "BANKEX": "BSE"}
			asset_dict = {'NIFTY BANK': "BANKNIFTY", "NIFTY 50": "NIFTY", 'NIFTY FIN SERVICE': 'FINNIFTY', 'NIFTY MID SELECT': 'MIDCPNIFTY', "SENSEX": "SENSEX", "BANKEX": "BANKEX"}

			if asset in asset_dict:
				inst_asset = asset_dict[asset]
			elif asset in asset_dict.values():
				inst_asset = asset
			else:
				inst_asset = asset

			# exchange = exchange_index[inst_asset]

			instrument_df = self.instrument_df.copy()
			instrument_df['SEM_EXPIRY_DATE'] = pd.to_datetime(instrument_df['SEM_EXPIRY_DATE'], errors='coerce')
			instrument_df['ContractExpiration'] = instrument_df['SEM_EXPIRY_DATE'].dt.date.astype(str)

			data = instrument_df[
				# (instrument_df['SEM_EXM_EXCH_ID'] == exchange) &
				((instrument_df['SEM_TRADING_SYMBOL'].str.contains(inst_asset)) | 
				 (instrument_df['SEM_CUSTOM_SYMBOL'].str.contains(inst_asset))) &
				(instrument_df['ContractExpiration'] == expiry) &
				(instrument_df['SEM_STRIKE_PRICE'] == strike) &
				(instrument_df['SEM_OPTION_TYPE']==scrip_type)
			]

			if data.empty:
				self.logger.error('No data found for the specified parameters.')
				return None

			script_list = data['SEM_CUSTOM_SYMBOL'].tolist()
			script = script_list[0]

			days_to_expiry = (datetime.datetime.strptime(expiry_date, "%d-%m-%Y").date() - datetime.datetime.now().date()).days
			if days_to_expiry <= 0:
				days_to_expiry = 1

			asset_price = self.get_ltp(asset)
			ltp = self.get_ltp(script)

			if scrip_type == 'CE':
				civ = mibian.BS([asset_price, strike, interest_rate, days_to_expiry], callPrice= ltp)
				cval = mibian.BS([asset_price, strike, interest_rate, days_to_expiry], volatility = civ.impliedVolatility ,callPrice= ltp)
				if flag == "price":
					return cval.callPrice
				if flag == "delta":
					return cval.callDelta
				if flag == "delta2":
					return cval.callDelta2
				if flag == "theta":
					return cval.callTheta
				if flag == "rho":
					return cval.callRho
				if flag == "vega":
					return cval.vega
				if flag == "gamma":
					return cval.gamma
				if flag == "all_val":
					return {'callPrice' : cval.callPrice, 'callDelta' : cval.callDelta, 'callDelta2' : cval.callDelta2, 'callTheta' : cval.callTheta, 'callRho' : cval.callRho, 'vega' : cval.vega, 'gamma' : cval.gamma}

			if scrip_type == "PE":
				piv = mibian.BS([asset_price, strike, interest_rate, days_to_expiry], putPrice= ltp)
				pval = mibian.BS([asset_price, strike, interest_rate, days_to_expiry], volatility = piv.impliedVolatility ,putPrice= ltp)
				if flag == "price":
					return pval.putPrice
				if flag == "delta":
					return pval.putDelta
				if flag == "delta2":
					return pval.putDelta2
				if flag == "theta":
					return pval.putTheta
				if flag == "rho":
					return pval.putRho
				if flag == "vega":
					return pval.vega
				if flag == "gamma":
					return pval.gamma
				if flag == "all_val":
					return {'callPrice' : pval.putPrice, 'callDelta' : pval.putDelta, 'callDelta2' : pval.putDelta2, 'callTheta' : pval.putTheta, 'callRho' : pval.putRho, 'vega' : pval.vega, 'gamma' : pval.gamma}

		except Exception as e:
			self.logger.exception(f"Exception in get_option_greek: {e}")
			return None

	def _unwrap_ticker_response(self, resp):
		"""Parse dhanhq ticker_data: {status, data: {status, data: {segment: {id: quote}}}}."""
		if not resp or not isinstance(resp, dict):
			return {}
		status = str(resp.get("status", "")).lower()
		if status and status != "success":
			return {"_error": resp.get("remarks") or resp.get("status") or "ticker_failed"}
		data = resp.get("data")
		if data is None or data == "":
			return {}
		if isinstance(data, dict):
			inner_status = str(data.get("status", "")).lower()
			if inner_status and inner_status != "success":
				return {"_error": data.get("remarks") or data.get("status") or "ticker_inner_failed"}
			if "data" in data and isinstance(data.get("data"), dict):
				data = data["data"]
		return data if isinstance(data, dict) else {}

	def _rest_index_ltp(self, underlying):
		"""REST LTP for index underlyings (no Excel)."""
		underlying_ids = {
			"NIFTY": (13, "IDX_I"),
			"BANKNIFTY": (25, "IDX_I"),
			"FINNIFTY": (27, "IDX_I"),
			"MIDCPNIFTY": (442, "IDX_I"),
			"SENSEX": (51, "IDX_I"),
			"BANKEX": (69, "IDX_I"),
		}
		if underlying not in underlying_ids:
			return None
		security_id, segment = underlying_ids[underlying]
		try:
			resp = self.Dhan.ticker_data({segment: [int(security_id)]})
			block = self._unwrap_ticker_response(resp).get(segment, {})
			quote = block.get(str(security_id)) or block.get(int(security_id)) or {}
			return float(quote.get("last_price") or 0) or None
		except Exception as e:
			print(f"REST LTP failed for {underlying}: {e}")
			return None

	def _infer_underlying_from_symbol(self, symbol):
		s = str(symbol or "").upper()
		for u in ("SENSEX", "BANKEX", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "NIFTY"):
			if u in s:
				return u
		return "NIFTY"

	def _get_ltp_via_rest(self, name):
		sym = str(name[0] if isinstance(name, list) and name else name).strip()
		if not sym:
			return 0
		u = sym.upper()
		if u in ("NIFTY", "NIFTY 50", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY"):
			return float(self._rest_index_ltp(u.split()[0]) or 0)
		underlying = self._infer_underlying_from_symbol(sym)
		if "CALL" in u or " PUT" in u or u.endswith("PUT"):
			try:
				chain = self.get_option_chain(underlying=underlying, strike_range=15)
				if chain and chain.get("options"):
					for opt in chain["options"]:
						if str(opt.get("symbol", "")).strip() == sym:
							ltp = float(opt.get("ltp") or 0)
							if ltp > 0:
								return ltp
			except Exception:
				pass
			quotes = self.get_rest_ltps_for_watchlist([(sym, "NFO")], quiet=True)
			ltp = quotes.get(sym)
			if ltp and float(ltp) > 0:
				return float(ltp)
		return 0

	def _get_session_expiry(self, underlying, security_id, segment):
		"""Cache nearest expiry per underlying for the session (one expiry_list per day)."""
		if not hasattr(self, "_option_chain_expiry"):
			self._option_chain_expiry = {}
		today = str(datetime.datetime.now().date())
		entry = self._option_chain_expiry.get(underlying)
		if entry and entry.get("day") == today and entry.get("expiry"):
			return entry["expiry"]
		exp_resp = self.Dhan.expiry_list(security_id, segment)
		exp_block = exp_resp.get("data") if isinstance(exp_resp, dict) else None
		if isinstance(exp_block, dict) and isinstance(exp_block.get("data"), list):
			exp_block = exp_block["data"]
		if not isinstance(exp_block, list) or not exp_block:
			return entry.get("expiry") if entry else None
		expiry = exp_block[0]
		self._option_chain_expiry[underlying] = {
			"day": today,
			"expiry": expiry,
			"all": exp_block,
		}
		return expiry

	def _normalize_watchlist_exchange(self, symbol, exchange):
		sym = str(symbol).upper().strip()
		exch = str(exchange or "NSE").strip().upper()
		index_nse = {
			"NIFTY", "NIFTY 50", "BANKNIFTY", "NIFTY BANK", "FINNIFTY",
			"NIFTY FIN SERVICE", "MIDCPNIFTY", "NIFTY MID SELECT",
		}
		index_bse = {"SENSEX", "BANKEX"}
		if sym in index_nse:
			return "NSE_IDX"
		if sym in index_bse:
			return "BSE_IDX"
		exch_alias = {
			"NSE_FNO": "NFO",
			"NSE FNO": "NFO",
			"NSE_EQ": "NSE",
			"EQ": "NSE",
			"BSE_FNO": "BFO",
			"IDX_I": "NSE_IDX",
			"NSE_IDX": "NSE_IDX",
			"BSE_IDX": "BSE_IDX",
		}
		exch = exch_alias.get(exch, exch)
		if exch in ("NSE", "") and sym and (
			" CE " in sym or " PE " in sym or sym.endswith(" CE") or sym.endswith(" PE")
		):
			return "NFO"
		return exch

	def _quote_list_from_market_block(self, quote):
		"""Parse quote_data / ohlc_data / ticker_data block into C:J row."""
		if not isinstance(quote, dict):
			return [None] * 8

		def _f(val):
			if val is None or val == "":
				return None
			try:
				v = float(val)
				return v if v != 0 else None
			except (TypeError, ValueError):
				return None

		ohlc = quote.get("ohlc") if isinstance(quote.get("ohlc"), dict) else {}
		ltp = quote.get("last_price") or quote.get("ltp") or quote.get("LTP")
		return [
			_f(ltp),
			_f(quote.get("average_price") or quote.get("avg_price")),
			_f(quote.get("volume")),
			_f(quote.get("sell_quantity") or quote.get("total_sell_quantity")),
			_f(ohlc.get("open") or quote.get("open")),
			_f(ohlc.get("close") or quote.get("close")),
			_f(ohlc.get("high") or quote.get("high")),
			_f(ohlc.get("low") or quote.get("low")),
		]

	def _quote_list_from_ticker_block(self, quote):
		return self._quote_list_from_market_block(quote)

	def get_rest_ltps_for_watchlist(self, watchlist_rows, quiet=False):
		"""Batch REST LTP for sheet rows (cash/index/FNO) via ticker_data. Dhan: ~1 req/sec."""
		if not watchlist_rows:
			return {}
		instrument_exchange = {
			"NSE": "NSE", "BSE": "BSE", "NFO": "NSE", "BFO": "BSE", "MCX": "MCX",
			"CUR": "NSE", "BSE_IDX": "BSE", "NSE_IDX": "NSE",
		}
		# dhanhq marketfeed keys (see Dhan API docs / Dhan_ltp_api.py)
		ticker_segment = {
			"NSE": "NSE_EQ", "BSE": "BSE_EQ", "NFO": "NSE_FNO", "BFO": "BSE_FNO",
			"NSE_IDX": "IDX_I", "BSE_IDX": "IDX_I", "MCX": "MCX_COMM",
		}
		index_ids = {
			"NIFTY": (13, "IDX_I"), "NIFTY 50": (13, "IDX_I"),
			"BANKNIFTY": (25, "IDX_I"), "NIFTY BANK": (25, "IDX_I"),
			"FINNIFTY": (27, "IDX_I"), "NIFTY FIN SERVICE": (27, "IDX_I"),
			"MIDCPNIFTY": (442, "IDX_I"), "NIFTY MID SELECT": (442, "IDX_I"),
			"SENSEX": (51, "IDX_I"), "BANKEX": (69, "IDX_I"),
		}
		groups = {}
		out = {}
		quotes_out = {}
		for symbol, exchange in watchlist_rows:
			sym = str(symbol).strip()
			if not sym or sym.lower() == "nan":
				continue
			if sym.upper() in index_ids:
				seg, sid = index_ids[sym.upper()][1], index_ids[sym.upper()][0]
				groups.setdefault(seg, []).append((sym, int(sid)))
				continue
			exch_norm = self._normalize_watchlist_exchange(sym, exchange)
			exch_id = instrument_exchange.get(exch_norm, "NSE")
			try:
				matched = self.instrument_df[
					(
						(self.instrument_df["SEM_TRADING_SYMBOL"] == sym)
						| (self.instrument_df["SEM_CUSTOM_SYMBOL"] == sym)
					)
					& (self.instrument_df["SEM_EXM_EXCH_ID"] == exch_id)
				]
				if exch_norm in ("NSE", "BSE") and "SEM_SERIES" in matched.columns:
					eq = matched[matched["SEM_SERIES"] == "EQ"]
					if not eq.empty:
						matched = eq
				if matched.empty:
					continue
				sid = int(matched.iloc[-1]["SEM_SMST_SECURITY_ID"])
				seg = ticker_segment.get(exch_norm, "NSE")
				groups.setdefault(seg, []).append((sym, sid))
			except Exception:
				continue
		if not hasattr(self, "_rest_ltp_last_log"):
			self._rest_ltp_last_log = 0.0

		def _log_rest(msg):
			if quiet:
				return
			now = time.time()
			if now - self._rest_ltp_last_log < 45:
				return
			self._rest_ltp_last_log = now
			print(msg)

		# Dhan marketfeed LTP: max ~1 request per second
		seg_order = ("IDX_I", "NSE_EQ", "BSE_EQ", "NSE_FNO", "BSE_FNO", "MCX_COMM")
		for seg in seg_order:
			items = groups.get(seg)
			if not items:
				continue
			chunk_size = 20 if seg in ("NSE_EQ", "BSE_EQ") else 8
			for start in range(0, len(items), chunk_size):
				chunk = items[start : start + chunk_size]
				try:
					time.sleep(1.05)
					ids = [sid for _, sid in chunk]
					parsed = {}
					for api_name, fetcher in (
						("quote", self.Dhan.quote_data),
						("ohlc", self.Dhan.ohlc_data),
						("ticker", self.Dhan.ticker_data),
					):
						resp = fetcher({seg: ids})
						parsed = self._unwrap_ticker_response(resp)
						if parsed.get("_error"):
							_log_rest(f"REST {api_name} {seg}: {parsed['_error']}")
							parsed = {}
							continue
						if parsed.get(seg):
							break
					if parsed.get("_error"):
						_log_rest(
							f"REST quotes {seg} ({len(ids)} ids): {parsed['_error']} "
							"(check Data API subscription / token)"
						)
						continue
					block = parsed.get(seg) or {}
					if not block:
						_log_rest(f"REST quotes {seg}: empty for {len(ids)} ids")
					for sym, sid in chunk:
						quote = block.get(str(sid)) or block.get(sid) or {}
						row = self._quote_list_from_market_block(quote)
						if row[0] and float(row[0]) > 0:
							out[sym] = float(row[0])
							quotes_out[sym] = row
				except Exception as e:
					_log_rest(f"REST quote batch {seg}: {e}")
		if not hasattr(self, "_last_rest_quotes"):
			self._last_rest_quotes = {}
		self._last_rest_quotes = quotes_out
		return out

	def get_rest_quotes_for_watchlist(self, watchlist_rows, quiet=False):
		"""Full quote rows after get_rest_ltps_for_watchlist (uses cached batch parse)."""
		self.get_rest_ltps_for_watchlist(watchlist_rows, quiet=quiet)
		cached = getattr(self, "_last_rest_quotes", {}) or {}
		out = dict(cached)
		by_upper = {str(k).upper(): v for k, v in cached.items()}
		for sym, _ in watchlist_rows:
			s = str(sym).strip()
			if s in out:
				continue
			if s.upper() in out:
				out[s] = out[s.upper()]
				continue
			row = by_upper.get(s.upper())
			if row is not None:
				out[s] = row
		return out

	def get_option_chain(self, underlying="NIFTY", expiry=None, strike_range=10, retries=4, retry_delay=1.2):
		"""Fetch NIFTY/index option chain; ATM +/- strike_range strikes for CE and PE."""
		CHAIN_CACHE_TTL = 2.0
		STALE_CACHE_MAX = 30.0
		try:
			underlying_ids = {
				"NIFTY": (13, "IDX_I"),
				"BANKNIFTY": (25, "IDX_I"),
				"FINNIFTY": (27, "IDX_I"),
				"MIDCPNIFTY": (442, "IDX_I"),
				"SENSEX": (51, "IDX_I"),
				"BANKEX": (69, "IDX_I"),
			}
			if underlying not in underlying_ids:
				raise ValueError(f"Unsupported underlying: {underlying}")

			security_id, segment = underlying_ids[underlying]
			step = self.index_step_dict.get(underlying, 50)
			if not hasattr(self, "_option_chain_cache"):
				self._option_chain_cache = {}

			if expiry is None:
				expiry = self._get_session_expiry(underlying, security_id, segment)
				if not expiry:
					print(f"expiry_list: bad response for {underlying}")
					return None

			cache_key = f"{underlying}|{expiry}|{strike_range}"
			cached = self._option_chain_cache.get(cache_key)
			if cached and (time.time() - cached[0]) < CHAIN_CACHE_TTL:
				return cached[1]

			expiry_from_session = (
				hasattr(self, "_option_chain_expiry")
				and underlying in getattr(self, "_option_chain_expiry", {})
			)

			chain = None
			last_note = ""
			for attempt in range(retries):
				resp = self.Dhan.option_chain(security_id, segment, expiry)
				if not resp or not isinstance(resp, dict):
					last_note = "no response"
					time.sleep(retry_delay)
					continue
				if str(resp.get("status", "")).lower() != "success":
					last_note = resp.get("remarks") or resp.get("status") or "failure"
					time.sleep(retry_delay)
					continue

				raw = resp.get("data")
				parsed = None
				if isinstance(raw, dict):
					parsed = raw.get("data") if isinstance(raw.get("data"), dict) else raw
				elif isinstance(raw, str):
					if raw.strip():
						last_note = raw.strip()
					else:
						last_note = "empty data (rate limit — retrying)"
					time.sleep(retry_delay)
					continue

				if isinstance(parsed, dict) and parsed.get("oc"):
					chain = parsed
					break
				last_note = "missing oc in response"
				time.sleep(retry_delay)

			if not isinstance(chain, dict) or not chain.get("oc"):
				print(
					f"option_chain: failed after {retries} tries "
					f"({underlying} {expiry}): {last_note}"
				)
				if cached and (time.time() - cached[0]) < STALE_CACHE_MAX:
					stale = dict(cached[1])
					fresh_spot = self._rest_index_ltp(underlying)
					if fresh_spot:
						stale["spot"] = fresh_spot
						step_v = self.index_step_dict.get(underlying, 50)
						stale["atm"] = round(fresh_spot / step_v) * step_v
					return stale
				return None

			time.sleep(0.3 if expiry_from_session else retry_delay)

			spot = float(chain.get("last_price") or 0)
			if spot <= 0:
				spot = float(self._rest_index_ltp(underlying) or 0)

			atm = round(spot / step) * step
			lower = atm - (strike_range * step)
			upper = atm + (strike_range * step)

			options = []
			for strike_key, legs in (chain.get("oc") or {}).items():
				if not isinstance(legs, dict):
					continue
				strike = int(float(strike_key))
				if strike < lower or strike > upper:
					continue

				for side, option_type in (("ce", "CE"), ("pe", "PE")):
					leg = legs.get(side) if isinstance(legs.get(side), dict) else {}
					volume = int(leg.get("volume") or 0)
					ltp = float(leg.get("last_price") or 0)
					if volume <= 0 and ltp <= 0:
						continue

					opt_security_id = leg.get("security_id")
					if opt_security_id is None:
						continue
					symbol_row = self.instrument_df[
						self.instrument_df["SEM_SMST_SECURITY_ID"].astype(int) == int(opt_security_id)
					]
					symbol = (
						symbol_row.iloc[-1]["SEM_CUSTOM_SYMBOL"]
						if not symbol_row.empty
						else f"{underlying} {strike} {option_type}"
					)

					oi = int(leg.get("oi") or 0)
					prev_oi = int(leg.get("previous_oi") or 0)
					options.append(
						{
							"strike": strike,
							"option_type": option_type,
							"symbol": symbol,
							"ltp": ltp,
							"iv": float(leg.get("implied_volatility") or 0),
							"oi": oi,
							"previous_oi": prev_oi,
							"oi_change": oi - prev_oi,
							"volume": volume,
						}
					)

			result = {
				"underlying": underlying,
				"spot": spot,
				"atm": atm,
				"expiry": expiry,
				"strike_range": strike_range,
				"options": options,
			}
			self._option_chain_cache[cache_key] = (time.time(), result)
			return result
		except Exception as e:
			print(f"Exception in get_option_chain: {e}")
			self.logger.exception(f"Exception in get_option_chain: {e}")
			traceback.print_exc()
			return None


	def get_expiry(self,underlying):
		try:
			instrument_df = self.instrument_df.copy()	
			data = instrument_df[instrument_df['Name']==underlying].sort_values('ContractExpiration')
			data = pd.DataFrame(pd.to_datetime(data[data['ContractExpiration']!='1']['ContractExpiration']).dt.date.unique(),columns=['Expiry Dates'])
			
			if not data.empty:
				return data['Expiry Dates'].to_list()
			else:
				raise TypeError("check input parameter correctly for get_atm()")
		except Exception as e:
			print(f"Exception in get_expiry as: {e}")
			self.logger.exception(f"Exception in get_expiry as: {e}")
			return None

	def check_expiry_date(self,underlying,Expiry):
		try:
			data = self.instrument_df[self.instrument_df['Name']==underlying].sort_values('ContractExpiration')
			date = pd.to_datetime(data[data['ContractExpiration']!='1']['ContractExpiration']).dt.date.unique()
			if Expiry in date:
				return True
			else:
				return False
		except Exception as e:
			print(f"Exception in check_expiry_date as: {e}")
			self.logger.exception(f"Exception in check_expiry_date as: {e}")

	
	def get_freeze_quantity(self,strike):
		data =  self.instrument_df[(self.instrument_df['Description'] == strike)]
		if len(data) == 0:
			self.logger.exception("Enter valid Script Name")
			return 0
		else:
			return data.iloc[0]['FreezeQty']
	
	def get_split_order_variables(self,strike,lots):
		try:
			lot_size = self.get_lot_size(strike)
			quantity = lots*lot_size

			freeze_quantity = self.get_freeze_quantity(strike)
			split_count = quantity//freeze_quantity
			remain_quantity = quantity%freeze_quantity

			return quantity, freeze_quantity, split_count, remain_quantity		
		except Exception as e:
			print(e)
			self.logger.exception(f"Error in getting split order variables as {e}")
			return 0,0,0,0	
	

	def get_bid_ask(self,name):
		try:
			strike_exchange = self.instrument_df.loc[self.instrument_df['Description']==name].iloc[0][['ExchangeSegment']][0]
			data = instrument_df.loc[(instrument_df['ExchangeSegment'] == strike_exchange) & (instrument_df['Description'] == name)]
			exchangeInstrumentID = data.iloc[0]['ExchangeInstrumentID']
			exchange_dict = {"NSECM": 1, "NSEFO": 2, "NSECD": 3, "BSECM": 11, "BSEFO": 12}
			exchangeSegment = exchange_dict[strike_exchange]
			instruments = [{'exchangeSegment': int(exchangeSegment), 'exchangeInstrumentID': int(exchangeInstrumentID)}]
			ltp_quote = self.xts2.get_quote(Instruments=instruments, xtsMessageCode=1501, publishFormat='JSON')
			ask = json.loads(ltp_quote['result']['listQuotes'][-1])['AskInfo']['Price']
			bid = json.loads(ltp_quote['result']['listQuotes'][-1])['BidInfo']['Price']
			return ask,bid
		except Exception as e:
			print(e)
			self.logger.exception(f'get exception get_bid_ask function as {e} ')
			traceback.print_exc()


	def get_data_for_single_script(self,names:list) -> dict:
		try:
			instruments = []
			if type(names)!=list:
				names = [names]	
			for name in names:
				try:
					if (name in self.token_dict) and (name not in self.token_and_exchange):
						token 										= self.token_dict[name]['token']
						token_exchange 								= self.token_dict[name]['exchange']
						self.token_and_exchange[name] 				= {'token':token,'token_exchange':token_exchange}
					elif name not in self.token_and_exchange:
						token                                       = self.instrument_df.loc[self.instrument_df['Description']==name].iloc[0][['ExchangeInstrumentID']][0]
						token_exchange                              = self.instrument_df.loc[self.instrument_df['Description']==name].iloc[0][['ExchangeSegment']][0]
						self.token_and_exchange[name] 				= {'token':token,'token_exchange':token_exchange}
					else:
						token 										= self.token_and_exchange[name]['token']
						token_exchange 								= self.token_and_exchange[name]['token_exchange']
				except:
					print(f'{name} is not correct!! Check spelling')
					names.remove(name)
					continue
				instrument 									= {'exchangeSegment': str(self.segment_dict[token_exchange]), 'exchangeInstrumentID': str(token)}
				instruments.append(instrument)
			response = self.xts2.get_quote(Instruments=instruments, xtsMessageCode=1501, publishFormat='JSON')
			return response
		except Exception as e:
			print(e)
			self.logger.exception(f"Exception in getting get data for single script as {e}")
			traceback.print_exc()
			
	def get_stock_data(self,names:list) -> dict:
		'''
		For getting LTP, OPEN, HIGH, LOW, CLOSE Values for more than two tradingsymbol
		get_stock_data(stock_list)
		'''
		try:
			stock_data = dict()
			quote_dict = self.get_quote(names)
			if len(quote_dict)==0:
				return stock_data
			for stock in names:	
				if stock in quote_dict:			
					ltp 	= quote_dict[stock]['LastTradedPrice']				
					open 	= quote_dict[stock]['Open']
					high 	= quote_dict[stock]['High']
					low 	= quote_dict[stock]['Low']
					close 	= quote_dict[stock]['Close']
					stock_data[stock] = {'ltp':ltp,'open':open, 'high':high, 'low':low, 'close':close}
				else:
					stock_data[stock] = {'ltp':0,'open':0, 'high':0, 'low':0, 'close':0}
			
			return stock_data
		except Exception as e:
			self.logger.exception(f"Exceptionn in getting stock data as {e}")
			return dict()

	

	def get_quote(self,names):
		try:
			response = self.get_data_for_single_script(names)
			i=0
			result = {}
			if response:
				if type(names)==list:
					for i,data in enumerate(response['result']['listQuotes']):
						data = json.loads(data)
						name = self.instrument_df.loc[self.instrument_df['ExchangeInstrumentID'] == data['ExchangeInstrumentID']].iloc[0]['Description']
						result[name] = data
					return result
				else:
					data    = response['result']['listQuotes'][0]
					data    = json.loads(data)
					return data
			else:
				print('No data returned from XTS')
				return None
		except Exception as e:
			print(e)
			self.logger.exception(f"Exception in get quote function as {e}")
			traceback.print_exc()

	def get_market_depth(self, name, exchange=None):
		"""
		Best-effort market depth / totals for Order Book Imbalance (OBI).

		Returns a dict shaped like:
		    { total_buy_quantity, total_sell_quantity, bids, asks }

		Notes:
		- Uses XTS quote payload if available; fields vary by instrument/exchange.
		- If totals aren't present, attempts to aggregate per-level bid/ask quantities.
		"""
		try:
			q = self.get_quote(name)
			if not q:
				return None

			# Common XTS keys (vary by segment). We'll parse what exists.
			depth = {}
			total_buy = (
				q.get("TotalBuyQuantity")
				or q.get("totalBuyQuantity")
				or (q.get("Touchline") or {}).get("TotalBuyQuantity")
				or (q.get("Touchline") or {}).get("totalBuyQuantity")
			)
			total_sell = (
				q.get("TotalSellQuantity")
				or q.get("totalSellQuantity")
				or (q.get("Touchline") or {}).get("TotalSellQuantity")
				or (q.get("Touchline") or {}).get("totalSellQuantity")
			)

			# Per-level lists sometimes appear as Bid/Ask arrays or BidInfo/AskInfo blocks.
			bids = q.get("Bids") or q.get("Bid") or q.get("bid") or []
			asks = q.get("Asks") or q.get("Ask") or q.get("ask") or []

			# If we only have top-of-book blocks, wrap them to keep a consistent list format
			if not bids and q.get("BidInfo"):
				bids = [q.get("BidInfo")]
			if not asks and q.get("AskInfo"):
				asks = [q.get("AskInfo")]

			# Normalize list items to {price, quantity}
			def _norm(side):
				out = []
				for row in side or []:
					if not row:
						continue
					out.append({
						"price": row.get("Price") or row.get("price"),
						"quantity": row.get("Quantity") or row.get("quantity") or row.get("Qty") or row.get("qty") or 0,
					})
				return out

			depth["bids"] = _norm(bids)
			depth["asks"] = _norm(asks)

			# Prefer totals if present; else compute from level quantities
			if total_buy is None:
				total_buy = sum(int(x.get("quantity") or 0) for x in depth["bids"])
			if total_sell is None:
				total_sell = sum(int(x.get("quantity") or 0) for x in depth["asks"])

			depth["total_buy_quantity"] = float(total_buy or 0)
			depth["total_sell_quantity"] = float(total_sell or 0)
			return depth
		except Exception as e:
			try:
				self.logger.exception(f"Exception in get_market_depth: {e}")
			except Exception:
				pass
			return None


	def get_orderhistory(self, order_id):
		try:
			flag = True
			while flag == True:
				try:
					time.sleep(1)
					order_history = self.xts1.get_order_history(appOrderID=order_id,clientID=self.client_code)
					send_order_history = order_history['result'][-1]
					flag = False
				except Exception as e:
					pass
			return send_order_history['OrderStatus']
		except Exception as e:
			self.logger.exception("exception in get_orderhistory {0} ".format(str(e)))
	

	def get_executed_price(self, order_id):
		try:
			flag = True
			while flag == True:
				try:
					time.sleep(1)
					order_history = self.xts1.get_order_history(appOrderID=order_id,clientID=self.client_code)
					send_order_history = order_history['result'][-1]
					flag = False
				except Exception as e:
					pass
			order_price = send_order_history['OrderAverageTradedPrice']
			if order_price is None:
				order_price = 0
			elif type(order_price)==str:
				if len(order_price)==0:
					order_price = 0
			order_price = float(order_price)

			return order_price
		except Exception as e:
			self.logger.exception("exception in get_orderhistory {0}".format(str(e)))


	def modify_order(self,appOrderID:str,modifiedOrderType:str, modifiedOrderQuantity:int, modifiedLimitPrice:int, modifiedStopPrice:int, trade_type:str) -> str:
		try:
			p_orders = pd.DataFrame(self.xts1.get_order_book()['result'])
			before_len = len(p_orders)
			self.order_Type = {'LIMIT': self.xts1.ORDER_TYPE_LIMIT, 'MARKET': self.xts1.ORDER_TYPE_MARKET,'STOPLIMIT': self.xts1.ORDER_TYPE_STOPLIMIT, 'STOPMARKET': self.xts1.ORDER_TYPE_STOPMARKET}
			product = {'MIS': self.xts1.PRODUCT_MIS, 'NRML': self.xts1.PRODUCT_NRML, 'CNC': 'CNC'}
			Validity = {'DAY': self.xts1.VALIDITY_DAY, 'IOC': 'IOC'}


			product_Type = product[trade_type.upper()]
			order_type = self.order_Type[modifiedOrderType.upper()]
			time_in_force = Validity['DAY']

			order = self.xts1.modify_order(appOrderID=appOrderID,modifiedProductType=product_Type,modifiedOrderType=order_type,modifiedOrderQuantity=modifiedOrderQuantity,modifiedDisclosedQuantity=0,modifiedLimitPrice=modifiedLimitPrice,modifiedStopPrice=modifiedStopPrice,modifiedTimeInForce=time_in_force,orderUniqueIdentifier="123abc")
			order_id = order['result']['AppOrderID']
			# time.sleep(1)
			c_orders = pd.DataFrame(self.xts1.get_order_book()['result'])
			after_len = len(c_orders)
			if order_id == None:
				print("didnt find order id from api trying to get it via wrapper")
				if before_len < after_len:
					order_id = c_orders.iloc[-1]['order_id']
					return order_id
			else:
				return str(order_id)
		except Exception as e:
			self.logger.exception(f'Got exception in modify_order as {e}')
			traceback.print_exc()

	def cancel_order(self,OrderID:str)->None:
		try:
			response = self.xts1.cancel_order(appOrderID=OrderID,orderUniqueIdentifier='123abc',clientID=self.client_code)
		except Exception as e:
			self.logger.exception(f'Got exception in cancel_order as {e}')
			traceback.print_exc()

	def check_valid_instrument(self,name):
		try:
			df = self.instrument_df[(self.instrument_df['Description']==name) | (self.instrument_df['Name']==name)]
			if len(df) != 0:
				return f"instrument {name} is valid"
			else:
				return f"instrument {name} is invalid"

		except Exception as e:
			print(e)
			self.logger.exception(f'Exception at check valid instrument as {e}')
			traceback.print_exc()
			return f"instrument {name} is invalid"

	def send_telegram_alert(self,message,receiver_chat_id,bot_token=None):
		"""
			1st receiver need to connect with BOT TradeHull Bot token is "5189311784:AAHgQxiQ6uhc1Qf7AvPAiUoUzxetu8uKP58" 
		"""
		try:
			bot_token = "5189311784:AAHgQxiQ6uhc1Qf7AvPAiUoUzxetu8uKP58"
			send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + receiver_chat_id + '&text=' + message
			response = requests.get(send_text)
		except Exception as e:
			print(e)
			self.logger.exception(f"Exception in sending telegram alerts as {e}")
			traceback.print_exc()
