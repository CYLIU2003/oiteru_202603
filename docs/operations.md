# OITERU Operations

## 目的
この文書は、OITERU を学内実証で引き継ぐための運用手順をまとめたものです。
開発手順ではなく、日常運用と障害時対応を対象にします。

## 標準構成
- 親機: `db_server.py`
- DB: MySQL 8 (InnoDB)
- 子機: Raspberry Pi + `unit.py`
- 起動基準: `docker/docker-compose.mysql.yml`

## 日常運用
- 補充前に管理画面で対象子機の在庫と最終接続時刻を確認する
- 補充後は `初期在庫数` と `現在の残り在庫` を更新する
- 子機設定を変えた場合は、設定送信後に heartbeat 同期完了を確認する
- 管理画面の認証情報は `.env` 管理とし、共有チャットに平文で貼らない

## 障害時の一次対応

### 管理画面に入れない
- `.env` の `OITERU_ADMIN_PASSWORD` が正しいか確認する
- 親機再起動後に secret が変わっていないか確認する
- ログイン試行上限に達した場合は、待機後に再試行する

### 子機がオフライン
- 子機本体の電源、LAN/Tailscale、NFC リーダー接続を確認する
- 管理画面で `最終接続` を確認する
- Raspberry Pi 上で `./venv-start.sh unit` を再起動する

### 排出されない
- 子機在庫が 0 でないか確認する
- センサー詰まりとモーター配線を確認する
- 子機ログと heartbeat の直近時刻を確認する
- 同一カードの短時間連打でないか確認する

### DB 接続異常
- `docker compose -f docker/docker-compose.mysql.yml ps` で `mysql` と `flask` の状態を確認する
- MySQL コンテナの healthcheck が `healthy` か確認する
- `.env` の `MYSQL_*` 設定が一致しているか確認する

## プライバシー運用
- `config.json`, `*.log`, `*.sqlite3`, バックアップファイルは Git に含めない
- 利用履歴を外部共有する場合は、個票ではなく集計値を使う
- カードIDや認証情報を画面共有・資料貼り付けに使わない

## 引き継ぎ時チェックリスト
- `.env.example` を元に新しい `.env` を作成した
- `config.example.json` を元に各子機の `config.json` を作成した
- MySQL 標準構成で起動確認した
- 管理画面ログインと子機 heartbeat を確認した
- 補充手順と障害時一次対応を担当者へ説明した
