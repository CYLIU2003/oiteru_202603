# OITERU クイックスタート

OITERU の標準構成は **Linux 親機 + MySQL 8 + Raspberry Pi 子機**です。運用端末から親機・子機へ SSH 接続し、それぞれを tmux 内で常駐起動します。SSH を切断してもプロセスは動き続けます。

```text
運用端末
├─ SSH → 親機 → tmux: oiteru-parent
└─ SSH → 子機 → tmux: oiteru-unit
```

以下では、両方のホストでリポジトリを `~/oiteru_202603` に配置したものとします。

## 1. 親機の初回準備

運用端末から親機へ SSH 接続します。

```bash
ssh <親機ユーザー>@<親機ホスト>
cd ~/oiteru_202603
```

`.env` を作成し、テンプレートの `change-this-...` を実際の値へ変更します。

```bash
cp .env.example .env
chmod 600 .env
nano .env
```

最低限、次を設定します。

- `DB_TYPE=mysql`
- `FLASK_SECRET_KEY`
- `OITERU_ADMIN_USERNAME`
- `OITERU_ADMIN_PASSWORD`
- `CARD_UID_HMAC_KEY`
- `MYSQL_PASSWORD`

Python と MySQL を準備します。

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip tmux curl
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
scripts/setup_local_mysql.sh --install
```

MySQL が導入済みの場合、最後のコマンドは `scripts/setup_local_mysql.sh` だけで構いません。

## 2. 親機を SSH + tmux で常駐起動する

親機へ SSH 接続し、リポジトリへ移動します。

```bash
ssh <親機ユーザー>@<親機ホスト>
cd ~/oiteru_202603
```

親機用 tmux セッションを作ります。

```bash
tmux new -s oiteru-parent
```

tmux 内で MySQL 親機を起動します。

```bash
./venv-start.sh parent-mysql
```

親機を止めずに tmux から抜けるには、`Ctrl-b`、続けて `d` を押します。その後は SSH を切断して構いません。

別のシェルで親機へ SSH 接続し、health check を実行します。

```bash
ssh <親機ユーザー>@<親機ホスト>
curl --fail http://127.0.0.1:5000/api/health
```

`"status":"ok"` が返れば親機は起動済みです。

## 3. 子機の初回準備

運用端末から Raspberry Pi 子機へ SSH 接続します。

```bash
ssh <子機ユーザー>@<子機ホスト>
cd ~/oiteru_202603
```

子機用の OS パッケージと Python 環境を準備します。

```bash
./scripts/setup_unit_environment.sh
```

I2C を新しく有効化した場合は再起動し、再度 SSH 接続します。

```bash
sudo reboot
```

子機から親機へ接続できることを確認します。

```bash
curl --fail https://<親機URL>/api/health
```

閉じた開発ネットワークで HTTP を使う場合は、`http://<親機IP>:5000/api/health` に置き換えます。

次に、子機名・親機 URL・16文字以上の子機用シークレットを対話形式で設定します。

```bash
sudo scripts/provision_unit.sh
```

`HTTP 404` は、親機への接続に成功し、未承認子機として保留登録されたことを示します。`config.json` と `/etc/oiteru/unit-secret` は Git に追加しません。

親機の管理画面で `/admin/units` を開き、「新規子機を登録」→「自動探知を開始」→「この子機を登録」の順に承認します。子機名と接続元 IP が実機と一致することを確認してください。

## 4. 子機を SSH + tmux で常駐起動する

子機へ SSH 接続し、リポジトリへ移動します。

```bash
ssh <子機ユーザー>@<子機ホスト>
cd ~/oiteru_202603
```

子機用 tmux セッションを作ります。

```bash
tmux new -s oiteru-unit
```

HTTPS の親機へ接続する標準構成では、tmux 内で子機を起動します。

```bash
./venv-start.sh unit
```

親機 URL が非ローカルの平文 HTTP である開発環境では、上のコマンドの代わりに次を実行します。学内実証では HTTPS を使い、この設定は行いません。

```bash
export OITERU_STRICT_SECURITY=false
./venv-start.sh unit
```

NFC、GPIO、親機接続、heartbeat のエラーが表示されていないことを確認します。子機を止めずに tmux から抜けるには、`Ctrl-b`、続けて `d` を押します。その後は SSH を切断して構いません。

## 5. tmux の再接続・停止

親機へ再接続する場合:

```bash
ssh <親機ユーザー>@<親機ホスト>
tmux attach -t oiteru-parent
```

子機へ再接続する場合:

```bash
ssh <子機ユーザー>@<子機ホスト>
tmux attach -t oiteru-unit
```

各ホストでセッション一覧を確認できます。

```bash
tmux ls
```

停止する場合は、対象の tmux へ接続して `Ctrl-c` を押します。セッションごと終了する場合は次を実行します。

```bash
# 親機で実行
tmux kill-session -t oiteru-parent

# 子機で実行
tmux kill-session -t oiteru-unit
```

## 6. 起動後の確認

- 親機の `/api/health` が `status: ok` を返す。
- 管理画面へログインできる。
- 子機が承認済み・オンラインとして表示される。
- 管理画面の在庫数と実際の投入数が一致する。
- NFC、LED、センサー、モーターにエラーがない。
- 親機では `oiteru-parent`、子機では `oiteru-unit` が `tmux ls` に表示される。

## 補足: その他の起動スクリプト

| スクリプト | 用途 |
| --- | --- |
| `scripts/start_parent.ps1` | Windows で親機を直接起動する補助スクリプト |
| `scripts/start_oiteru.sh` | Docker Compose 前提の旧親機起動スクリプト |
| `scripts/launcher.sh` | GUI/CUI ランチャー。`2` で BIOS 風 CUI を開く |
| `scripts/start_unit.sh` | 引数指定型の旧子機起動スクリプト |

BIOS 風 CUI と旧起動スクリプトには SQLite や古い設定経路が残っています。学内実証では、この文書の `venv-start.sh parent-mysql` と `venv-start.sh unit` を使用します。

子機の詳細は [scripts/SETUP_UNIT.md](scripts/SETUP_UNIT.md)、日常運用・障害対応は [docs/operations.md](docs/operations.md) を参照してください。

最終更新: 2026-08-23
