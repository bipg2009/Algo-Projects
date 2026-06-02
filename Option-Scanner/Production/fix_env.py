import sys

path = 'multi_day_backtest.py'
with open(path, 'r') as f:
    c = f.read()

if 'os.environ["IS_BACKTEST"] = "1"' not in c:
    c = c.replace(
        'import sys\nimport pandas as pd',
        'import sys\nimport pandas as pd\nimport os\nos.environ["IS_BACKTEST"] = "1"\n'
    )
    with open(path, 'w') as f:
        f.write(c)
    print("Hardcoded IS_BACKTEST=1 into multi_day_backtest.py")
else:
    print("Already hardcoded")
