# Scripts ディレクトリ

このディレクトリには、OITERU のセットアップ、tmux 起動、診断に使うスクリプトが含まれています。

現在の標準運用は **Linux 系 OS + tmux + ローカル MySQL** です。新しく参加した人は、まず「推奨スクリプト」だけ見れば十分です。

## 推奨スクリプト

| ファイル名 | 説明 | 対象環境 |
|---|---|---|
| `tmux_oiteru.sh` | 親機・子機・従親機を tmux で start/stop/attach/status/logs する | Linux |
| `setup_local_mysql.sh` | `.env` を読み、ローカル MySQL の DB とユーザーを作成する | Linux |
| `setup_unit_environment.sh` | 子機環境の自動セットアップ | Raspberry Pi |
| `SETUP_UNIT.md` | 子機セットアップの詳細ガイド | 全環境 |

## よく使うコマンド

親機:

```bash
scripts/setup_local_mysql.sh
scripts/tmux_oiteru.sh start parent
scripts/tmux_oiteru.sh attach parent
```

子機:

```bash
scripts/tmux_oiteru.sh start unit
scripts/tmux_oiteru.sh attach unit
```

状態確認:

```bash
scripts/tmux_oiteru.sh status
tmux ls
systemctl status mysql
```

停止:

```bash
scripts/tmux_oiteru.sh stop parent
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
- Windows 用スクリプトは開発・補助用です。学内実証の標準手順は Linux/tmux です。
- Docker 関連スクリプトは当面の標準ではありません。

## 関連ドキュメント

| ファイル | 内容 |
|---|---|
| `../README.md` | 全体像 |
| `../docs/onboarding.md` | 新規参加者向け |
| `../取説書/QUICKSTART.md` | 詳細な起動手順 |
| `../docs/operations.md` | 運用・障害対応 |
| `../config_templates/README.md` | 設定ファイルの詳細 |

最終更新: 2026-06-04
