# 🚀 OITERU QUICKSTART
## 親機・従親機・子機の立ち上げガイド

<div style="text-align: right;">
  <span class="badge badge-primary">Version 2.0</span>
  <span class="badge badge-accent">Updated: 2025-12-24</span>
</div>

このガイドは「まず動かす」ための手順書です。

- **🖥️ 親機**: DBを持つサーバー（SQLiteまたはMySQLで運用）
- **🔗 従親機**: DBを持たないサーバー（外部MySQLに接続して運用）
- **📡 子機**: NFC/モーターで実際に排出する端末（Raspberry Pi等）

> **💡 補足**: 本リポジトリでは `server.py` が親機/従親機の両方を担える設計です。

---

## 0. 🏁 まず結論（最小の動かし方）

| 目的 | 推奨構成 | コマンド |
|---|---|---|
| **手元PCだけで試す** | 親機 (SQLite) | `.\venv-start.ps1 parent-sqlite` |
| **本番運用** | 親機 (MySQL+Docker) | `./docker-start.sh mysql` |

---

## 1. 🛠️ 共通準備（Windows / PowerShell想定）

### 1.1 必要なもの

- 🐍 **Python**（`.venv` を使う構成が前提）
- 🐳 **Docker Desktop**（MySQL運用する場合）

### 1.2 依存関係のインストール

このワークスペースには「依存を入れる」タスクが用意されています。

- タスク: `Install Requirements`

（手動で行う場合は `requirements.txt` を参照）

---

## 2. 🖥️ 親機の立ち上げ

親機は「データベースを持つサーバー」です。

### 2.1 方法A: 支援スクリプトを使う（推奨）

Dockerを使わない仮想環境（venv）で起動する場合、以下のスクリプトを使うと簡単です。

**Windows (PowerShell):**
```powershell
# SQLite版（手軽に試すならこれ）
.\venv-start.ps1 parent-sqlite

# MySQL版（Docker等でMySQLがlocalhost:3306にある場合）
.\venv-start.ps1 parent-mysql
```

**Linux / Mac:**
```bash
# SQLite版
./venv-start.sh parent-sqlite

# MySQL版
./venv-start.sh parent-mysql
```

### 2.2 方法B: Dockerを使う

Docker環境が整っている場合は、以下のスクリプトで一発起動できます。

```bash
# MySQLサーバーとFlaskサーバーをまとめて起動
./docker-start.sh mysql
```

### 2.3 方法C: 手動コマンド（詳細）

スクリプトを使わずに起動する場合のコマンドです。

**SQLite版:**
```bash
# Windows
.venv\Scripts\python.exe server.py

# Linux
.venv/bin/python server.py
```

**MySQL版（環境変数を指定）:**
```powershell
# Windows (PowerShell)
$env:DB_TYPE='mysql'; $env:MYSQL_HOST='localhost'; .venv\Scripts\python.exe server.py
```

---

## 3. 🔗 従親機の立ち上げ（外部MySQLに接続）

従親機は「DBを持たず、外部MySQLを参照するサーバー」です。
※ 親機と同じMySQLに接続することで、データを共有します。

### 3.1 方法A: 支援スクリプトを使う（推奨）

**Windows (PowerShell):**
```powershell
# デフォルトで localhost:3306 のMySQLに接続します
.\venv-start.ps1 sub-parent
```

**Linux / Mac:**
```bash
./venv-start.sh sub-parent
```

### 3.2 方法B: Dockerを使う

```bash
# 外部DB設定（docker-compose.external-db.yml）を使って起動
./docker-start.sh external
```

### 3.3 方法C: 手動コマンド（詳細）

```powershell
# Windows (PowerShell) - 接続先やサーバー名を指定
$env:DB_TYPE='mysql'
$env:MYSQL_HOST='192.168.1.10'  # 親機(DB)のIP
$env:SERVER_NAME='従親機A'
.venv\Scripts\python.exe server.py
```

---

## 4. 📡 子機の立ち上げ（Raspberry Pi 等）

子機は `unit.py` を使います。

### 4.1 事前に設定する（重要）

`config.json` を編集して、少なくとも以下を合わせてください。

- `SERVER_URL` : 親機/従親機のURL
  - 例: `http://192.168.1.10:5000`
- `UNIT_NAME` / `UNIT_PASSWORD` : サーバー側の子機登録情報と一致させる

### 4.2 方法A: 支援スクリプトを使う（推奨）

