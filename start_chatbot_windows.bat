@echo off
setlocal

REM Procurement Chatbot - Windows Quick Start
REM Double-click this file from the project folder to start the server.

cd /d "%~dp0"

echo Procurement Chatbot - Starting Server
echo ==========================================
echo.

REM Find a usable Python command.
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    set "PYTHON_CMD=py -3"
) else (
    where python >nul 2>nul
    if %ERRORLEVEL% EQU 0 (
        set "PYTHON_CMD=python"
    ) else (
        echo ERROR: Python was not found.
        echo Install Python 3, then run this file again.
        echo.
        pause
        exit /b 1
    )
)

REM Check if virtual environment exists.
if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment not found. Creating...
    %PYTHON_CMD% -m venv .venv
    if %ERRORLEVEL% NEQ 0 (
        echo.
        echo ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo Virtual environment created.
)

REM Activate virtual environment.
call ".venv\Scripts\activate.bat"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Failed to activate virtual environment.
    pause
    exit /b 1
)
echo Virtual environment activated.

REM Install/update requirements.
echo Installing dependencies...
python -m pip install -q -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Failed to install dependencies.
    pause
    exit /b 1
)
echo Dependencies installed.

echo.
echo ==========================================
echo Chatbot is starting...
echo ==========================================
echo.
echo Server:   http://localhost:8950
echo API Docs: http://localhost:8950/docs
echo ReDoc:    http://localhost:8950/redoc
echo.
echo Press Ctrl+C to stop the server.
echo ==========================================
echo.

python chatbot.py

echo.
echo Chatbot stopped.
pause
