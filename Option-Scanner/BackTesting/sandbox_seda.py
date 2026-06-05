import os
import sys
import time
import datetime
import pandas as pd
from dotenv import load_dotenv

from Dhan_Tradehull import Tradehull
from STRATEGies.analytics.timeframe_manager import CandleAggregator
from STRATEGies.analytics.state_engine import StateClassifier
import indicator_engine as Indicators
from system_health import system_health

sys.stdout.reconfigure(encoding='utf-8')

load_dotenv("cred.env")
tsl = Tradehull(os.getenv("DHAN_CLIENT_CODE"), os.getenv("DHAN_TOKEN_ID"))

print("Fetching NIFTY 1m data...")
df_1m = tsl.get_intraday_data("NIFTY", "NSE", 1)

if df_1m is not None and not df_1m.empty:
    print(f"df_1m fetched: {len(df_1m)} rows.")
    
    df_1m = tsl.add_supertrend(df_1m, period=10, multiplier=3)
    df_1m = Indicators.add_adx(df_1m)
    df_1m = Indicators.add_vwap(df_1m)
    
    df_1m_copy = df_1m.copy()
    multi_dfs = CandleAggregator.resample_1m_to_multi(df_1m_copy)
    df_3m = multi_dfs.get("3m", pd.DataFrame())
    df_5m = multi_dfs.get("5m", pd.DataFrame())
    df_10m = multi_dfs.get("10m", pd.DataFrame())
    
    print(f"Aggregated rows -> 3m: {len(df_3m)}, 5m: {len(df_5m)}, 10m: {len(df_10m)}")
    
    if not df_10m.empty: 
        df_10m = Indicators.add_ema(df_10m)
        df_10m = Indicators.add_adx(df_10m)
        df_10m = Indicators.add_supertrend(df_10m)
    if not df_5m.empty: df_5m = Indicators.add_ema(df_5m)
    if not df_3m.empty: df_3m = Indicators.add_vwap(df_3m)
    
    if "EMA9" in df_10m.columns: df_10m["ema_9"] = df_10m["EMA9"]
    if "EMA9" in df_5m.columns: df_5m["ema_9"] = df_5m["EMA9"]
    if "EMA20" in df_5m.columns: df_5m["ema_21"] = df_5m["EMA20"]
    if "VWAP" in df_3m.columns: df_3m["vwap"] = df_3m["VWAP"]
    
    chain = {"pcr_val": 1.0, "options": []}
    
    # Run the newly fixed datetime clock comparison
    system_health.startup_warmup = 0 # override warmup for immediate test
    system_health.update_and_check(df_1m)
    health_status = system_health.get_health_status()
    print(f"[System Health]: {health_status}")
    
    ctx = StateClassifier.build_market_context(df_1m, df_3m, df_5m, df_10m, chain)
    
    total_score = ctx.regime_10m.score + ctx.structure_5m.score + ctx.confirmation_3m.score + ctx.execution_1m.score + ctx.derivatives.score
    
    print(f"   └── [SEDA SCORE: {total_score}]")
    print(f"       10m REGIME: {ctx.regime_10m.state} ({ctx.regime_10m.score} pts)")
    print(f"        5m STRUCT: {ctx.structure_5m.state} ({ctx.structure_5m.score} pts)")
    print(f"        3m PARTIC: {ctx.confirmation_3m.state} ({ctx.confirmation_3m.score} pts)")
    print(f"       DERIVATIVE: {ctx.derivatives.pcr_bias} ({ctx.derivatives.score} pts)")
    print(f"        1m EXECUT: {ctx.execution_1m.state} ({ctx.execution_1m.score} pts)")
else:
    print("df_1m was empty!")
