@echo off
setlocal
title SmartxCV
cd /d "%~dp0"

echo.
echo   ==========================================
echo     SmartxCV - AI CV Builder
echo   ==========================================
echo.

rem --- 1. Create the private Python environment on first run ---
if exist "venv\Scripts\python.exe" goto :deps
echo   First run: creating a private Python environment...
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 -m venv venv
) else (
    python -m venv venv
)
if not exist "venv\Scripts\python.exe" goto :nopython

rem --- 2. Install requirements only if they are missing ---
:deps
"venv\Scripts\python.exe" -c "import streamlit" >nul 2>nul
if %errorlevel%==0 goto :start
echo   Installing requirements (first run only, needs internet)...
"venv\Scripts\python.exe" -m pip install --upgrade pip
"venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :installfail

rem --- 3. Start the app (your browser opens automatically) ---
:start
echo.
echo   SmartxCV is starting at  http://localhost:8501
echo   Keep this window open while you use the app.
echo   To stop SmartxCV, close this window or press Ctrl+C.
echo.
start "" /b cmd /c "ping -n 6 127.0.0.1 >nul & start "" http://localhost:8501"
"venv\Scripts\python.exe" -m streamlit run app.py --server.port 8501 --server.headless true
goto :end

:nopython
echo.
echo   [!] Python was not found.
echo       Install Python 3.10 or newer from https://www.python.org/downloads/
echo       and tick "Add python.exe to PATH" during setup. Then run this file again.
goto :end

:installfail
echo.
echo   [!] Installing requirements failed. Check your internet connection and run this file again.

:end
echo.
pause
