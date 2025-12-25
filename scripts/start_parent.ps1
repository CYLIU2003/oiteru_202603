<#
.SYNOPSIS
    OITERUシステム 親機起動スクリプト (Windows PowerShell)

.DESCRIPTION
    仮想環境を自動検出・作成し、MySQL環境変数を設定してサーバーを起動します。

.PARAMETER Name
    サーバーの場所名（例: "本社", "倉庫A"）デフォルト: "本社"

.PARAMETER Location
    サーバーの住所/説明（例: "東京都千代田区"）デフォルト: ""

.PARAMETER Port
    サーバーのポート番号。デフォルト: 5000

.PARAMETER MysqlHost
    MySQLホスト。デフォルト: localhost

.PARAMETER MysqlPort
    MySQLポート。デフォルト: 3306

.PARAMETER MysqlDatabase
    MySQLデータベース名。デフォルト: oiteru

.PARAMETER MysqlUser
    MySQLユーザー名。デフォルト: oiteru_user

.PARAMETER MysqlPassword
    MySQLパスワード。デフォルト: oiteru_password_2025

.PARAMETER SkipDocker
    Dockerコンテナの起動をスキップ

.EXAMPLE
    .\start_parent.ps1
    デフォルト設定で起動

.EXAMPLE
    .\start_parent.ps1 -Name "倉庫A" -Location "大阪府堺市" -Port 5001
    カスタム設定で起動
#>

param(
    [string]$Name = "本社",
    [string]$Location = "",
    [int]$Port = 5000,
    [string]$MysqlHost = "localhost",
    [int]$MysqlPort = 3306,
    [string]$MysqlDatabase = "oiteru",
    [string]$MysqlUser = "oiteru_user",
    [string]$MysqlPassword = "oiteru_password_2025",
    [switch]$SkipDocker
)

$ErrorActionPreference = "Stop"

# 色付きメッセージ関数
function Write-Status {
    param([string]$Message, [string]$Color = "Cyan")
    Write-Host "[$((Get-Date).ToString('HH:mm:ss'))] " -NoNewline -ForegroundColor Gray
    Write-Host $Message -ForegroundColor $Color
}

function Write-Success {
    param([string]$Message)
    Write-Status "✓ $Message" -Color Green
}

function Write-Warning {
    param([string]$Message)
    Write-Status "⚠ $Message" -Color Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Status "✗ $Message" -Color Red
}

# ヘッダー表示
Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║         OITERUシステム 親機起動スクリプト                ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# スクリプトのディレクトリを取得
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir

Write-Status "プロジェクトディレクトリ: $ProjectDir"
Set-Location $ProjectDir

# ========================================
# 1. 仮想環境の検出・作成
# ========================================
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
Write-Status "ステップ 1: Python仮想環境のセットアップ"
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray

# ユーザーフォルダの仮想環境パス
$UserVenvPath = Join-Path $env:USERPROFILE ".venv_oiteru"
$VenvPaths = @($UserVenvPath, ".venv", "venv", "env", ".env")
$VenvFound = $null
$VenvPython = $null

foreach ($path in $VenvPaths) {
    if ($path -eq $UserVenvPath) {
        $activateScript = Join-Path $path "Scripts\Activate.ps1"
        $pythonExe = Join-Path $path "Scripts\python.exe"
    }
    else {
        $activateScript = Join-Path $ProjectDir "$path\Scripts\Activate.ps1"
        $pythonExe = Join-Path $ProjectDir "$path\Scripts\python.exe"
    }
    
    if (Test-Path $activateScript) {
        $VenvFound = $path
        $VenvPython = $pythonExe
        Write-Success "仮想環境を発見: $path"
        break
    }
}

if (-not $VenvFound) {
    Write-Warning "仮想環境が見つかりません。新規作成します..."
    
    # Pythonのバージョン確認
    try {
        $pythonVersion = & python --version 2>&1
        Write-Status "システムPython: $pythonVersion"
    }
    catch {
        Write-Error "Pythonが見つかりません。Pythonをインストールしてください。"
        exit 1
    }
    
    # ユーザーフォルダに仮想環境作成
    Write-Status "仮想環境を作成中: $UserVenvPath"
    & python -m venv $UserVenvPath
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "仮想環境の作成に失敗しました"
        exit 1
    }
    
    $VenvFound = $UserVenvPath
    $VenvPython = Join-Path $UserVenvPath "Scripts\python.exe"
    Write-Success "仮想環境を作成しました: $UserVenvPath"
}

# 仮想環境をアクティベート
if ($VenvFound -eq $UserVenvPath) {
    $ActivateScript = Join-Path $UserVenvPath "Scripts\Activate.ps1"
}
else {
    $ActivateScript = Join-Path $ProjectDir "$VenvFound\Scripts\Activate.ps1"
}
Write-Status "仮想環境をアクティベート中..."
& $ActivateScript

# pipの確認とアップグレード
Write-Status "pipをアップグレード中..."
& $VenvPython -m pip install --upgrade pip -q 2>&1 | Out-Null

