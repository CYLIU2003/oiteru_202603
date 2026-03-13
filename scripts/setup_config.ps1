<#
.SYNOPSIS
    OITERU Configuration Wizard (Windows)
.DESCRIPTION
    Setup config for sub-parent or unit interactively
.EXAMPLE
    .\setup_config.ps1
    .\setup_config.ps1 -Type unit -Name "3" -Location "Building7"
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
Write-Host "   OITERU Setup Wizard" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if (-not $Type) {
    Write-Host "What do you want to setup?" -ForegroundColor Yellow
    Write-Host "  1. Unit (Raspberry Pi dispenser)"
    Write-Host "  2. Sub-parent (Secondary server)"
    Write-Host ""
    $choice = Read-Host "Select [1/2]"
    $Type = if ($choice -eq "2") { "sub-parent" } else { "unit" }
}

Write-Host ""
Write-Host "Setting up: $Type" -ForegroundColor Green
Write-Host ""

if (-not $Name) {
    $defaultName = if ($Type -eq "unit") { "Unit1" } else { "SubParentA" }
    $Name = Read-Host "Enter name (e.g. Unit3, BuildingA) [$defaultName]"
    if ([string]::IsNullOrWhiteSpace($Name)) { $Name = $defaultName }
}

if (-not $Location) {
    $Location = Read-Host "Enter location (e.g. Building7-1F)"
    if ([string]::IsNullOrWhiteSpace($Location)) { $Location = "NotSet" }
}

if (-not $Password) {
    $Password = Read-Host "Enter password (empty for auto-generate)"
    if ([string]::IsNullOrWhiteSpace($Password)) {
        $Password = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 12 | ForEach-Object {[char]$_})
        Write-Host "  Auto-generated password: $Password" -ForegroundColor Magenta
    }
}

Write-Host ""
Write-Host "Parent server IP: $ServerIP" -ForegroundColor Cyan
$changeIP = Read-Host "Change it? [y/N]"
if ($changeIP -eq "y" -or $changeIP -eq "Y") {
    $ServerIP = Read-Host "Enter new IP address"
}

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
        MYSQL_PASSWORD = "change-this-mysql-password"
        SERVER_NAME = $Name
        SERVER_LOCATION = $Location
        IS_SECONDARY = $true
    }
}

$configJson = $config | ConvertTo-Json -Depth 10
$configJson | Set-Content -Path $configPath -Encoding UTF8

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "   Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Saved to: $configPath" -ForegroundColor Cyan
Write-Host ""
Write-Host "--- Configuration ---" -ForegroundColor Yellow
Write-Host $configJson
Write-Host ""

if ($Type -eq "unit") {
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "  1. Register unit at: http://${ServerIP}:5000/admin/units/new"
    Write-Host "  2. Start unit: scripts\start_unit.bat"
} else {
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "  1. Start sub-parent: scripts\start_sub_parent.bat"
}
Write-Host ""
