import sys

path = 'NSE-Option-Scanner-Backtest.py'
with open(path, 'r') as f:
    c = f.read()

c = c.replace(
    '        action, reason, new_sl = mon_engine.execute_hypercare_monitoring(\n            pos_obj, df_slice, opt_row, snap["ltp"], bar_time\n        )',
    '        action, reason, new_sl = mon_engine.execute_hypercare_monitoring(\n            pos_obj, df_slice, opt_row, snap["ltp"]\n        )'
)

with open(path, 'w') as f:
    f.write(c)

print('Patched arguments correctly!')
