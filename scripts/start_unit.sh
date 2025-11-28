#!/bin/bash

# OITELUシステム 子機起動スクリプト
# 使い方: ./start_unit.sh

set -e

echo "============================================================"
echo "  OITERU子機クライアント - 起動スクリプト"
echo "============================================================"
echo ""
echo "起動方法を選択してください:"
echo ""
echo "  1. 通常起動（仮想環境自動作成）"
echo "  2. Docker起動（コンテナで実行）"
echo "  3. キャンセル"
echo ""
read -p "選択 [1-3]: " choice

case $choice in
    1)
        echo ""
        echo "通常起動モードを選択しました"
        echo "------------------------------------------------------------"
        echo ""
        echo "実行モードを選択してください:"
        echo "  1. CUIモード - 対話型設定"
        echo "  2. CUIモード - 自動起動（設定済み）"
        echo "  3. CUIモード - 親機自動探知"
        echo "  4. GUIモード"
        echo ""
        read -p "選択 [1-4]: " mode_choice
        
        case $mode_choice in
            1)
                echo ""
                echo "CUIモード（対話型）で起動します..."
                python unit_client.py --no-gui
                ;;
            2)
                echo ""
                echo "CUIモード（自動起動）で起動します..."
                python unit_client.py --no-gui --auto
                ;;
            3)
                echo ""
                echo "親機を自動探知して起動します..."
                python unit_client.py --no-gui --find-server
                ;;
            4)
                echo ""
                echo "GUIモードで起動します..."
                python unit_client.py
                ;;
            *)
                echo "✗ 無効な選択です"
                exit 1
                ;;
        esac
        ;;
        
    2)
        echo ""
        echo "Docker起動モードを選択しました"
        echo "------------------------------------------------------------"
        
        # Dockerがインストールされているか確認
        if ! command -v docker &> /dev/null; then
            echo "✗ Dockerがインストールされていません"
            echo "  以下のコマンドでインストールしてください:"
            echo "  curl -fsSL https://get.docker.com | sh"
            exit 1
        fi
        
        # docker-composeがインストールされているか確認
        if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
            echo "✗ docker-composeがインストールされていません"
            echo "  以下のコマンドでインストールしてください:"
            echo "  sudo apt-get install docker-compose"
            exit 1
        fi
        
        echo ""
        echo "Dockerコンテナの操作を選択してください:"
        echo "  1. 起動（バックグラウンド）"
        echo "  2. 起動（ログ表示）"
        echo "  3. 停止"
        echo "  4. 再起動"
        echo "  5. ログ確認"
        echo "  6. ビルドして起動"
        echo ""
        read -p "選択 [1-6]: " docker_choice
        
        case $docker_choice in
            1)
                echo ""
                echo "コンテナをバックグラウンドで起動します..."
                docker-compose -f docker-compose.unit.yml up -d
                echo "✓ 起動しました"
                echo "  ログ確認: docker-compose -f docker-compose.unit.yml logs -f"
                ;;
            2)
                echo ""
                echo "コンテナを起動します（Ctrl+C で停止）..."
                docker-compose -f docker-compose.unit.yml up
                ;;
            3)
                echo ""
                echo "コンテナを停止します..."
                docker-compose -f docker-compose.unit.yml down
                echo "✓ 停止しました"
                ;;
            4)
                echo ""
                echo "コンテナを再起動します..."
                docker-compose -f docker-compose.unit.yml restart
                echo "✓ 再起動しました"
                ;;
            5)
                echo ""
                echo "ログを表示します（Ctrl+C で終了）..."
                docker-compose -f docker-compose.unit.yml logs -f
                ;;
            6)
                echo ""
                echo "イメージをビルドして起動します..."
                docker-compose -f docker-compose.unit.yml up --build -d
                echo "✓ ビルドと起動が完了しました"
                echo "  ログ確認: docker-compose -f docker-compose.unit.yml logs -f"
                ;;
            *)
                echo "✗ 無効な選択です"
                exit 1
                ;;
        esac
        ;;
        
    3)
        echo ""
        echo "キャンセルしました"
        exit 0
        ;;
        
    *)
        echo "✗ 無効な選択です"
        exit 1
        ;;
esac
