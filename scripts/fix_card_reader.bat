@echo off
echo ========================================
echo   カードリーダー完全修正
echo ========================================
echo.

echo PowerShellで修正スクリプトを実行します...
echo 管理者権限が必要です（UACプロンプトで「はい」をクリック）
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Start-Process powershell.exe -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File \"%~dp0fix_card_reader.ps1\"' -Verb RunAs"

echo.
echo PowerShellウィンドウで処理を確認してください
echo.
pause
