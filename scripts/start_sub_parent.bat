@echo off
chcp 65001 > nul
echo.
echo ========================================
echo    OITERU Sub-Parent Server Start
echo ========================================
echo.

set "SCRIPT_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPT_DIR%.."

cd /d "%PROJECT_DIR%"

:: Check if venv exists
if exist ".venv\Scripts\python.exe" (
    echo Starting with virtual environment...
    echo.
    
    set "DB_TYPE=mysql"
    
    .venv\Scripts\python.exe server.py
) else (
    echo Virtual environment not found.
    echo Please setup first:
    echo.
    echo   python -m venv .venv
    echo   .venv\Scripts\pip install -r requirements-server.txt
    echo.
    pause
)
