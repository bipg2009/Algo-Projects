import os, sys
import pandas as pd
os.environ["IS_BACKTEST"] = "1"
import Option_strategy_core as core
import backtest_helpers as bh
import backtest_dhan_client
import importlib.util

filename = "NSE-Option-Scanner-Backtest.py"
file_path = os.path.join(os.path.dirname(__file__), filename)
spec = importlib.util.spec_from_file_location("backtest_engine", file_path)
module = importlib.util.module_from_spec(spec)
sys.modules["backtest_engine"] = module
spec.loader.exec_module(module)

test_date = "2026-01-01"
sc = backtest_dhan_client.get_scanner_module()
nifty_1m = module.fetch_nifty_bars(sc.tsl, test_date, 1)
test_day = pd.to_datetime(test_date).date()
nifty_1m = nifty_1m[pd.to_datetime(nifty_1m["start_Time"]).dt.date == test_day].reset_index(drop=True)
legs = module.align_legs(module.fetch_option_legs(sc.tsl, test_date, 1), len(nifty_1m) // 5 + 1)

prev_close = float(nifty_1m.iloc[0]["close"])
today_open = float(nifty_1m.iloc[0]["open"])

for i in range(30, len(nifty_1m)):
    chain = module.build_chain_at_bar(legs, module.option_bar_idx(i), test_date, "NIFTY")
    if not chain: continue
    df_slice = bh.prepare_nifty_1m(nifty_1m.iloc[: i + 1])
    pcr = bh.pcr_from_chain(chain)
    
    spot = chain["spot"]
    atm = round(spot / 50) * 50
    
    for opt in chain["options"]:
        ot = opt["option_type"]
        target = atm - 100 if ot == "CE" else atm + 100
        if int(opt["strike"]) != int(target): continue
        
        opt_row = {
            "symbol": opt["display_symbol"],
            "strike": opt["strike"],
            "volume": opt.get("volume", 0),
            "oi_change": opt.get("oi_change", 0),
        }
        
        score = core.build_score(opt_row, ot, df_slice, pcr, False)
        if score >= 90:
            passed, reason, details = core.explain_trigger_failure(
                df_slice, ot, opt_row, spot, prev_close, today_open, pcr, None
            )
            print(f"[{bh.format_ist(nifty_1m.iloc[i]['start_Time'])}] {ot} Score: {score} -> Passed: {passed}, Reason: {reason}")
