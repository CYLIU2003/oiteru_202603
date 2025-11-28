@echo off
echo ========================================
echo   OITELU 親機起動 (MySQL版)
echo ========================================
echo.

cd /d "%~dp0"

echo WSL環境で起動スクリプトを実行します...
echo.

wsl bash -c "cd /mnt/c/Users/Owner/Desktop/oiteru_250827_restAPI && ./start_oiteru_mysql.sh"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo   起動完了！
    echo ========================================
    echo.
    echo 管理画面: http://localhost:5000/admin
    echo.
) else (
    echo.
    echo エラーが発生しました
    echo.
)

pause
