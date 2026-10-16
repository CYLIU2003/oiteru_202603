# 設定ファイルの役割

親機と子機で、使う設定ファイルが違います。変更は設置担当者と一緒に行ってください。

| 設定するもの | 見本 | 実際に使うファイル | 内容 |
| --- | --- | --- | --- |
| 親機 | [`.env.example`](../.env.example) | `.env` | DB 接続先、管理者認証、カード保護の鍵 |
| 子機の公開設定 | [`config.example.json`](../config.example.json) | `config.json` | 親機 URL、子機名、配線、モーター設定 |
| 子機の秘密値 | なし | `/etc/oiteru/unit-secret` | 子機認証用の秘密値 |

初回導入は [セットアップの説明書](setup.md) の順に進めます。
すでに稼働している機械の設定を、見本で上書きしないでください。

## 子機の主な設定

| キー | 確認すること |
| --- | --- |
| `SERVER_URL` | 子機から到達できる親機 URL。ネットワーク運用は HTTPS |
| `UNIT_NAME` / `UNIT_LOCATION` | 子機を区別する名前と設置場所 |
| `UNIT_SECRET_FILE` | 通常は `/etc/oiteru/unit-secret`。秘密値そのものは JSON に入れない |
| `MOTOR_TYPE` | `SERVO` または `STEPPER`。実物に合わせる |
| `CONTROL_METHOD` | Raspberry Pi 直結なら `RASPI_DIRECT` |
| `USE_SENSOR` / `SENSOR_PIN` | センサーの有無、BCM 方式の GPIO 番号 |
| `GREEN_LED_PIN` / `RED_LED_PIN` | LED の BCM GPIO 番号 |
| `STEPPER_PINS` | ステッピングモーターの配線順。実機で確認する |
| `STEPPER_PHASE_ORDER` / `STEPPER_BACKEND` | 回転順と制御方式。配線確認後に担当者が調整する |
| `HEARTBEAT_INTERVAL` | 状態を送る間隔（秒）。既定は 30 |
| `OFFLINE_MODE_ENABLED` | 条件を満たすときに子機だけで排出を判断するか |
| `OFFLINE_DATA_DIR` | 照合表・未送信記録の保管先。内容を削除・共有しない |

`config.json` は JSON 形式です。文字列は `"` で囲み、項目を `,` で区切ります。
読み取れるかだけを確認する場合は、子機で次を実行します。内容は表示しません。

```bash
.venv/bin/python -c "import json; json.load(open('config.json', encoding='utf-8')); print('JSON OK')"
```

子機の秘密ファイルは `sudo bash scripts/provision_unit.sh` で作成します。
通常ユーザーに戻してから子機を起動してください。
親機の `.env` を子機へコピーする必要はありません。

## 以前のウィザードを使っていた人へ

旧 `setup_config.sh` / `setup_config.ps1` は、固定 IP、古い配線、現在は使わないパスワード入力を含むため削除しました。
公開設定の見本は `config.example.json` に統一しています。
従親機用の旧 JSON も削除しました。現在の親機プログラムは DB 設定を `.env` から読みます。
