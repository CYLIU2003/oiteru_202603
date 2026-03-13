#!/bin/bash
#
# OITERU 設定ウィザード（Linux/macOS用）
# 従親機・子機の設定を対話形式で簡単に作成します
#
# 使い方:
#   ./setup_config.sh                    # 対話モード
#   ./setup_config.sh unit 3号機 5号館   # ワンライナー

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_PATH="$PROJECT_DIR/config.json"

# デフォルト値
DEFAULT_SERVER_IP="100.114.99.67"
SERVER_IP="$DEFAULT_SERVER_IP"

# 色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

echo ""
echo -e "${CYAN}========================================"
echo "   🍬 OITERU 設定ウィザード"
echo -e "========================================${NC}"
echo ""

# 引数チェック
if [ -n "$1" ]; then
    TYPE="$1"
    NAME="${2:-新規子機}"
    LOCATION="${3:-未設定}"
    PASSWORD="${4:-$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 12 | head -n 1)}"
else
    # 対話モード
    echo -e "${YELLOW}何を設定しますか？${NC}"
    echo "  1. 子機（生理用品を排出する端末）"
    echo "  2. 従親機（サブサーバー）"
    echo ""
    read -p "選択 [1/2]: " choice
    
    if [ "$choice" = "2" ]; then
        TYPE="sub-parent"
    else
        TYPE="unit"
    fi
    
    echo ""
    echo -e "${GREEN}【${TYPE} の設定を開始します】${NC}"
    echo ""
    
    # 名前入力
    if [ "$TYPE" = "unit" ]; then
        DEFAULT_NAME="新規子機"
    else
        DEFAULT_NAME="従親機A"
    fi
    read -p "名前を入力 (例: 3号機、A棟子機) [$DEFAULT_NAME]: " NAME
    NAME="${NAME:-$DEFAULT_NAME}"
    
    # 設置場所
    read -p "設置場所を入力 (例: 7号館1階): " LOCATION
    LOCATION="${LOCATION:-未設定}"
    
    # パスワード
    read -p "パスワードを入力 (空で自動生成): " PASSWORD
    if [ -z "$PASSWORD" ]; then
        PASSWORD=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 12 | head -n 1)
        echo -e "  → 自動生成されたパスワード: ${MAGENTA}$PASSWORD${NC}"
    fi
    
    # サーバーIP確認
    echo ""
    echo -e "${CYAN}親機のIPアドレス: $SERVER_IP${NC}"
    read -p "変更しますか？ [y/N]: " change_ip
    if [ "$change_ip" = "y" ] || [ "$change_ip" = "Y" ]; then
        read -p "新しいIPアドレスを入力: " SERVER_IP
    fi
fi

# 設定ファイル生成
if [ "$TYPE" = "unit" ]; then
    cat > "$CONFIG_PATH" << EOF
{
    "SERVER_URL": "http://${SERVER_IP}:5000",
    "UNIT_NAME": "$NAME",
    "UNIT_PASSWORD": "$PASSWORD",
    "UNIT_LOCATION": "$LOCATION",
    "IS_SECONDARY": false,
    "MOTOR_TYPE": "SERVO",
    "CONTROL_METHOD": "RASPI_DIRECT",
    "USE_SENSOR": true,
    "GREEN_LED_PIN": 17,
    "RED_LED_PIN": 27,
    "SENSOR_PIN": 22,
    "ARDUINO_PORT": "/dev/ttyACM0",
    "MOTOR_SPEED": 100,
    "MOTOR_DURATION": 2.0,
    "MOTOR_REVERSE": false
}
EOF
else
    cat > "$CONFIG_PATH" << EOF
{
    "DB_TYPE": "mysql",
    "MYSQL_HOST": "$SERVER_IP",
    "MYSQL_PORT": 3306,
    "MYSQL_DATABASE": "oiteru",
    "MYSQL_USER": "oiteru_user",
    "MYSQL_PASSWORD": "oiteru_password_2025",
    "SERVER_NAME": "$NAME",
    "SERVER_LOCATION": "$LOCATION",
    "IS_SECONDARY": true
}
EOF
fi

echo ""
echo -e "${GREEN}========================================"
echo "   ✅ 設定が完了しました！"
echo -e "========================================${NC}"
echo ""
echo -e "${CYAN}保存先: $CONFIG_PATH${NC}"
echo ""
echo -e "${YELLOW}--- 設定内容 ---${NC}"
cat "$CONFIG_PATH"
echo ""

if [ "$TYPE" = "unit" ]; then
    echo -e "${YELLOW}【次のステップ】${NC}"
    echo "  1. 親機の管理画面で子機を登録"
    echo "     → http://${SERVER_IP}:5000/admin/units/new"
    echo "  2. 子機を起動"
    echo "     → sudo ./scripts/quick_start_unit.sh"
else
    echo -e "${YELLOW}【次のステップ】${NC}"
    echo "  1. 従親機を起動"
    echo "     → ./venv-start.sh sub-parent"
fi
echo ""
