#!/bin/bash
#
# OITERUシステム 従親機起動スクリプト (Linux/Mac Bash)
#
# 仮想環境を自動検出・作成し、リモートMySQLに接続してサーバーを起動します。
#
# 使用方法:
#   ./start_sub_parent.sh --host 192.168.1.100
#   ./start_sub_parent.sh --host 192.168.1.100 --name "支店A" --location "大阪市北区"
#   ./start_sub_parent.sh --host 192.168.1.100 --port 5001
#
# パラメータ:
#   --host        親機のIPアドレス（必須）
#   --name        サーバーの場所名（デフォルト: "支店"）
#   --location    サーバーの住所/説明（デフォルト: ""）
#   --port        サーバーのポート番号（デフォルト: 5000）
#   --mysql-port  MySQLポート（デフォルト: 3306）
#   --mysql-db    MySQLデータベース名（デフォルト: oiteru）
#   --mysql-user  MySQLユーザー名（デフォルト: oiteru_user）
#   --mysql-pass  MySQLパスワード（未指定時は .env の MYSQL_PASSWORD を使用）
#   --help        ヘルプを表示
#

set -e

# ========================================
# カラー定義
# ========================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;90m'
NC='\033[0m' # No Color

# メッセージ関数
log_status() {
    echo -e "${GRAY}[$(date '+%H:%M:%S')]${NC} ${CYAN}$1${NC}"
}

log_success() {
    echo -e "${GRAY}[$(date '+%H:%M:%S')]${NC} ${GREEN}✓ $1${NC}"
}

log_warning() {
    echo -e "${GRAY}[$(date '+%H:%M:%S')]${NC} ${YELLOW}⚠ $1${NC}"
}

log_error() {
    echo -e "${GRAY}[$(date '+%H:%M:%S')]${NC} ${RED}✗ $1${NC}"
}

# ========================================
# デフォルト値
# ========================================
MYSQL_HOST=""
SERVER_NAME="支店"
SERVER_LOCATION=""
SERVER_PORT=5000
MYSQL_PORT=3306
MYSQL_DATABASE="oiteru"
MYSQL_USER="oiteru_user"
MYSQL_PASSWORD=""

# ========================================
# ヘルプ表示
# ========================================
show_help() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║      OITERUシステム 従親機起動スクリプト                 ║"
    echo "╚══════════════════════════════════════════════════════════╝"
    echo ""
    echo "使用方法:"
    echo "  $0 --host <親機IP> [オプション]"
    echo ""
    echo "必須パラメータ:"
    echo "  --host          親機のIPアドレス"
    echo ""
    echo "オプション:"
    echo "  --name          サーバーの場所名（デフォルト: 支店）"
    echo "  --location      サーバーの住所/説明"
    echo "  --port          サーバーのポート番号（デフォルト: 5000）"
    echo "  --mysql-port    MySQLポート（デフォルト: 3306）"
    echo "  --mysql-db      MySQLデータベース名（デフォルト: oiteru）"
    echo "  --mysql-user    MySQLユーザー名（デフォルト: oiteru_user）"
    echo "  --mysql-pass    MySQLパスワード"
    echo "  --help          このヘルプを表示"
    echo ""
    echo "例:"
    echo "  $0 --host 192.168.1.100"
    echo "  $0 --host 192.168.1.100 --name \"大阪支店\" --location \"大阪市北区\""
    echo "  $0 --host 192.168.1.100 --port 5001"
    echo ""
    exit 0
}

# ========================================
# 引数解析
# ========================================
while [[ $# -gt 0 ]]; do
    case $1 in
        --host)
            MYSQL_HOST="$2"
            shift 2
            ;;
        --name)
            SERVER_NAME="$2"
            shift 2
            ;;
        --location)
            SERVER_LOCATION="$2"
            shift 2
            ;;
        --port)
            SERVER_PORT="$2"
            shift 2
            ;;
        --mysql-port)
            MYSQL_PORT="$2"
            shift 2
            ;;
        --mysql-db)
            MYSQL_DATABASE="$2"
            shift 2
            ;;
        --mysql-user)
            MYSQL_USER="$2"
            shift 2
            ;;
        --mysql-pass)
            MYSQL_PASSWORD="$2"
            shift 2
            ;;
        --help|-h)
            show_help
            ;;
        *)
            log_error "不明なオプション: $1"
            echo "ヘルプを表示するには: $0 --help"
            exit 1
            ;;
    esac
