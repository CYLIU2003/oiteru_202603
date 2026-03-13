<#
.SYNOPSIS
OITERU 仮想環境(venv)用 起動スクリプト (Windows)

.DESCRIPTION
Dockerを使わずに、ローカルのPython仮想環境(.venv)を使用して
親機・従親機・子機を起動するためのヘルパースクリプトです。

.PARAMETER Mode
起動モードを指定します。
- parent-sqlite : 親機 (SQLite版)
- parent-mysql  : 親機 (MySQL版 - localhost:3306に接続)
- sub-parent    : 従親機 (MySQL版 - localhost:3306に接続)
- unit          : 子機 (unit.py)

.EXAMPLE
.\venv-start.ps1 parent-sqlite
#>

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("parent-sqlite", "parent-mysql", "sub-parent", "unit")]
    [string]$Mode
)

# スクリプトのあるディレクトリへ移動
Set-Location $PSScriptRoot
$EnvFile = Join-Path $PSScriptRoot ".env"
$EnvExampleFile = Join-Path $PSScriptRoot ".env.example"

# 仮想環境のPythonパス
$PythonPath = ".\.venv\Scripts\python.exe"

if (-not (Test-Path $PythonPath)) {
    Write-Error "仮想環境が見つかりません: $PythonPath"
    Write-Host "先に 'python -m venv .venv' と 'pip install -r requirements.txt' を実行してください。"
    exit 1
}

Write-Host "起動モード: $Mode"

switch ($Mode) {
    "parent-sqlite" {
        Write-Host "親機 (SQLite) を起動します..."
        $env:DB_TYPE = "sqlite"
        & $PythonPath server.py
    }
    "parent-mysql" {
        Write-Host "親機 (MySQL) を起動します..."
        Write-Host "※ 事前にMySQLが localhost:3306 で起動している必要があります。"

        if (-not (Test-Path $EnvFile)) {
            Write-Error ".env が見つかりません: $EnvFile"
            Write-Host "$EnvExampleFile をコピーし、必須値を設定してください。"
            exit 1
        }

        & $PythonPath db_server.py
    }
    "sub-parent" {
        Write-Host "従親機 (MySQL接続) を起動します..."
        Write-Host "※ 接続先は localhost:3306 (デフォルト) です。"

        if (-not (Test-Path $EnvFile)) {
            Write-Error ".env が見つかりません: $EnvFile"
            Write-Host "$EnvExampleFile をコピーし、必須値を設定してください。"
            exit 1
        }

        $env:DB_TYPE = "mysql"
        if (-not $env:MYSQL_HOST) { $env:MYSQL_HOST = "localhost" }
        if (-not $env:SERVER_NAME) { $env:SERVER_NAME = "OITERU従親機" }
        
        & $PythonPath server.py
    }
    "unit" {
        Write-Host "子機クライアントを起動します..."
        Write-Host ""
        Write-Host "========================================="
        Write-Host "  子機: 親機・従親機からの設定同期対応"
        Write-Host "  - GUIモード: --gui オプション"
        Write-Host "  - CUIモード: デフォルト"
        Write-Host "  - リモート設定変更が自動反映されます"
        Write-Host "========================================="
        Write-Host ""
        & $PythonPath unit.py @args
    }
}
