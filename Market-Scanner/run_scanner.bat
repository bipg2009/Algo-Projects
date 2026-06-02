@echo off
title Market Scanner
echo ==============================================
echo   Starting MARKET SCANNER...
echo   (Fetching data from Dhan API - please wait ~40 seconds)
echo ==============================================

call venv\Scripts\activate.bat
python run_scanner.py

echo.
echo ==============================================
pause
