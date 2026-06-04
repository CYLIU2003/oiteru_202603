# OITERU かんたんスタートガイド

このガイドは、OITERU を初めて触る人が **Linux 系 OS + tmux + ローカル MySQL** で親機と子機を起動できるようにまとめた手順書です。

コマンドを上から順に実行すれば、基本的な起動確認まで進められます。Docker は標準手順では使いません。

## 0. 必要なソフトウェアと環境

### 必須環境

| 区分 | 必須 / 推奨 | 内容 |
|---|---|---|
| 親機 OS | 必須 | Ubuntu 22.04 LTS 以降などの Linux 系 OS |
| 子機 OS | 必須 | Raspberry Pi OS 64-bit 推奨 |
| Python | 必須 | Python 3.10 以上 |
| DB | 必須 | MySQL 8.0 系 |
| 起動管理 | 必須 | tmux |
| Git | 必須 | Git CLI |
| ネットワーク | 必須 | 親機と子機が相互通信できる LAN / Tailscale 等 |
| エディタ | 推奨 | Visual Studio Code |

### 公式ダウンロード URL

| ソフトウェア | 用途 | URL |
|---|---|---|
| Ubuntu | 親機 Linux OS の候補 | https://ubuntu.com/download |
| Raspberry Pi Imager | Raspberry Pi OS を SD カードへ書き込む | https://www.raspberrypi.com/software/ |
| Raspberry Pi OS | 子機 OS | https://www.raspberrypi.com/software/operating-systems/ |
| Python | Python 本体 | https://www.python.org/downloads/ |
| Git | Git CLI | https://git-scm.com/downloads |
| MySQL Community Server | 親機 DB | https://dev.mysql.com/downloads/mysql/ |
| tmux | tmux 本体。Linux では通常 `apt` で入れる | https://github.com/tmux/tmux/releases |
| Visual Studio Code | 推奨エディタ | https://code.visualstudio.com/download |
| Tailscale | 別ネットワーク間で親機・子機をつなぐ場合の任意 VPN | https://tailscale.com/downloads |

Linux では、通常は次のコマンドで必要な実行環境をまとめて入れます。

```bash
sudo apt update
sudo apt install -y git tmux python3-full python3-venv python3-pip mysql-server curl
```

## 1. 最初に知っておくこと

### 役割

| 名前 | 何をするか | 主なファイル |
|---|---|---|
| 親機 | 管理画面、DB、利用履歴、子機状態を管理する | `db_server.py` |
| 子機 | NFC カードを読み、排出制御と heartbeat 送信を行う | `unit.py` |
| 従親機 | 親機 DB を参照する追加サーバー。必要な時だけ使う | `server.py` |

### 標準構成

| 項目 | 標準 |
|---|---|
| OS | Linux 系 OS |
| 起動方法 | tmux |
| DB | MySQL 8 (InnoDB) |
| 親機 | `db_server.py` |
| 子機 | `unit.py` |
| 起動補助 | `scripts/tmux_oiteru.sh` |

SQLite と `server.py` 単体起動は legacy 経路です。新しく作業する人は、親機では `db_server.py` を使ってください。

## 2. tmux の超基本

tmux は、SSH を切ってもプログラムを動かし続けるための道具です。

| やりたいこと | コマンド |
|---|---|
| セッション一覧を見る | `tmux ls` |
| 画面から一時退出する | `Ctrl+b` → `d` |
| 親機に戻る | `scripts/tmux_oiteru.sh attach parent` |
| 子機に戻る | `scripts/tmux_oiteru.sh attach unit` |
| 状態を見る | `scripts/tmux_oiteru.sh status` |
| 停止する | `scripts/tmux_oiteru.sh stop <parent|unit>` |

手動で tmux を使う場合の名前:

| 用途 | 推奨セッション名 |
|---|---|
| 親機 | `oiteru-parent` |
| 子機 | `oiteru-unit` |
| 従親機 | `oiteru-sub-parent` |

## 3. 共通準備

親機でも子機でも、まずプロジェクトフォルダへ移動します。

```bash
cd ~/Desktop/oiteru_202603
```

場所が分からない場合:

```bash
find ~ -name unit.py 2>/dev/null | grep oiteru
```

現在の場所を確認:

```bash
pwd
```

ブランチ確認と最新化:

```bash
git branch --show-current
git pull
git status --short
```

必要な Linux パッケージ:

```bash
sudo apt update
sudo apt install -y git tmux python3-full python3-venv python3-pip curl
```

## 4. 親機の初回設定

親機では `.env` を作ります。

```bash
cp .env.example .env
nano .env
```

最低限、次を変更してください。

| 変数 | 何を入れるか |
|---|---|
| `FLASK_SECRET_KEY` | 長いランダム文字列 |
| `OITERU_ADMIN_PASSWORD` | 管理画面ログイン用パスワード |
| `MYSQL_PASSWORD` | MySQL 接続パスワード |
| `MYSQL_ROOT_PASSWORD` | MySQL root パスワード |

保存方法:

```text
Ctrl+o → Enter → Ctrl+x
```

