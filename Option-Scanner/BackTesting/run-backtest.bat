@echo off
cd /d "%~dp0"
echo Running NSE Option Scanner BACKTEST...
py "NSE-Option-Scanner-Backtest.py" %*
pause
