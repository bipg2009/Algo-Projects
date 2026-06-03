@echo off
echo [SYSTEM] Initiating SEDA Multi-Timeframe Scanner Engine...
start cmd /k "cd C:\Biplab\ALGO-Projects\Option-Scanner\Dashboard && python Market_Scanner.py"

echo [SYSTEM] Bypassing fractured global PATH. Initiating Streamlit via explicit binary path...
start cmd /k "cd C:\Biplab\ALGO-Projects\Option-Scanner\Dashboard && C:\Users\bipla\AppData\Local\Programs\Python\Python314\Scripts\streamlit.exe run app.py"

echo [SYSTEM] Multi-threaded execution successfully dispatched.
exit
