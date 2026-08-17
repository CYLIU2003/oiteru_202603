# OITERU クイックスタート

このガイドでは、OITERU の親機と子機をセットアップし、tmux で常駐起動するまでを
説明します。親機は Linux + MySQL 8、子機は Raspberry Pi を標準環境とします。

## 最初に確認すること

親機と子機は通常、別のホストで動かします。各ホストへ SSH 接続し、それぞれの
プロジェクトルートでコマンドを実行してください。

起動方法は次の順で説明します。

1. **常駐用 tmux 起動**: 通常はこちらを使用します。SSH を切断しても動作を継続します。
2. **一時確認用の前景起動**: 短時間の動作確認に使用し、`Ctrl-c` で終了します。

| 役割 | 標準ホスト | 常駐時の tmux セッション |
|---|---|---|
| 親機 | Linux サーバー | `oiteru-parent` |
| 子機 | Raspberry Pi | `oiteru-unit` |

Windows はローカル開発と RC-S380 の確認には使用できますが、学内実証の標準運用
ホストではありません。

## 1. 親機を準備する

### 1-1. 必要なソフトウェア

- Git
- Python 3.10 以上
- MySQL 8
- tmux

プロジェクトの配置先は任意です。次の例では `~/oiteru_202603` を使用します。

```bash
cd ~/oiteru_202603
cp .env.example .env
chmod +x venv-start.sh scripts/setup_local_mysql.sh scripts/tmux_oiteru.sh
```

### 1-2. `.env` を設定する

`.env` を開き、少なくとも次の値を初期値から変更してください。

| 設定 | 用途 |
|---|---|
| `FLASK_SECRET_KEY` | 管理画面セッションの署名キー（32文字以上） |
| `OITERU_ADMIN_USERNAME` | 初回管理者のユーザー名 |
| `OITERU_ADMIN_PASSWORD` | 初回管理者のパスワード |
| `CARD_UID_HMAC_KEY` | カード UID を擬似 ID 化するキー（32文字以上） |
| `MYSQL_PASSWORD` | OITERU 用 MySQL ユーザーのパスワード |

`.env` は認証情報を含むため、Git に追加したり、チャットへ貼り付けたりしないでください。

ローカルの平文 HTTP で開発するときだけ、次の2項目を両方 `false` にできます。

```dotenv
SESSION_COOKIE_SECURE=false
OITERU_STRICT_SECURITY=false
```

TLS を使う学内実証・本番環境では、両方を `true` にし、TLS 終端済みの `https://...`
URL を使用します。`MYSQL_ROOT_PASSWORD` は Docker Compose 用の設定であり、このガイドの
ローカル MySQL セットアップスクリプトでは使用しません。

### 1-3. Python 環境を作成する

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
```

### 1-4. MySQL を準備する

MySQL が未導入の場合は、次を実行します。

```bash
scripts/setup_local_mysql.sh --install
```

MySQL 8 が導入済みの場合は、`--install` を付けません。

```bash
scripts/setup_local_mysql.sh
```

このスクリプトは `.env` を読み、ローカル MySQL の DB とユーザーを作成します。
MySQL の導入・起動と DB 作成には `sudo` 権限が必要です。手書きの DDL は実行しないで
ください。アプリケーションの migration は親機起動時に適用されます。

## 2. 親機を起動する

### 2-1. 常駐させる場合: tmux

通常運用では、親機を tmux セッションに常駐させます。

```bash
scripts/tmux_oiteru.sh start parent
scripts/tmux_oiteru.sh status parent
```

`running: oiteru-parent` は tmux セッションが存在することを示します。続けて親機 API が
応答することを確認します。

```bash
curl http://localhost:5000/api/health
```

レスポンスに `"status":"ok"` が含まれていれば、親機の起動完了です。

```bash
scripts/tmux_oiteru.sh attach parent   # 実行画面を開く
scripts/tmux_oiteru.sh logs parent     # ログを追跡する
scripts/tmux_oiteru.sh restart parent  # 再起動する
scripts/tmux_oiteru.sh stop parent     # 停止する
```

`attach` 中は `Ctrl-b`、続けて `d` を押すと、親機を停止せずに tmux から離脱できます。
`logs` は `Ctrl-c` で終了します。既存セッションがある状態で `start` を実行しても
二重起動せず、既存セッションへの `attach` が案内されます。

### 2-2. 一時的に起動する場合: 前景起動

短時間だけ確認するときは、tmux を使わず前景で起動します。

```bash
./venv-start.sh parent-mysql
```

終了するには `Ctrl-c` を押します。

### 2-3. 親機の画面を確認する

| 画面 | URL |
|---|---|
| 利用者向け画面 | `https://<公開している親機URL>/` |
| 管理画面 | `https://<公開している親機URL>/admin` |

ローカル HTTP 開発では、前述の2つのセキュリティ設定を `false` にしたうえで
`http://<親機IP>:5000/` を使用できます。親機と同じホストでは
`http://localhost:5000/` を開きます。管理画面へ `.env` の管理者情報でログインできる
ことを確認してください。

