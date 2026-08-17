# OITERU クイックスタート

このガイドでは、OITERU を構成する**親機**と**子機**を最短で起動します。親機は
Linux + MySQL 8、子機は Raspberry Pi を標準環境とします。起動にはどちらも tmux を
使用するため、SSH 接続を切ってもプロセスは継続します。

> Windows はローカル開発と RC-S380 の利用に対応していますが、学内実証の標準運用
> ホストではありません。

## 全体の流れ

1. 親機で MySQL と親機サービスを起動する
2. 管理画面へログインできることを確認する
3. Raspberry Pi 子機をセットアップし、親機の URL と子機用シークレットを登録する
4. 子機を起動し、管理者が承認する

親機と子機は通常は別ホストで動かします。同一ホストで検証する場合も、tmux セッションが
分かれるため同時起動できます。

| 役割 | 実行するホスト | tmux セッション | 起動コマンド |
|---|---|---|---|
| 親機 | Linux サーバー | `oiteru-parent` | `scripts/tmux_oiteru.sh start parent` |
| 子機 | Raspberry Pi | `oiteru-unit` | `scripts/tmux_oiteru.sh start unit` |

## 1. 親機を起動する（Linux）

### 1-1. 必要なもの

- Git
- Python 3.10 以上
- MySQL 8
- tmux

プロジェクトの配置先は任意です。以降はプロジェクトのルートディレクトリで実行します。

```bash
cd ~/oiteru_202603
cp .env.example .env
chmod +x venv-start.sh scripts/*.sh
```

### 1-2. `.env` を設定する

`.env` は認証情報を含むため、Git に追加・共有しないでください。少なくとも次の値を、
推測されにくい値へ変更します。

| 設定 | 用途 |
|---|---|
| `FLASK_SECRET_KEY` | 管理画面セッションの署名キー（32 文字以上） |
| `OITERU_ADMIN_USERNAME` / `OITERU_ADMIN_PASSWORD` | 初回管理者のログイン情報 |
| `CARD_UID_HMAC_KEY` | カード UID を擬似 ID 化するキー（32 文字以上） |
| `MYSQL_PASSWORD` | OITERU 用 MySQL ユーザーのパスワード |
| `MYSQL_ROOT_PASSWORD` | ローカル MySQL 初期設定用の root パスワード |

ローカルの平文 HTTP 開発だけでは、`SESSION_COOKIE_SECURE=false` と
`OITERU_STRICT_SECURITY=false` を**両方**設定できます。TLS を使う環境では、両方を
`true` のままにしてください。`MYSQL_HOST`、`MYSQL_PORT`、`MYSQL_DATABASE` は、別の
MySQL を使う場合のみ環境に合わせて変更します。

### 1-3. Python と MySQL を準備する

次のコマンドは仮想環境を作成し、依存関係とローカル MySQL の DB・ユーザーを準備します。
`--install` は MySQL サーバーが未導入の場合だけ付けてください。MySQL の導入・起動と
DB 作成には `sudo` 権限が必要です。

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt

# MySQL が未導入の場合
scripts/setup_local_mysql.sh --install

# MySQL が導入済みの場合
# scripts/setup_local_mysql.sh
```

手書きの DDL は実行しないでください。親機の起動時に migration が適用されます。

### 1-4. 親機を tmux で起動する

```bash
scripts/tmux_oiteru.sh start parent
scripts/tmux_oiteru.sh status parent
```

`running: oiteru-parent` と表示されれば起動しています。利用者向け画面は
`http://<親機のホスト名または IP>:5000/`、管理画面は
`http://<親機のホスト名または IP>:5000/admin` です。

ローカルホストだけで確認する場合は、`http://localhost:5000/` を開きます。

## 2. 子機を起動する（Raspberry Pi）

GPIO、NFC リーダー、モーターは Raspberry Pi 実機で確認してください。親機が起動済みで、
子機から親機の URL に到達できる状態にしてから始めます。

