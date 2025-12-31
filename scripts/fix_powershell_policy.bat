@echo off
chcp 65001 > nul
echo.
echo ========================================
echo   PowerShell 実行ポリシー修正ツール
echo ========================================
echo.
echo このツールは、PowerShellスクリプトを実行できるように
echo 実行ポリシーを変更します。
echo.
echo 【注意】管理者権限が必要です。
echo.
pause

:: 管理者権限で実行
powershell -Command "Start-Process powershell -ArgumentList '-NoProfile -ExecutionPolicy Bypass -Command Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force; Write-Host \"実行ポリシーを変更しました！\" -ForegroundColor Green; pause' -Verb RunAs"

echo.
echo 完了しました。PowerShellスクリプトが実行できるようになりました。
echo.
pause
