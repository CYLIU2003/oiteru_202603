@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

echo.
echo ========================================
echo    OITERU Setup Wizard
echo ========================================
echo.

:: プロジェクトディレクトリを取得
set "SCRIPT_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPT_DIR%.."
set "CONFIG_PATH=%PROJECT_DIR%\config.json"

:: タイプ選択
echo What do you want to setup?
echo   1. Unit (Raspberry Pi dispenser)
echo   2. Sub-parent (Secondary server)
echo.
set /p CHOICE="Select [1/2]: "

if "%CHOICE%"=="2" (
    set "TYPE=sub-parent"
    set "DEFAULT_NAME=SubParentA"
) else (
    set "TYPE=unit"
    set "DEFAULT_NAME=Unit1"
)

echo.
echo Setting up: %TYPE%
echo.

:: 名前入力
set /p NAME="Enter name (e.g. Unit3, BuildingA) [%DEFAULT_NAME%]: "
if "%NAME%"=="" set "NAME=%DEFAULT_NAME%"

:: 設置場所
set /p LOCATION="Enter location (e.g. Building7-1F): "
if "%LOCATION%"=="" set "LOCATION=NotSet"

:: パスワード
set /p PASSWORD="Enter password (empty for auto-generate): "
if "%PASSWORD%"=="" (
    :: 簡易的なランダム生成
    set "PASSWORD=pw%RANDOM%%RANDOM%"
    echo   Auto-generated password: !PASSWORD!
)

:: サーバーIP
set "SERVER_IP=100.114.99.67"
echo.
echo Parent server IP: %SERVER_IP%
set /p CHANGE_IP="Change it? [y/N]: "
if /i "%CHANGE_IP%"=="y" (
    set /p SERVER_IP="Enter new IP address: "
)

:: 設定ファイル生成
echo.
echo Creating config file...

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
echo    Setup Complete!
echo ========================================
echo.
echo Saved to: %CONFIG_PATH%
echo.
echo --- Configuration ---
type "%CONFIG_PATH%"
echo.

if "%TYPE%"=="unit" (
    echo Next steps:
    echo   1. Register unit at: http://%SERVER_IP%:5000/admin/units/new
    echo   2. Start unit: scripts\start_unit.bat
) else (
    echo Next steps:
    echo   1. Start sub-parent: scripts\start_sub_parent.bat
)
echo.
pause