done

# ========================================
# ヘッダー表示
# ========================================
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║       OITERUシステム 従親機起動スクリプト                ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# 必須パラメータチェック
if [ -z "$MYSQL_HOST" ]; then
    log_error "親機のIPアドレスが指定されていません"
    echo ""
    echo "使用方法: $0 --host <親機IP>"
    echo "ヘルプ:   $0 --help"
    echo ""
    exit 1
fi

# スクリプトのディレクトリを取得
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_DIR/.env"
ENV_EXAMPLE_FILE="$PROJECT_DIR/.env.example"

log_status "プロジェクトディレクトリ: $PROJECT_DIR"
cd "$PROJECT_DIR"

if [ ! -f "$ENV_FILE" ]; then
    log_error ".env が見つかりません: $ENV_FILE"
    echo "$ENV_EXAMPLE_FILE をコピーし、必須値を設定してください。"
    exit 1
fi

# ========================================
# ステップ 1: 仮想環境のセットアップ
# ========================================
echo ""
echo -e "${GRAY}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
log_status "ステップ 1: Python仮想環境のセットアップ"
echo -e "${GRAY}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# ホームディレクトリの仮想環境を優先
USER_VENV="$HOME/.venv_oiteru"
VENV_PATHS=("$USER_VENV" "$PROJECT_DIR/.venv" "$PROJECT_DIR/venv" "$PROJECT_DIR/env" "$PROJECT_DIR/.env")
VENV_FOUND=""
VENV_PYTHON=""

for path in "${VENV_PATHS[@]}"; do
    activate_script="$path/bin/activate"
    python_exe="$path/bin/python"
    
    if [ -f "$activate_script" ]; then
        VENV_FOUND="$path"
        VENV_PYTHON="$python_exe"
        log_success "仮想環境を発見: $path"
        break
    fi
done

if [ -z "$VENV_FOUND" ]; then
    log_warning "仮想環境が見つかりません。新規作成します..."
    
    # Pythonのバージョン確認
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        log_error "Pythonが見つかりません。Pythonをインストールしてください。"
        exit 1
    fi
    
    python_version=$($PYTHON_CMD --version 2>&1)
    log_status "システムPython: $python_version"
    
    # ホームディレクトリに仮想環境作成
    log_status "仮想環境を作成中: $USER_VENV"
    $PYTHON_CMD -m venv "$USER_VENV"
    
    if [ $? -ne 0 ]; then
        log_error "仮想環境の作成に失敗しました"
        exit 1
    fi
    
    VENV_FOUND="$USER_VENV"
    VENV_PYTHON="$USER_VENV/bin/python"
    log_success "仮想環境を作成しました: $USER_VENV"
fi

# 仮想環境をアクティベート
ACTIVATE_SCRIPT="$VENV_FOUND/bin/activate"
log_status "仮想環境をアクティベート中..."
source "$ACTIVATE_SCRIPT"

# pipのアップグレード
log_status "pipをアップグレード中..."
"$VENV_PYTHON" -m pip install --upgrade pip -q 2>/dev/null

# requirements.txtのインストール
if [ -f "$PROJECT_DIR/requirements.txt" ]; then
    log_status "依存パッケージをインストール中 (requirements.txt)..."
    "$VENV_PYTHON" -m pip install -r "$PROJECT_DIR/requirements.txt" -q 2>/dev/null
    log_success "requirements.txt インストール完了"
fi

if [ -f "$PROJECT_DIR/requirements.mysql.txt" ]; then
    log_status "MySQL依存パッケージをインストール中 (requirements.mysql.txt)..."
    "$VENV_PYTHON" -m pip install -r "$PROJECT_DIR/requirements.mysql.txt" -q 2>/dev/null
    log_success "requirements.mysql.txt インストール完了"
