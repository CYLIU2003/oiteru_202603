@echo off
echo ========================================
echo   カードリーダー接続スクリプト
echo ========================================
echo.

echo 管理者権限でPowerShellを起動します...
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Start-Process powershell.exe -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File \"%~dp0attach_card_reader.ps1\"' -Verb RunAs"

echo.
echo PowerShellウィンドウで処理を確認してください
echo.
pause
