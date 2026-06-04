# OITERU 運用手順

この文書は、OITERU を学内実証で引き継ぐための運用手順です。開発手順ではなく、日常運用と障害時対応を対象にします。

## 標準構成

| 項目 | 標準 |
|---|---|
| 親機 | `db_server.py` |
| DB | ローカル MySQL 8 (InnoDB) |
| 子機 | Raspberry Pi / Linux + `unit.py` |
| 起動 | `tmux` |
| 起動補助 | `scripts/tmux_oiteru.sh` |

Docker は当面の標準運用では使いません。MySQL は OS の `mysql` サービスとして起動します。

## 日常運用

- 補充前に管理画面で対象子機の在庫と最終接続時刻を確認する
- 補充後は `初期在庫数` と `現在の残り在庫` を更新する
- 子機設定を変えた場合は、設定送信後に heartbeat 同期完了を確認する
- 管理画面の認証情報は `.env` 管理とし、共有チャットに平文で貼らない
- 運用ログやカード UID を画面共有・資料貼り付けに使わない

## 起動・停止

親機:

```bash
cd ~/Desktop/oiteru_202603
scripts/tmux_oiteru.sh start parent
scripts/tmux_oiteru.sh attach parent
```

子機:

```bash
cd ~/Desktop/oiteru_202603
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

## 障害時の一次対応

### 管理画面に入れない

- `.env` の `OITERU_ADMIN_PASSWORD` が正しいか確認する
- 親機再起動後に `FLASK_SECRET_KEY` が変わっていないか確認する
- ログイン試行上限に達した場合は、待機後に再試行する
- 親機が起動しているか `scripts/tmux_oiteru.sh status parent` で確認する

### 子機がオフライン

- 子機本体の電源、LAN/Tailscale、NFC リーダー接続を確認する
- 管理画面で `最終接続` を確認する
- 子機側で `scripts/tmux_oiteru.sh status unit` を確認する
- `config.json` の `SERVER_URL` が親機 IP を指しているか確認する
- 子機から `curl http://<親機IP>:5000` を実行する

### 排出されない

- 子機在庫が 0 でないか確認する
- センサー詰まり、モーター配線、電源を確認する
- 子機ログと heartbeat の直近時刻を確認する
- 同一カードの短時間連打でないか確認する
- 物理排出済みだが DB 未反映の疑いがある場合は、時刻、子機名、カード操作の有無をメモしてから調査する

### DB 接続異常

- `systemctl status mysql` で MySQL サービス状態を確認する
- `.env` の `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE` を確認する
- 親機から次を実行する

```bash
mysql -u oiteru_user -p oiteru -e "SELECT 1;"
```

- 初回構築直後なら `scripts/setup_local_mysql.sh` を再確認する

## プライバシー運用

- `.env`, `config.json`, `logs/`, `*.log`, `*.sqlite3`, バックアップファイルは Git に含めない
- 利用履歴を外部共有する場合は、個票ではなく集計値を使う
- ユーザー名、カード UID、トークン、パスワードをログや資料に平文で出さない
- スクリーンショットを共有する場合は、カード ID と認証情報を隠す

## 引き継ぎ時チェックリスト

- `.env.example` を元に新しい `.env` を作成した
- `config.example.json` を元に各子機の `config.json` を作成した
- `scripts/setup_local_mysql.sh` でローカル MySQL を準備した
- `scripts/tmux_oiteru.sh start parent` で親機を起動した
- 管理画面ログインを確認した
- 子機 heartbeat を確認した
- 補充手順と障害時一次対応を担当者へ説明した

最終更新: 2026-06-04
