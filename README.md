# OITERU (オイテル) システム

**NFCカードで「生理用品(ナプキン)」を管理するスマートIoTシステム**

社員証や学生証などのICカードをかざすだけで、自動で生理用品(ナプキン)を排出し、利用履歴を記録します。

---

## 📁 ファイル構成（これだけ覚えればOK！）

```
oiteru_202603/
│
├── 🗄️  db_server.py     ← 標準の親機エントリポイント（MySQL）
├── 🖥️  server.py        ← legacy 親機エントリポイント（SQLite/互換用）
├── 📡  unit.py          ← 子機を起動するファイル（Raspberry Pi用）
│
├── 📄  db_adapter.py    ← (内部用) データベース処理
├── ⚙️  config.example.json ← 子機設定テンプレート
├── ⚙️  .env.example     ← サーバー設定のテンプレート
│
├── 📁  docker/          ← Docker関連ファイル
├── 📁  docs/            ← 運用資料・引き継ぎ資料
├── 📁  scripts/         ← 便利スクリプト集
├── 📁  tools/           ← テスト・診断ツール
├── 📁  templates/       ← Web画面のHTML
├── 📁  static/          ← CSS・画像
│
└── 📚  取説書/          ← ドキュメント
    ├── QUICKSTART.md    ← 🔰 初心者はここから！
    └── REFERENCE.md     ← 📖 全機能の詳細説明
```

---

## 標準構成

- 親機: `db_server.py`
- DB: `MySQL 8 (InnoDB)`
- Docker: `docker-compose.mysql.yml`
- `server.py` は legacy 互換経路で、新規開発対象外です

## 標準起動手順

この README の標準経路は `MySQL + .env + db_server.py` の 1 本です。
`server.py + SQLite` は既存検証用の legacy 経路として扱います。

## ⚡ 5ステップで始める

### ステップ1: `.env` を作成

```bash
cp .env.example .env
```

最低限、以下を必ず変更してください。

- `FLASK_SECRET_KEY`
- `OITERU_ADMIN_PASSWORD`
- `MYSQL_PASSWORD`
- `MYSQL_ROOT_PASSWORD`

`OITERU_STRICT_SECURITY=true` の場合、既定値のままでは起動時に停止します。

### ステップ2: 子機設定を作成

```bash
cp config.example.json config.json
```

最低限、以下を子機ごとに変更してください。

- `SERVER_URL`
- `UNIT_NAME`
- `UNIT_PASSWORD`

### ステップ3: 親機を起動

```bash
# Dockerで起動（推奨・標準）
docker compose -f docker-compose.mysql.yml up -d

# または直接起動（MySQL接続）
python db_server.py

# venv経由でも MySQL が既定
./venv-start.sh parent-mysql
```

### ステップ4: 子機を起動（Raspberry Pi）

```bash
# 仮想環境で起動（推奨）
./venv-start.sh unit

# または直接起動（CUIモード）
sudo python unit.py --no-gui
```

#### 4-A. ステッピングモーター (28BYJ-48 + ULN2003AN) を使う場合

`main_stepping_branch` では `RpiMotorLib` を標準バックエンドとして使い、
GPIO 直結はフォールバックとして残しています。子機初回セットアップ時に
`archive/unit_client.py` の自動 venv セットアップが
`RpiMotorLib` も `pip install` するように更新されています。

```bash
# 既定の requirements-client.txt を使う場合
pip install -r requirements-client.txt
# あるいは手動で
pip install RpiMotorLib
```

| ULN2003AN 入力 | Raspberry Pi BCM GPIO | 設定キー `STEPPER_PINS` 順 |
|---|---|---:|
| IN1 |  GPIO5 | 0 |
| IN2 |  GPIO6 | 1 |
| IN3 | GPIO13 | 2 |
| IN4 | GPIO19 | 3 |

設定の既定値 (`config.example.json`):

