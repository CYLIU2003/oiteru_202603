<#
.SYNOPSIS
    OITERU 設定ウィザード（Windows用）
.DESCRIPTION
    従親機・子機の設定を対話形式で簡単に作成します
.EXAMPLE
    .\setup_config.ps1
    .\setup_config.ps1 -Type unit -Name "3号機" -Location "5号館2階"
#>

param(
    [ValidateSet("unit", "sub-parent")]
    [string]$Type,
    [string]$Name,
    [string]$Location,
    [string]$Password,
    [string]$ServerIP = "100.114.99.67"
)

$configPath = Join-Path (Split-Path $PSScriptRoot) "config.json"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   🍬 OITERU 設定ウィザード" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# タイプ選択
if (-not $Type) {
    Write-Host "何を設定しますか？" -ForegroundColor Yellow
    Write-Host "  1. 子機（お菓子を出す端末）"
    Write-Host "  2. 従親機（サブサーバー）"
    Write-Host ""
    $choice = Read-Host "選択 [1/2]"
    $Type = if ($choice -eq "2") { "sub-parent" } else { "unit" }
}

Write-Host ""
Write-Host "【$Type の設定を開始します】" -ForegroundColor Green
Write-Host ""

# 名前入力
if (-not $Name) {
    $defaultName = if ($Type -eq "unit") { "新規子機" } else { "従親機A" }
    $Name = Read-Host "名前を入力 (例: 3号機、A棟子機) [$defaultName]"
    if ([string]::IsNullOrWhiteSpace($Name)) { $Name = $defaultName }
}

# 設置場所
if (-not $Location) {
    $Location = Read-Host "設置場所を入力 (例: 7号館1階、本館ロビー)"
    if ([string]::IsNullOrWhiteSpace($Location)) { $Location = "未設定" }
}

# パスワード
if (-not $Password) {
    $Password = Read-Host "パスワードを入力 (何も入力しなければ自動生成)"
    if ([string]::IsNullOrWhiteSpace($Password)) {
        $Password = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 12 | ForEach-Object {[char]$_})
        Write-Host "  → 自動生成されたパスワード: $Password" -ForegroundColor Magenta
    }
}

# サーバーIP確認
Write-Host ""
Write-Host "親機のIPアドレス: $ServerIP" -ForegroundColor Cyan
$changeIP = Read-Host "変更しますか？ [y/N]"
if ($changeIP -eq "y" -or $changeIP -eq "Y") {
    $ServerIP = Read-Host "新しいIPアドレスを入力"
}

# 設定生成
if ($Type -eq "unit") {
    $config = @{
        SERVER_URL = "http://${ServerIP}:5000"
        UNIT_NAME = $Name
        UNIT_PASSWORD = $Password
        UNIT_LOCATION = $Location
        IS_SECONDARY = $false
        MOTOR_TYPE = "SERVO"
        CONTROL_METHOD = "RASPI_DIRECT"
        USE_SENSOR = $true
        GREEN_LED_PIN = 17
        RED_LED_PIN = 27
        SENSOR_PIN = 22
        ARDUINO_PORT = "/dev/ttyACM0"
        MOTOR_SPEED = 100
        MOTOR_DURATION = 2.0
        MOTOR_REVERSE = $false
    }
} else {
    $config = @{
        DB_TYPE = "mysql"
        MYSQL_HOST = $ServerIP
        MYSQL_PORT = 3306
        MYSQL_DATABASE = "oiteru"
        MYSQL_USER = "oiteru_user"
        MYSQL_PASSWORD = "oiteru_password_2025"
        SERVER_NAME = $Name
        SERVER_LOCATION = $Location
        IS_SECONDARY = $true
    }
}

# 設定を保存
$configJson = $config | ConvertTo-Json -Depth 10
$configJson | Set-Content -Path $configPath -Encoding UTF8

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "   ✅ 設定が完了しました！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "保存先: $configPath" -ForegroundColor Cyan
Write-Host ""
Write-Host "--- 設定内容 ---" -ForegroundColor Yellow
Write-Host $configJson
Write-Host ""

if ($Type -eq "unit") {
    Write-Host "【次のステップ】" -ForegroundColor Yellow
    Write-Host "  1. 親機の管理画面で子機を登録"
    Write-Host "     → http://${ServerIP}:5000/admin/units/new"
    Write-Host "  2. 子機を起動"
    Write-Host "     → sudo ./scripts/quick_start_unit.sh"
} else {
    Write-Host "【次のステップ】" -ForegroundColor Yellow
    Write-Host "  1. 従親機を起動"
    Write-Host "     → .\venv-start.ps1 sub-parent"
}
Write-Host ""
