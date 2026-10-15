# scripts/

OITERU を動かすためのスクリプトです。はじめての人が使うのは `parent.sh` だけです。
親機の運用手順は [../docs/runbook.md](../docs/runbook.md) を見てください。

## 親機（本番 Linux）

| ファイル | 使う場面 |
|---|---|
| `parent.sh` | 親機を見る・直す。`status` / `restart` / `logs` / `install` |
| `setup_local_mysql.sh` | 初回だけ。`.env` を読んで MySQL の DB とユーザーを作る |
| `backup_mysql.sh`, `restore_mysql.sh` | DB の暗号化バックアップと復元（[../docs/operations.md](../docs/operations.md)） |
| `init_card_reader.sh` | 親機の NFC リーダー初期化。systemd が自動で実行する |

## 子機（Raspberry Pi）・従親機

| ファイル | 使う場面 |
|---|---|
| `setup_unit_environment.sh` | 子機の初回セットアップ |
| `provision_unit.sh` | 子機の設定ファイルと秘密情報を作る |
| `SETUP_UNIT.md` | 子機セットアップの詳しい説明 |
| `tmux_oiteru.sh` | 子機・従親機を tmux で起動・停止する。親機は保守で手動起動するときだけ |
| `setup_config.sh`, `setup_config.ps1` | `config.json` を対話形式で作る（[../config_templates/README.md](../config_templates/README.md)） |

## 開発用 PC（Windows）

| ファイル | 使う場面 |
|---|---|
| `windows/oiteru_restart_auto.ps1` | 開発用 PC の再起動後に、MySQL と親機を自動で起動する |
| `windows/wsl_nfc_setup.ps1` | WSL2 で NFC リーダーを使えるようにする |

本番の親機では、Windows 用スクリプトは使いません。

## 使わなくなったスクリプト

Docker 版、launcher 版、`start_*` 版などの古い起動スクリプトは [../legacy/](../legacy/) に移しました。
標準の手順では使いません。

## 注意

- `.env`, `config.json`, `logs/`, DB ファイルは Git に含めないでください。
- 実行権限がない場合は `chmod +x scripts/<ファイル名>` を実行してください。
