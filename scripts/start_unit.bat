@echo off
chcp 65001 > nul
echo.
echo ========================================
echo    🍬 OITERU 子機 起動
echo ========================================
echo.

set "SCRIPT_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPT_DIR%.."

cd /d "%PROJECT_DIR%"

:: 仮想環境があるか確認
if exist ".venv\Scripts\python.exe" (
    echo 仮想環境を使用して起動します...
    echo.
    
    :: Pythonを直接実行（実行ポリシー不要）
    .venv\Scripts\python.exe unit_client.py
) else (
    echo 仮想環境が見つかりません。
    echo 先に仮想環境をセットアップしてください:
    echo.
    echo   python -m venv .venv
    echo   .venv\Scripts\pip install -r requirements-client.txt
    echo.
    pause
)
