# OITERU クイックスタート

このドキュメントは、サポート対象である MySQL 構成のセットアップと起動をまとめた唯一の手順書です。
親機サービスは Linux、MySQL 8、tmux 上で稼働します。Windows はローカル開発および
RC-S380 リーダーの利用手順には対応しますが、標準の本番ホストとしてはサポートしません。

## 1. Linux で親機サービスを起動する

必要なもの: Git、Python 3.10 以上、MySQL 8、tmux。

```bash
cd /home/hirameki-3/デスクトップ/oiteru_202603/
cp .env.example .env
chmod +x venv-start.sh scripts/*.sh
```

続行前に `.env` を編集してください。最低限、`FLASK_SECRET_KEY`、
`OITERU_ADMIN_PASSWORD`、`CARD_UID_HMAC_KEY`、`MYSQL_PASSWORD`、
`MYSQL_ROOT_PASSWORD` を置き換えます。ローカル限定の HTTP 開発では
`SESSION_COOKIE_SECURE=false` を設定してください。TLS を使用するすべてのデプロイでは、
必ず `true` に戻します。厳格なセキュリティを有効にしている場合は、ローカル以外の
平文 HTTP 親機 URL を有効にしないでください。

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
scripts/setup_local_mysql.sh --install
scripts/tmux_oiteru.sh start parent
scripts/tmux_oiteru.sh status parent
```

利用者向け画面は `http://localhost:5000/` で開きます。管理者としてログインするには
`http://localhost:5000/admin` を使用してください。親機サービスの初回起動時に
アプリケーションの migration が適用されます。個別に DDL を実行しないでください。

よく使う tmux コマンド:

```bash
scripts/tmux_oiteru.sh attach parent
scripts/tmux_oiteru.sh logs parent
scripts/tmux_oiteru.sh restart parent
```

## 2. Raspberry Pi 子機

対象の Raspberry Pi 上で実行してください。GPIO、NFC、モーターのテストは、
開発用 PC では検証できません。

```bash
cd ~/oiteru_202603
chmod +x scripts/setup_unit_environment.sh scripts/provision_unit.sh
./scripts/setup_unit_environment.sh
sudo scripts/provision_unit.sh
scripts/tmux_oiteru.sh start unit
scripts/tmux_oiteru.sh status unit
```

`provision_unit.sh` は、パーミッション `0600` の `/etc/oiteru/unit-secret` を作成し、
`config.json` にはそのパスのみを書き込みます。また、親機に到達できることも確認します。
子機は、管理者による承認が完了するまで保留状態のままです。

ステッピングモーターを直接接続する場合は、`MOTOR_TYPE=STEPPER` と
`CONTROL_METHOD=RASPI_DIRECT` を維持してください。また、`config.json` の BCM ピンが
LED やセンサーと重複していないことを確認してください。詳細は
[../config_templates/README.md](../config_templates/README.md).

## 3. Windows でのローカル開発

Python 3.10 以上をインストールし、`.venv` を作成して `.env` をコピー・設定した後、
開発用のローカル MySQL インスタンスを起動してください。親機サービスは次のように起動します:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv-start.ps1 parent-mysql
```

RC-S380 を使用する場合は、[card_reader_windows.md](card_reader_windows.md) を参照してください。

## 4. 運用前の確認

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check .
git diff --check
```

Windows では、該当する Windows 用 Python パスを使用してください。本番運用および
復旧手順は [operations.md](operations.md) を参照してください。