### 2-1. 子機の実行環境を準備する

```bash
cd ~/oiteru_202603
chmod +x scripts/setup_unit_environment.sh scripts/provision_unit.sh
./scripts/setup_unit_environment.sh
```

このスクリプトは tmux と子機に必要な OS パッケージ、`.venv`、および
`requirements-client.txt` の依存関係を用意します。I2C を有効にした場合は、案内に従い
再起動してから次へ進みます。

### 2-2. 子機を親機に登録する

次のコマンドは対話形式で、子機名・親機 URL・16 文字以上の子機用シークレットを尋ねます。
シークレットは `/etc/oiteru/unit-secret` に権限 `0600` で保存され、`config.json` には
ファイルパスだけが保存されます。

```bash
sudo scripts/provision_unit.sh
```

親機への接続確認に成功すると完了します。`404` は未承認の子機として親機に到達できた
ことを示す正常な結果です。接続に失敗した場合は、親機 URL、ネットワーク、親機の
tmux 状態を見直してください。

ステッピングモーターを直結する構成では、`config.json` の `MOTOR_TYPE=STEPPER` と
`CONTROL_METHOD=RASPI_DIRECT` を維持し、BCM ピンが LED・センサーと重複しないことを
確認します。詳しい設定は [config_templates/README.md](../config_templates/README.md) を
参照してください。

### 2-3. 子機を tmux で起動する

```bash
scripts/tmux_oiteru.sh start unit
scripts/tmux_oiteru.sh status unit
```

`running: oiteru-unit` と表示されれば起動しています。子機は、管理者が承認するまで
保留状態です。親機の管理画面の `/admin/units` で子機名と接続元を確認して承認します。
次回 heartbeat が届くと、子機はオンラインになります。子機用シークレットをチャットや
チケットに平文で書かないでください。

長期の無人運用では systemd 化を推奨します。設定例と注意点は
[operations.md](operations.md) を参照してください。

## 3. tmux の基本操作

親機・子機とも、操作するホスト上で同じ形式のコマンドを使います。

```bash
# 親機の例。子機の場合は parent を unit に置き換える
scripts/tmux_oiteru.sh attach parent  # 実行画面を表示する
scripts/tmux_oiteru.sh logs parent    # ログを追跡する
scripts/tmux_oiteru.sh restart parent # 再起動する
scripts/tmux_oiteru.sh stop parent    # 停止する
```

`attach` 中に `Ctrl-b`、続けて `d` を押すと、サービスを止めずに tmux から離脱できます。
SSH を切断してもセッションは継続します。再接続後は `attach`、または次のコマンドで
状態を確認してください。

```bash
scripts/tmux_oiteru.sh status
tmux ls
```

すでにセッションが存在する状態で `start` を実行しても二重起動せず、既存セッションへの
`attach` が案内されます。

## 4. Windows でローカル開発する

Windows は開発・検証用です。先に MySQL 8 を起動し、Linux の親機と同様に `.env` の
認証情報と接続先を設定します。

```powershell
Copy-Item .env.example .env
# .env を編集してから実行する
.\venv-start.ps1 parent-mysql
```

`venv-start.ps1` は必要に応じて `.venv` を作成し、開発用依存関係をインストールします。
RC-S380 を使う場合は [card_reader_windows.md](card_reader_windows.md) を参照してください。

## 5. 起動後の確認と次の資料

親機では管理画面にログインできること、子機では heartbeat が届き承認後にオンラインに
なることを確認します。変更前・運用開始前には、次のチェックを実行してください。

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check .
git diff --check
```

Windows では `.venv\\Scripts\\python.exe` を使います。日常運用、バックアップ、障害時の
一次対応は [operations.md](operations.md)、子機の詳細な手動セットアップは
[scripts/SETUP_UNIT.md](../scripts/SETUP_UNIT.md) を参照してください。

最終更新: 2026-08-17
