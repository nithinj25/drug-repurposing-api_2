@echo off
REM Start API in background
echo Starting Drug Repurposing API...
start cmd /k "cd src && python api.py"

REM Wait a moment for API to start
timeout /t 3 /nobreak

REM Start React frontend
echo Starting React Frontend...
cd ui-react
call npm start