fi

# ========================================
# ステップ 2: 親機への接続テスト
# ========================================
echo ""
echo -e "${GRAY}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
log_status "ステップ 2: 親機への接続テスト"
echo -e "${GRAY}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

log_status "親機 ($MYSQL_HOST:$MYSQL_PORT) への接続をテスト中..."

# ncコマンドで接続テスト
if command -v nc &> /dev/null; then
    if nc -z -w5 "$MYSQL_HOST" "$MYSQL_PORT" 2>/dev/null; then
        log_success "親機MySQLへの接続に成功しました"
    else
        log_error "親機MySQLへの接続に失敗しました"
        log_warning "以下を確認してください:"
        echo "  1. 親機のIPアドレス ($MYSQL_HOST) が正しいか"
        echo "  2. 親機でMySQLコンテナが起動しているか"
        echo "  3. ファイアウォールでポート $MYSQL_PORT が開いているか"
        echo "  4. Tailscale等のVPNが接続されているか"
        exit 1
    fi
else
    log_warning "ncコマンドがありません。接続テストをスキップします"
fi

# ========================================
# ステップ 3: 環境変数の設定
# ========================================
echo ""
echo -e "${GRAY}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
log_status "ステップ 3: 環境変数の設定"
echo -e "${GRAY}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

export DB_TYPE="mysql"
export MYSQL_HOST="$MYSQL_HOST"
export MYSQL_PORT="$MYSQL_PORT"
export MYSQL_DATABASE="$MYSQL_DATABASE"
export MYSQL_USER="$MYSQL_USER"
if [ -n "$MYSQL_PASSWORD" ]; then
    export MYSQL_PASSWORD="$MYSQL_PASSWORD"
fi
export SERVER_NAME="$SERVER_NAME"
export SERVER_LOCATION="$SERVER_LOCATION"

log_status "DB_TYPE       = mysql"
log_status "MYSQL_HOST    = $MYSQL_HOST"
log_status "MYSQL_PORT    = $MYSQL_PORT"
log_status "MYSQL_DATABASE= $MYSQL_DATABASE"
log_status "MYSQL_USER    = $MYSQL_USER"
log_status "SERVER_NAME   = $SERVER_NAME"
log_status "SERVER_LOCATION= $SERVER_LOCATION"
log_success "環境変数を設定しました"

# ========================================
# ステップ 4: サーバー起動
# ========================================
echo ""
echo -e "${GRAY}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
log_status "ステップ 4: サーバー起動"
echo -e "${GRAY}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# server.py または app.py を探す
SERVER_SCRIPT=""
if [ -f "$PROJECT_DIR/server.py" ]; then
    SERVER_SCRIPT="server.py"
elif [ -f "$PROJECT_DIR/app.py" ]; then
    SERVER_SCRIPT="app.py"
else
    log_error "server.py または app.py が見つかりません"
    exit 1
fi

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    サーバー起動情報                      ║${NC}"
echo -e "${GREEN}╠══════════════════════════════════════════════════════════╣${NC}"
printf "${GREEN}║  サーバー名   : %-38s║${NC}\n" "$SERVER_NAME"
if [ -n "$SERVER_LOCATION" ]; then
    printf "${GREEN}║  場所         : %-38s║${NC}\n" "$SERVER_LOCATION"
fi
printf "${GREEN}║  ポート       : %-38s║${NC}\n" "$SERVER_PORT"
printf "${GREEN}║  親機MySQL    : %-38s║${NC}\n" "$MYSQL_HOST:$MYSQL_PORT"
printf "${GREEN}║  アクセスURL  : http://localhost:%-22s║${NC}\n" "$SERVER_PORT"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
log_status "サーバーを起動中... (Ctrl+C で停止)"
echo ""

# サーバー起動
"$VENV_PYTHON" "$SERVER_SCRIPT" --port "$SERVER_PORT"
