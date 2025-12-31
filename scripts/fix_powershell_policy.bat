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
echo 【方法1】現在のユーザーのみ変更（管理者権限不要）
echo.

:: 現在のユーザーの実行ポリシーを変更
powershell.exe -NoProfile -Command "Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ 成功しました！
    echo.
    echo PowerShellスクリプトが実行できるようになりました。
    echo ターミナルを一度閉じて、再度開いてください。
) else (
    echo.
    echo ❌ 方法1が失敗しました。方法2を試します...
    echo.
    echo 【方法2】管理者権限で変更
    echo 新しいウィンドウが開きます。「はい」をクリックしてください。
    echo.
    
    :: 管理者権限で再試行
    powershell.exe -NoProfile -Command "Start-Process -FilePath 'powershell.exe' -ArgumentList '-NoProfile -Command \"Set-ExecutionPolicy RemoteSigned -Scope CurrentUser -Force; Write-Host 完了しました -ForegroundColor Green; Start-Sleep 3\"' -Verb RunAs"
)

echo.
pause