```json
"STEPPER_PINS": [5, 6, 13, 19],
"STEPPER_PHASE_ORDER": [0, 2, 1, 3],
"STEPPER_DRIVE_MODE": "full",
"STEPPER_STEP_DELAY": 0.01,
"STEPPER_TEST_STEPS": 256,
"STEPPER_BACKEND": "auto"
```

| キー | 意味 |
|---|---|
| `STEPPER_BACKEND` | `auto` (既定) / `library` / `gpio` のいずれか。`auto` は `RpiMotorLib` 優先・失敗時 GPIO フォールバック。 |
| `STEPPER_DRIVE_MODE` | `full` (2相励磁, 2048 step/rev) / `half` (8 ビート, 4096 step/rev) / `wave` (1相励磁, 2048 step/rev) |
| `STEPPER_PHASE_ORDER` | IN1..IN4 をどの順で励磁するか。CUI の "15. 配線順スキャン" で探索可。 |
| `STEPPER_STEP_DELAY` | 1 ステップ間の待ち秒。28BYJ-48 は 0.01s 以下でも脱調しやすい。 |

##### バックエンド切替ログ

NFC 排出時と CUI テスト時は必ず以下のようにバックエンドをログに出します。

```text
[STEPPER] backend=RpiMotorLib pins(IN1-4)=[5, 6, 13, 19] phase_order=[0, 2, 1, 3] mode=full steps=512 wait=0.0100s reverse=False
[STEPPER] start (nfc-dispense)
[STEPPER] done (nfc-dispense)
[STEPPER] coils off
```

GPIO フォールバック時は:

```text
[STEPPER] backend=GPIO pins(IN1-4)=[5, 6, 13, 19] ...
```

##### 単体テスト

ライブラリ導入後、`unit.py` を起動する前に最小確認ができます。

```python
from stepper_driver import run_stepper
# 任意のGPIOモックを渡して dry-run
result = run_stepper(None, {"STEPPER_BACKEND": "gpio", "STEPPER_PINS": [5, 6, 13, 19]},
                     steps=256, label="smoke")
print(result)
```

実機では CUI メニューの **22. ライブラリ正方向テスト** で確認できます。

### ステップ5: 管理画面にアクセス

ブラウザで http://localhost:5000/admin を開き、`.env` の `OITERU_ADMIN_PASSWORD` でログインします。

## legacy / 互換構成

- `server.py + SQLite` は既存データ確認や互換検証向けです
- 新規セットアップ、運用手順、障害切り分けは `db_server.py + MySQL` を前提にしてください
- `config.json`、`*.sqlite3`、`*.log` はローカル生成物として Git 管理しません
- `venv-start.sh` / `venv-start.ps1` は引数なしなら MySQL 親機を起動します

---

## 📚 ドキュメント

| 対象 | ドキュメント | 説明 |
|:---:|:---|:---|
| 🔰 | [取説書/QUICKSTART.md](取説書/QUICKSTART.md) | **初心者向け** - まずはここから |
| 📖 | [取説書/REFERENCE.md](取説書/REFERENCE.md) | **上級者向け** - 全機能の詳細 |
| 🛠️ | [docs/operations.md](docs/operations.md) | **運用・引き継ぎ向け** - 日常運用と障害対応 |

---

## ✨ 主な機能

- **自動登録モード**: 未登録カードも自動でユーザー登録
- **複数親機対応**: 複数サーバーで同じDBを共有
- **Web管理画面**: ブラウザから利用状況を確認
- **Docker対応**: MySQL込みで環境構築

---

## 運用上の注意

- 標準DBは `MySQL 8 (InnoDB)` です
- `config.json`、`*.sqlite3`、`*.log` は Git 管理しません
- 管理者パスワードと Flask secret は必ず `.env` から設定してください
- `server.py + SQLite` は legacy 互換経路です。標準構成では使いません

---

**最終更新: 2026年3月13日**