**Windows (PowerShell):**
```powershell
.\venv-start.ps1 unit
```

**Linux / Mac (Raspberry Pi):**
```bash
./venv-start.sh unit
```

### 4.3 方法B: Dockerを使う

```bash
# 子機用コンテナを起動
./docker-start.sh unit
```

### 4.4 方法C: 手動コマンド（詳細）

```bash
# Linux (Raspberry Pi)
# 権限が必要な場合（GPIO/NFC）は sudo が必要なこともあります
sudo .venv/bin/python unit.py
```

---

## 5. 📜 支援スクリプトについて

このプロジェクトには、起動を簡単にするためのスクリプトが用意されています。

### 5.1 `venv-start.ps1` / `venv-start.sh` (仮想環境用)

Dockerを使わず、ローカルのPython仮想環境（`.venv`）を使って起動するためのスクリプトです。
環境変数の設定などを自動で行います。

- **Windows**: `.\venv-start.ps1 [mode]`
- **Linux**: `./venv-start.sh [mode]`

**モード一覧:**
- `parent-sqlite`: 親機 (SQLite)
- `parent-mysql`: 親機 (MySQL接続)
- `sub-parent`: 従親機 (MySQL接続)
- `unit`: 子機

### 5.2 `docker-start.sh` (Docker用)

Docker Composeコマンドをラップしたスクリプトです。
`docker/` フォルダ内の適切なYAMLファイルを選択して起動します。

- **使い方**: `./docker-start.sh [mode]`

**モード一覧:**
- `mysql`: 親機DB版（MySQL + Webサーバー）
- `external`: 従親機（外部DB接続）
- `unit`: 子機
- `stop`: 全コンテナ停止

---

## 6. ❓ トラブルシューティング（よくある順）

### 6.1 サーバーが起動しない / 5000番が使われている

<div class="alert alert-warning">
  <strong>症状:</strong> 起動直後にエラー / <code>Address already in use</code>
</div>

**対処:**
1. すでに別の `server.py` が動いていないか確認
2. 5000番を使っている別プロセスを停止
3. それでもダメなら、ポート変更（アプリ側の設定）を検討

### 6.2 ブラウザで開けない（見えない）

<div class="alert alert-warning">
  <strong>症状:</strong> <code>http://localhost:5000</code> がタイムアウト
</div>

**対処:**
1. サーバーの起動ログにエラーが無いか確認
2. Windowsファイアウォール/セキュリティソフトのブロックを確認
3. 別PC/子機からアクセスする場合は、`localhost` ではなく **サーバーPCのIPアドレス** を使う

### 6.3 MySQLに接続できない

<div class="alert alert-warning">
  <strong>症状:</strong> サーバー起動時にDB接続エラー
</div>

**対処:**
1. `MYSQL_HOST` / `MYSQL_PORT` / `MYSQL_USER` / `MYSQL_PASSWORD` が正しいか
2. MySQLコンテナが起動しているか（Docker Desktop側で確認）
3. WindowsからMySQLへ接続する場合、ポート開放が必要なことがあります
   - 参考: `scripts/open_mysql_port_windows.ps1`

### 6.4 テーブルが無い / 初期化されていない

<div class="alert alert-warning">
  <strong>症状:</strong> 画面表示やAPIで「no such table」「table doesn’t exist」
</div>

**対処:**
- **SQLite運用**: `oiteru.sqlite3` が正しい場所にあるか、初回起動で生成されるか
- **MySQL運用**: `docker/init_mysql.sql` が実行されているか

### 6.5 子機がサーバーに繋がらない

<div class="alert alert-warning">
  <strong>症状:</strong> 子機側で接続エラー
</div>

**対処:**
1. `config.json` の `SERVER_URL` が正しいか
   - サーバーPCから見た `localhost` を子機で使うのはNG（子機にとっては子機自身のlocalhost）
2. サーバーがLAN内で疎通可能か（IPアドレス変更に注意）
3. ファイアウォールで5000番が遮断されていないか

### 6.6 NFCが読めない

**対処の方針:**
1. USB接続を確認
2. OSからデバイスが認識されているか確認
3. コンテナ内で扱う場合はデバイスのアタッチが必要
   - 参考: `scripts/attach_card_reader.ps1` / `scripts/fix_card_reader.ps1`

---

## 7. 📚 次に読む

- 詳細な仕様/設定/運用: `取説書/README.md`
- Docker構成: `docker/`
- 診断ツール: `tools/`
