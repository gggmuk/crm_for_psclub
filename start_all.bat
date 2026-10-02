@echo off
echo ========================================
echo   Gaming Club - Starting All Services
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Check if Node.js is available
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js is not installed or not in PATH
    pause
    exit /b 1
)

echo [1/2] Starting Django Backend...
start "Django Backend" cmd /k "python manage.py runserver"
timeout /t 3 >nul

echo [2/2] Starting Telegram Bot...
start "Telegram Bot" cmd /k "cd tg_bot && node index.js"
timeout /t 2 >nul

echo.
echo ========================================
echo   All services started successfully!
echo ========================================
echo.
echo Backend:   http://127.0.0.1:8000
echo Dashboard: http://127.0.0.1:8000/dashboard/
echo.
echo Press any key to stop all services...
pause >nul

echo.
echo Stopping all services...
taskkill /FI "WindowTitle eq Django Backend*" /T /F >nul 2>&1
taskkill /FI "WindowTitle eq Telegram Bot*" /T /F >nul 2>&1

echo All services stopped.
pause
