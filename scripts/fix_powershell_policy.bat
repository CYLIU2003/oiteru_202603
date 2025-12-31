@echo off
chcp 65001 > nul
echo.
echo ========================================
echo   PowerShell Execution Policy Fix Tool
echo ========================================
echo.
echo This tool enables PowerShell script execution.
echo.
echo [Method 1] Change for current user only (no admin required)
echo.

:: 現在のユーザーの実行ポリシーを変更
powershell.exe -NoProfile -Command "Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo SUCCESS!
    echo.
    echo PowerShell scripts are now enabled.
    echo Please close this terminal and open a new one.
) else (
    echo.
    echo Method 1 failed. Trying Method 2...
    echo.
    echo [Method 2] Change with admin privileges
    echo A new window will open. Click "Yes" to allow.
    echo.
    
    :: 管理者権限で再試行
    powershell.exe -NoProfile -Command "Start-Process -FilePath 'powershell.exe' -ArgumentList '-NoProfile -Command \"Set-ExecutionPolicy RemoteSigned -Scope CurrentUser -Force; Write-Host Done -ForegroundColor Green; Start-Sleep 3\"' -Verb RunAs"
)

echo.
pause

