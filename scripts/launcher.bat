@echo off
REM =========================================
REM OITELU ランチャー起動スクリプト (Windows)
REM =========================================

echo.
echo ========================================
echo   OITELU System Launcher
echo ========================================
echo.
echo どちらのランチャーを起動しますか？
echo.
echo   1. GUI版 (グラフィカルインターフェース)
echo   2. CUI版 (BIOS風テキストインターフェース)
echo.

set /p choice="選択してください [1-2]: "

if "%choice%"=="1" (
    echo.
    echo GUI版ランチャーを起動しています...
    python launcher_gui.py
) else if "%choice%"=="2" (
    echo.
    echo CUI版ランチャーを起動しています...
    python launcher_cui.py
) else (
    echo.
    echo 無効な選択です。デフォルトでGUI版を起動します。
    timeout /t 2 /nobreak >nul
    python launcher_gui.py
)

pause