# requirements.txtのインストール
$RequirementsFile = Join-Path $ProjectDir "requirements.txt"
$MysqlRequirementsFile = Join-Path $ProjectDir "requirements.mysql.txt"

if (Test-Path $RequirementsFile) {
    Write-Status "依存パッケージをインストール中 (requirements.txt)..."
    & $VenvPython -m pip install -r $RequirementsFile -q 2>&1 | Out-Null
    Write-Success "requirements.txt インストール完了"
}

if (Test-Path $MysqlRequirementsFile) {
    Write-Status "MySQL依存パッケージをインストール中 (requirements.mysql.txt)..."
    & $VenvPython -m pip install -r $MysqlRequirementsFile -q 2>&1 | Out-Null
    Write-Success "requirements.mysql.txt インストール完了"
}

# ========================================
# 2. Dockerコンテナの起動
# ========================================
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
Write-Status "ステップ 2: MySQLコンテナのセットアップ"
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray

if (-not $SkipDocker) {
    # Dockerの確認
    try {
        $dockerVersion = & docker --version 2>&1
        Write-Status "Docker: $dockerVersion"
    }
    catch {
        Write-Warning "Dockerが見つかりません。MySQLコンテナの起動をスキップします。"
        Write-Warning "外部MySQLサーバーを使用する場合は -MysqlHost パラメータを指定してください。"
        $SkipDocker = $true
    }
}

if (-not $SkipDocker) {
    # コンテナの状態確認
    $containerStatus = & docker ps -a --filter "name=oiteru_mysql" --format "{{.Status}}" 2>&1
    
    if ($containerStatus -match "Up") {
        Write-Success "MySQLコンテナは既に起動しています"
    }
    elseif ($containerStatus) {
        Write-Status "MySQLコンテナを起動中..."
        & docker start oiteru_mysql 2>&1 | Out-Null
        Start-Sleep -Seconds 3
        Write-Success "MySQLコンテナを起動しました"
    }
    else {
        Write-Status "MySQLコンテナを作成・起動中..."
        $composeFile = Join-Path $ProjectDir "docker-compose.mysql.yml"
        
        if (Test-Path $composeFile) {
            & docker-compose -f $composeFile up -d 2>&1 | Out-Null
            Write-Status "MySQLの初期化を待機中 (15秒)..."
            Start-Sleep -Seconds 15
            Write-Success "MySQLコンテナを作成・起動しました"
        }
        else {
            Write-Warning "docker-compose.mysql.yml が見つかりません"
            Write-Warning "手動でMySQLコンテナを起動してください"
        }
    }
}
else {
    Write-Status "Dockerコンテナの起動をスキップしました"
}

# ========================================
# 3. 環境変数の設定
# ========================================
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
Write-Status "ステップ 3: 環境変数の設定"
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray

$env:DB_TYPE = "mysql"
$env:MYSQL_HOST = $MysqlHost
$env:MYSQL_PORT = $MysqlPort
$env:MYSQL_DATABASE = $MysqlDatabase
$env:MYSQL_USER = $MysqlUser
$env:MYSQL_PASSWORD = $MysqlPassword
$env:SERVER_NAME = $Name
$env:SERVER_LOCATION = $Location

Write-Status "DB_TYPE       = mysql"
Write-Status "MYSQL_HOST    = $MysqlHost"
Write-Status "MYSQL_PORT    = $MysqlPort"
Write-Status "MYSQL_DATABASE= $MysqlDatabase"
Write-Status "MYSQL_USER    = $MysqlUser"
Write-Status "SERVER_NAME   = $Name"
Write-Status "SERVER_LOCATION= $Location"
Write-Success "環境変数を設定しました"

# ========================================
# 4. サーバー起動
# ========================================
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
Write-Status "ステップ 4: サーバー起動"
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray

# server.py または app.py を探す
$ServerScript = $null
if (Test-Path (Join-Path $ProjectDir "server.py")) {
    $ServerScript = "server.py"
}
elseif (Test-Path (Join-Path $ProjectDir "app.py")) {
    $ServerScript = "app.py"
}
else {
    Write-Error "server.py または app.py が見つかりません"
    exit 1
}

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║                    サーバー起動情報                      ║" -ForegroundColor Green
Write-Host "╠══════════════════════════════════════════════════════════╣" -ForegroundColor Green
Write-Host "║  サーバー名   : $($Name.PadRight(38))║" -ForegroundColor Green
if ($Location) {
    Write-Host "║  場所         : $($Location.PadRight(38))║" -ForegroundColor Green
}
Write-Host "║  ポート       : $($Port.ToString().PadRight(38))║" -ForegroundColor Green
Write-Host "║  アクセスURL  : http://localhost:$Port$(' ' * (25 - $Port.ToString().Length))║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Status "サーバーを起動中... (Ctrl+C で停止)"
Write-Host ""

# サーバー起動
& $VenvPython $ServerScript --port $Port
