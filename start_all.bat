@echo off
echo ====================================
echo    CareerZone - Start All Services
echo ====================================
echo.
echo Starting: API + Kafka + Cleanup Scheduler
echo.

cd /d "%~dp0"

REM Check if virtual environment exists
if exist venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM
echo
echo Starting all services...
echo Press Ctrl+C to stop all services
echo.

python start.py

pause
