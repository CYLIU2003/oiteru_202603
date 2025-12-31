@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

echo.
echo ========================================
echo    🍬 OITERU 設定ウィザード
echo ========================================
echo.

:: プロジェクトディレクトリを取得
set "SCRIPT_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPT_DIR%.."
set "CONFIG_PATH=%PROJECT_DIR%\config.json"

:: タイプ選択
echo 何を設定しますか？
echo   1. 子機（お菓子を出す端末）
echo   2. 従親機（サブサーバー）
echo.
set /p CHOICE="選択 [1/2]: "

if "%CHOICE%"=="2" (
    set "TYPE=sub-parent"
    set "DEFAULT_NAME=従親機A"
) else (
    set "TYPE=unit"
    set "DEFAULT_NAME=新規子機"
)

echo.
echo 【%TYPE% の設定を開始します】
echo.

:: 名前入力
set /p NAME="名前を入力 (例: 3号機) [%DEFAULT_NAME%]: "
if "%NAME%"=="" set "NAME=%DEFAULT_NAME%"

:: 設置場所
set /p LOCATION="設置場所を入力 (例: 7号館1階): "
if "%LOCATION%"=="" set "LOCATION=未設定"

:: パスワード
set /p PASSWORD="パスワードを入力 (空で自動生成): "
if "%PASSWORD%"=="" (
    :: 簡易的なランダム生成
    set "PASSWORD=pw%RANDOM%%RANDOM%"
    echo   → 自動生成されたパスワード: !PASSWORD!
)

:: サーバーIP
set "SERVER_IP=100.114.99.67"
echo.
echo 親機のIPアドレス: %SERVER_IP%
set /p CHANGE_IP="変更しますか？ [y/N]: "
if /i "%CHANGE_IP%"=="y" (
    set /p SERVER_IP="新しいIPアドレスを入力: "
)

:: 設定ファイル生成
echo.
echo 設定ファイルを作成中...

if "%TYPE%"=="unit" (
    (
        echo {
        echo     "SERVER_URL": "http://%SERVER_IP%:5000",
        echo     "UNIT_NAME": "%NAME%",
        echo     "UNIT_PASSWORD": "%PASSWORD%",
        echo     "UNIT_LOCATION": "%LOCATION%",
        echo     "IS_SECONDARY": false,
        echo     "MOTOR_TYPE": "SERVO",
        echo     "CONTROL_METHOD": "RASPI_DIRECT",
        echo     "USE_SENSOR": true,
        echo     "GREEN_LED_PIN": 17,
        echo     "RED_LED_PIN": 27,
        echo     "SENSOR_PIN": 22,
        echo     "ARDUINO_PORT": "/dev/ttyACM0",
        echo     "MOTOR_SPEED": 100,
        echo     "MOTOR_DURATION": 2.0,
        echo     "MOTOR_REVERSE": false
        echo }
    ) > "%CONFIG_PATH%"
) else (
    (
        echo {
        echo     "DB_TYPE": "mysql",
        echo     "MYSQL_HOST": "%SERVER_IP%",
        echo     "MYSQL_PORT": 3306,
        echo     "MYSQL_DATABASE": "oiteru",
        echo     "MYSQL_USER": "oiteru_user",
        echo     "MYSQL_PASSWORD": "oiteru_password_2025",
        echo     "SERVER_NAME": "%NAME%",
        echo     "SERVER_LOCATION": "%LOCATION%",
        echo     "IS_SECONDARY": true
        echo }
    ) > "%CONFIG_PATH%"
)

echo.
echo ========================================
echo    ✅ 設定が完了しました！
echo ========================================
echo.
echo 保存先: %CONFIG_PATH%
echo.
echo --- 設定内容 ---
type "%CONFIG_PATH%"
echo.

if "%TYPE%"=="unit" (
    echo 【次のステップ】
    echo   1. 親機の管理画面で子機を登録
    echo      → http://%SERVER_IP%:5000/admin/units/new
    echo   2. 子機を起動
    echo      → scripts\start_unit.bat
) else (
    echo 【次のステップ】
    echo   1. 従親機を起動
    echo      → scripts\start_sub_parent.bat
)
echo.
pause
