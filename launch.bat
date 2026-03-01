@echo off
REM Investment Tracker - Double-click to launch

REM Change to the directory where this script lives
cd /d "%~dp0"

echo ==========================================
echo   Investment Tracker - Starting Up
echo ==========================================
echo.

REM Check for Python 3 (also check standard install location)
set PYTHON=
python --version >nul 2>&1 && set PYTHON=python
if not defined PYTHON (
    py --version >nul 2>&1 && set PYTHON=py
)
if not defined PYTHON (
    if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
        set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%PATH%"
        set PYTHON=python
    )
)
if not defined PYTHON (
    if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" (
        set "PATH=%LOCALAPPDATA%\Programs\Python\Python313;%LOCALAPPDATA%\Programs\Python\Python313\Scripts;%PATH%"
        set PYTHON=python
    )
)
if not defined PYTHON (
    echo ERROR: Python 3 is not installed.
    echo Please install Python 3 from https://python.org
    echo.
    pause
    exit /b 1
)

REM Create virtual environment if it doesn't exist
if not exist ".venv" (
    echo Creating virtual environment (first run only^)...
    %PYTHON% -m venv .venv
    echo.
)

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Install/upgrade dependencies
echo Checking dependencies...
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
echo Dependencies OK.
echo.

REM Launch Streamlit
echo Starting Investment Tracker...
echo The app will open in your browser shortly.
echo To stop: close this window or press Ctrl+C.
echo.
streamlit run app.py --server.headless=true --browser.gatherUsageStats=false

REM Keep terminal open if Streamlit exits unexpectedly
pause