## 3. 子機を準備する

GPIO、NFC リーダー、モーターは Raspberry Pi 実機で確認してください。子機の作業を
始める前に、親機が起動し、Raspberry Pi から親機 URL へ接続できることを確認します。

### 3-1. 実行環境をセットアップする

Raspberry Pi 上で実行します。

```bash
cd ~/oiteru_202603
chmod +x venv-start.sh scripts/setup_unit_environment.sh \
  scripts/provision_unit.sh scripts/tmux_oiteru.sh
./scripts/setup_unit_environment.sh
```

このスクリプトは tmux、子機用 OS パッケージ、`.venv`、および
`requirements-client.txt` の依存関係を準備します。I2C を有効にした場合は、案内に
従って Raspberry Pi を再起動してから次へ進みます。

### 3-2. 子機を親機へ登録する

```bash
sudo scripts/provision_unit.sh
```

対話形式で次の値を入力します。

- 子機名
- 親機 URL
- 16文字以上の子機用シークレット

シークレットは `/etc/oiteru/unit-secret` に権限 `0600` で保存され、`config.json`
にはファイルパスだけが保存されます。シークレットを Git、チャット、チケットへ平文で
記録しないでください。

接続確認で返る `404` は、未承認の子機として親機へ到達できたことを示す正常な結果です。
`200` は、同じ子機がすでに承認済みであることを示します。それ以外で失敗した場合は、
親機 URL、ネットワーク、親機の起動状態を確認します。

子機は `.env` を読みません。検証のため子機から localhost 以外の平文 HTTP 親機へ
接続する場合だけ、子機を起動する同じシェルで次を設定します。学内実証・本番環境では
設定せず、HTTPS の親機 URL を使用してください。

```bash
export OITERU_STRICT_SECURITY=false
```

ステッピングモーターを Raspberry Pi に直接接続する場合は、`config.json` の
`"MOTOR_TYPE": "STEPPER"` と `"CONTROL_METHOD": "RASPI_DIRECT"` を維持してください。BCM ピンが
LED やセンサーと重複していないことも確認します。詳しくは
[config_templates/README.md](config_templates/README.md) を参照してください。

## 4. 子機を起動する

### 4-1. 常駐させる場合: tmux

通常運用では、子機を tmux セッションに常駐させます。

```bash
scripts/tmux_oiteru.sh start unit
scripts/tmux_oiteru.sh status unit
```

`running: oiteru-unit` と表示されれば、子機の tmux セッションが存在しています。ログを
開き、接続エラーやハードウェア初期化エラーがないことも確認してください。

```bash
scripts/tmux_oiteru.sh attach unit   # 実行画面を開く
scripts/tmux_oiteru.sh logs unit     # ログを追跡する
scripts/tmux_oiteru.sh restart unit  # 再起動する
scripts/tmux_oiteru.sh stop unit     # 停止する
```

`attach` 中は `Ctrl-b`、続けて `d` を押すと、子機を停止せずに tmux から離脱できます。
`logs` は `Ctrl-c` で終了します。既存セッションがある状態で `start` を実行しても
二重起動しません。

### 4-2. 一時的に起動する場合: 前景起動

短時間だけ確認するときは、tmux を使わず前景で起動します。

```bash
./venv-start.sh unit
```

終了するには `Ctrl-c` を押します。

### 4-3. 子機を承認する

provisioning の接続確認または初回 heartbeat を送信した子機は、未承認の保留状態に
なります。親機の管理画面で `/admin/units` を開き、「新規子機を登録」→「自動探知を
開始」→対象子機の「この子機を登録」の順に進み、子機名と接続元を確認して承認して
ください。次回 heartbeat が届くと、子機がオンラインになります。

## 5. Windows で親機を一時起動する

Windows は開発・検証用です。MySQL 8 を先に起動し、`.env` の認証情報と MySQL 接続先を
設定してください。

```powershell
Copy-Item .env.example .env
# .env を編集してから実行
.\venv-start.ps1 parent-mysql
```

`venv-start.ps1` は必要に応じて `.venv` を作成し、開発用依存関係をインストールします。
RC-S380 を使用する場合は [card_reader_windows.md](docs/card_reader_windows.md) を参照してください。

## 6. 起動後の確認

- 親機の管理画面へログインできる
- 子機が管理画面に表示され、承認後にオンラインになる
- 親機・子機の tmux セッションが `running` になっている
- `.env`、`config.json`、ログ、DB ファイルが Git の変更対象に含まれていない

開発時または変更後は、次のチェックも実行します。

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check .
git diff --check
```

Windows では `.venv\Scripts\python.exe` を使用します。日常運用、バックアップ、障害時の
対応は [operations.md](docs/operations.md)、子機の詳細なセットアップは
[scripts/SETUP_UNIT.md](scripts/SETUP_UNIT.md) を参照してください。詳細版は
[docs/quick_start.md](docs/quick_start.md) にも同じ手順で掲載しています。

最終更新: 2026-08-17
