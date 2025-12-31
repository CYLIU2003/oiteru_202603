@echo off
chcp 65001 > nul
echo.
echo ========================================
echo    🍬 OITERU 従親機 起動
echo ========================================
echo.

set "SCRIPT_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPT_DIR%.."

cd /d "%PROJECT_DIR%"

:: 仮想環境があるか確認
if exist ".venv\Scripts\python.exe" (
    echo 仮想環境を使用して起動します...
    echo.
    
    :: 環境変数を設定（config.jsonから読む場合もあるが、念のため）
    set "DB_TYPE=mysql"
    
    :: Pythonを直接実行（実行ポリシー不要）
    .venv\Scripts\python.exe server.py
) else (
    echo 仮想環境が見つかりません。
    echo 先に仮想環境をセットアップしてください:
    echo.
    echo   python -m venv .venv
    echo   .venv\Scripts\pip install -r requirements-server.txt
    echo.
    pause
)
