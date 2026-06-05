import sys
import datetime

path = 'NSE-Option-Scanner-Backtest.py'
with open(path, 'r') as f:
    c = f.read()

c = c.replace(
    'action, reason, new_sl = mon_engine.monitor_position(position, snap)',
    '''from models import TradePosition
        import datetime
        pos_obj = TradePosition(
            symbol="NIFTY", option_type="CE", qty=75,
            entry_ltp=position["entry_ltp"],
            target=position.get("target", position["entry_ltp"] + 60),
            sl=position["sl"],
            initial_sl=position.get("initial_sl", position["sl"]),
            margin_used=0.0,
            entry_time=position.get("entry_time", bar_time),
            entry_oi=position.get("entry_oi", opt.get("oi", 0)),
            peak_price=position.get("max_ltp", snap["ltp"])
        )
        opt_row = {"oi": opt.get("oi", 0)}
        action, reason, new_sl = mon_engine.execute_hypercare_monitoring(
            pos_obj, df_slice, opt_row, snap["ltp"], bar_time
        )'''
)

with open(path, 'w') as f:
    f.write(c)
print('Patched monitor_position to execute_hypercare_monitoring successfully!')
