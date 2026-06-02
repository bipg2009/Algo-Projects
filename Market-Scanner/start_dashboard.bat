@echo off
echo ==============================================
echo   Starting STOCK FINDER Dashboard...
echo ==============================================

if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing dependencies...
pip install --no-cache-dir fastapi uvicorn pydantic python-dotenv pandas yfinance mibian xlwings requests dhanhq

if %errorlevel% neq 0 (
    echo.
    echo Failed to install dependencies. Please check the error above.
    pause
    exit /b %errorlevel%
)

echo Starting Server...
start http://127.0.0.1:8000

echo The dashboard is running. Do not close this window.
python -m uvicorn api:app --host 127.0.0.1 --port 8000
