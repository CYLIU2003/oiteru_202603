# OITERU クイックスタート

OITERU の標準構成は **Linux 親機 + MySQL 8 + Raspberry Pi 子機**です。親機は tmux 内で起動します。SSH を閉じても tmux セッションと親機は継続します。

## 起動方法の選び方

| 目的・環境 | 使うもの | 扱い |
| --- | --- | --- |
| Linux の標準 MySQL 親機 | `venv-start.sh parent-mysql` | 標準 |
| Windows で親機を直接起動 | `scripts/start_parent.ps1` | Windows 開発・補助用 |
| BIOS 風 CUI を開く | `scripts/launcher.sh` → `2` | 補助用。標準運用には使わない |
| `scripts/start_oiteru.sh` | 旧 Docker 起動スクリプト | 標準運用には使わない |

`scripts/start_oiteru.sh` は BIOS 風画面を開くスクリプトではありません。Docker Compose を前提とした旧経路です。BIOS 風の対話画面は `scripts/launcher.sh` の CUI 版です。CUI ランチャーには SQLite など古い既定設定が残っているため、学内実証の MySQL 親機を起動する用途には使いません。

## 1. Linux 親機を準備する

初回だけ、リポジトリ直下で `.env` を作成・編集します。

```bash
cp .env.example .env
chmod 600 .env
nano .env
```

少なくとも次をテンプレートの値から変更します。

- `FLASK_SECRET_KEY`
- `OITERU_ADMIN_USERNAME`
- `OITERU_ADMIN_PASSWORD`
- `CARD_UID_HMAC_KEY`
- `MYSQL_PASSWORD`

`DB_TYPE=mysql` を維持します。`.env` は Git、チャット、チケットに保存しません。

Python と MySQL を準備します。MySQL が未導入の場合だけ `--install` を付けます。

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip tmux curl
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
scripts/setup_local_mysql.sh --install
```

MySQL がすでに導入済みなら、最後のコマンドは次です。

```bash
scripts/setup_local_mysql.sh
```

`OITERU local MySQL is ready` と表示されたら、親機を起動できます。

## 2. Linux 親機を tmux で起動する

リポジトリ直下で tmux セッションを作成します。

```bash
tmux new -s oiteru-parent
```

tmux 内で、MySQL 親機の起動スクリプトを実行します。

```bash
./venv-start.sh parent-mysql
```

初回起動時は migration が実行されます。エラーが表示された場合は、その画面の内容を確認してから修正します。

tmux を閉じずに抜けるには、次の順に押します。

```text
Ctrl-b、続けて d
```

再び親機の画面を開くには、別のシェルから実行します。

```bash
tmux attach -t oiteru-parent
```

セッション一覧の確認と停止は次です。

```bash
tmux ls
tmux kill-session -t oiteru-parent
```

## 3. 親機を確認する

tmux とは別のシェルで実行します。

```bash
curl --fail http://127.0.0.1:5000/api/health
```

`"status":"ok"` が返れば起動しています。

| 画面 | URL |
| --- | --- |
| 利用者画面 | `http://127.0.0.1:5000/` |
| 管理画面 | `http://127.0.0.1:5000/admin` |

HTTPS 運用では、組織で割り当てた親機 URL を使います。管理画面には `.env` の管理者アカウントでログインします。

## 4. Windows で親機を起動する

Windows は tmux の標準運用対象ではありません。PowerShell を開き、リポジトリ直下で実行します。

```powershell
.\scripts\start_parent.ps1
```

このスクリプトは仮想環境と MySQL 接続を確認して親機を直接起動します。停止は実行画面で `Ctrl-c` です。

## 5. BIOS 風 CUI を使う場合

BIOS 風の対話画面を開くだけなら、次を実行します。

```bash
cd scripts
./launcher.sh
```

最初の画面で `2` を選ぶと CUI 版ランチャーが開きます。ただし、これは親機・子機・Docker をまとめた旧ランチャーであり、SQLite や古い MySQL 設定を選べます。MySQL 標準構成を誤って SQLite で起動しないため、学内実証の親機起動には「2. Linux 親機を tmux で起動する」を使ってください。

## 6. 次に行うこと

親機が起動したら、Raspberry Pi 子機を準備し、管理画面で承認します。子機の環境構築は [scripts/SETUP_UNIT.md](scripts/SETUP_UNIT.md)、日常運用・障害対応は [docs/operations.md](docs/operations.md) を参照してください。

最終更新: 2026-08-23