## 5. ローカル MySQL を準備する

親機では MySQL を OS のサービスとして起動します。

```bash
sudo apt install -y mysql-server
scripts/setup_local_mysql.sh
```

接続確認:

```bash
systemctl status mysql
mysql -u oiteru_user -p oiteru -e "SELECT 1;"
```

`.env` で `MYSQL_DATABASE` や `MYSQL_USER` を変更した場合は、確認コマンドも同じ値に読み替えてください。

## 6. 親機を tmux で起動する

```bash
scripts/tmux_oiteru.sh start parent
scripts/tmux_oiteru.sh attach parent
```

起動後、ブラウザで開きます。

```text
http://<親機IP>:5000/admin
```

同じ PC で確認する場合:

```text
http://localhost:5000/admin
```

SSH から抜けたい場合は `Ctrl+b` → `d` です。親機は動き続けます。

親機へ戻る:

```bash
scripts/tmux_oiteru.sh attach parent
```

ログを見る:

```bash
scripts/tmux_oiteru.sh logs parent
```

## 7. 子機の初回設定

子機では `config.json` を作ります。

```bash
cd ~/Desktop/oiteru_202603
cp config.example.json config.json
nano config.json
```

最低限、次を変更してください。

| キー | 何を入れるか | 例 |
|---|---|---|
| `SERVER_URL` | 親機 URL | `http://192.168.1.10:5000` |
| `UNIT_NAME` | 子機名 | `unit-01` |
| `UNIT_PASSWORD` | 親機側と合わせるパスワード | `change-this` |

子機が Raspberry Pi の場合、必要に応じて pigpio も準備します。

```bash
sudo apt install -y pigpio
sudo systemctl enable pigpiod
sudo systemctl start pigpiod
```

## 8. 子機を tmux で起動する

```bash
scripts/tmux_oiteru.sh start unit
scripts/tmux_oiteru.sh attach unit
```

SSH から抜けたい場合は `Ctrl+b` → `d` です。

子機へ戻る:

```bash
scripts/tmux_oiteru.sh attach unit
```

ログを見る:

```bash
scripts/tmux_oiteru.sh logs unit
```

## 9. 管理画面で確認する

親機のブラウザで次を開きます。

```text
http://<親機IP>:5000/admin
```

確認すること:

| 確認 | 見る場所 |
|---|---|
| ログインできる | 管理画面 |
| 子機が表示される | 子機一覧 |
| 子機の最終接続が更新される | 子機詳細 |
| 在庫数が正しい | 子機詳細 |
| 利用履歴が残る | 履歴画面 |

## 10. よく使うコマンド

```bash
git branch --show-current
git status --short
tmux ls
scripts/tmux_oiteru.sh status
systemctl status mysql
curl http://localhost:5000
```

親機を再起動:

```bash
scripts/tmux_oiteru.sh restart parent
```

子機を再起動:

```bash
scripts/tmux_oiteru.sh restart unit
```

## 11. トラブルシューティング

### tmux に戻れない

```bash
tmux ls
scripts/tmux_oiteru.sh status
scripts/tmux_oiteru.sh attach parent
```

子機の場合:

```bash
scripts/tmux_oiteru.sh attach unit
```

### 管理画面が開かない

```bash
scripts/tmux_oiteru.sh status parent
scripts/tmux_oiteru.sh logs parent
curl http://localhost:5000
```

親機 tmux のログに DB 接続エラーが出ている場合は、`.env` の `MYSQL_*` と MySQL サービスを確認してください。

### MySQL に接続できない

```bash
systemctl status mysql
scripts/setup_local_mysql.sh
mysql -u oiteru_user -p oiteru -e "SELECT 1;"
```

`.env` の `MYSQL_PASSWORD` が `change-this-mysql-password` のままだと初期化スクリプトは止まります。必ず変更してください。

### 子機が親機に接続できない

子機側で確認:

```bash
curl http://<親機IP>:5000
```

`config.json` の `SERVER_URL` が `http://<親機IP>:5000` になっているか確認してください。

### NFC が読めない

```bash
lsusb
python - <<'PY'
import nfc
print(nfc)
PY
```

USB リーダーを抜き差しし、子機を再起動してください。

### externally-managed-environment と出る

Raspberry Pi OS Bookworm 以降では、直接 `pip install` しないで venv を使います。

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-client.txt
```

通常は `./venv-start.sh unit` が自動で処理します。

## 12. 作業前後チェックリスト

作業前:

```bash
git branch --show-current
git pull
git status --short
tmux ls
```

作業後:

```bash
python -m unittest
scripts/tmux_oiteru.sh status
systemctl status mysql
```

秘密情報確認:

```bash
git status --short
```

`.env`, `config.json`, `logs/`, ログ、DB ファイルをコミットしないでください。

## 13. 補足: Windows について

Windows 用の PowerShell や bat スクリプトは残っていますが、この取説の標準ではありません。

レビュー、実証運用、引き継ぎでは Linux/tmux 手順を基準にしてください。

最終更新: 2026-06-04
