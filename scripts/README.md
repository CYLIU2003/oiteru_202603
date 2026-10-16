# 起動・保守コマンドの一覧

普段の当番は [操作ガイド](../QUICK_START.md#daily) を使います。
親機の状態確認が必要な場合は [親機の運用ガイド](../docs/runbook.md) へ進んでください。

| ファイル | 実行する場所・用途 |
| --- | --- |
| `parent.sh` | 親機。`status` で状態確認、`logs` でログ確認、`restart` で再起動、`install` で初回登録 |
| `setup_local_mysql.sh` | 親機。初回にローカル MySQL の DB とユーザーを作成 |
| `backup_mysql.sh` / `restore_mysql.sh` | 親機。`bash scripts/backup_mysql.sh` などとして実行。鍵の渡し方は操作ガイドを参照 |
| `init_card_reader.sh` | 親機。systemd が NFC リーダーを初期化するときに使う |
| `setup_unit_environment.sh` | 子機。初回のソフトウェア準備 |
| `provision_unit.sh` | 子機。`sudo bash scripts/provision_unit.sh` で秘密ファイルを作成 |
| `tmux_oiteru.sh` | 子機の起動・停止。親機では保守で手動起動するときだけ使う |

設定の見本と役割は [設定ファイルの説明](../docs/configuration.md) を参照してください。
旧 Docker・launcher・設定ウィザード・特定の Windows PC 用自動起動スクリプトは削除しました。
Windows で NFC を検証する場合は [WSL の手順](../docs/card_reader_windows.md) を使います。

`.env`、`config.json`、秘密ファイル、ログ、DB、バックアップは Git に含めません。
