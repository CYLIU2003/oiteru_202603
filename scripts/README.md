# Scripts ディレクトリ

このディレクトリには、OITERU のセットアップ、起動、診断に使うスクリプトが含まれています。

現在の標準運用は **Linux 系 OS + ローカル MySQL** で、親機は systemd、子機は tmux で起動します。親機の運用手順は [../docs/runbook.md](../docs/runbook.md) を見てください。新しく参加した人は、まず「推奨スクリプト」だけ見れば十分です。

## 推奨スクリプト

| ファイル名 | 説明 | 対象環境 |
|---|---|---|
| `install_parent_service.sh` | 本番親機を systemd サービスとして導入・更新する（`sudo` で実行、`--dry-run` で内容確認） | Linux（本番親機） |
| `tmux_oiteru.sh` | 子機・従親機を tmux で start/stop/attach/status/logs する。親機は保守時の手動起動だけに使う | Linux |
| `setup_local_mysql.sh` | `.env` を読み、ローカル MySQL の DB とユーザーを作成する | Linux |
| `setup_unit_environment.sh` | 子機環境の自動セットアップ | Raspberry Pi |
| `SETUP_UNIT.md` | 子機セットアップの詳細ガイド | 全環境 |

## よく使うコマンド

親機（初回・更新時）:

```bash
scripts/setup_local_mysql.sh
sudo scripts/install_parent_service.sh
```

子機:

```bash
scripts/tmux_oiteru.sh start unit
scripts/tmux_oiteru.sh attach unit
```

状態確認:

```bash
systemctl is-active oiteru-parent
scripts/tmux_oiteru.sh status unit
systemctl status mysql
```

停止:

```bash
sudo systemctl stop oiteru-parent
scripts/tmux_oiteru.sh stop unit
```

## 設定・診断

| ファイル名 | 説明 | 対象環境 |
|---|---|---|
| `setup_config.sh` | 設定ファイルの対話的作成 | Linux |
| `setup_config.ps1` | 設定ファイルの対話的作成 | Windows |
| `open_mysql_port_linux.sh` | MySQL 外部接続設定 | Linux |
| `open_mysql_port_windows.ps1` | MySQL 外部接続設定 | Windows |
| `check_mysql_port.ps1` | MySQL ポート確認 | Windows |
| `init_card_reader.sh` | NFC カードリーダーの初期化 | Linux |
| `auto_attach_card_reader.sh` | カードリーダーの自動接続 | Linux |

## legacy / 補助スクリプト

次のスクリプトは残していますが、標準手順では優先しません。古い資料や検証用の経路として扱ってください。

| ファイル名 | 理由 |
|---|---|
| `launcher.sh`, `launcher.ps1`, `launcher.bat` | Docker/GUI/複数モードを含む古い統合ランチャー |
| `launcher_gui.py`, `launcher_cui.py` | 旧ランチャー本体 |
| `quick_start_parent.sh`, `quick_start_parent.ps1` | Docker 前提の分岐が残る |
| `start_oiteru.sh`, `start_oiteru_mysql.sh`, `start_oiteru.ps1` | Docker 前提の起動処理が残る |
| `setup_multi_server.sh` | Docker Compose 前提のマルチサーバー補助 |
| `test_nfc_in_container.sh` | コンテナ内 NFC 検証用 |

## 注意事項

- `.env`, `config.json`, `logs/`, DB ファイルは Git に含めないでください。
- Linux/macOS で実行権限がない場合は `chmod +x scripts/<script>` を実行してください。
- Windows 用スクリプト（`oiteru_restart_auto.ps1` を含む）は開発用 PC 向けです。本番親機では使いません。
- Docker 関連スクリプトは当面の標準ではありません。

## 関連ドキュメント

| ファイル | 内容 |
|---|---|
| `../README.md` | 全体像 |
| `../docs/onboarding.md` | 新規参加者向け |
| `../docs/quick_start.md` | 標準の起動手順 |
| `../docs/runbook.md` | 親機の起動・停止・復旧（はじめての人向け） |
| `../docs/operations.md` | 運用・障害対応 |
| `../config_templates/README.md` | 設定ファイルの詳細 |

最終更新: 2026-06-04
