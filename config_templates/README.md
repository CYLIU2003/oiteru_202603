# OITERU 設定テンプレート

このフォルダには、子機・従親機の設定テンプレートがあります。

## 使い方

### 方法1: テンプレートをコピーして編集

```bash
# 子機の場合
cp config_unit.template.json ../config.json
nano ../config.json  # ★マークの項目を編集

# 従親機の場合
cp config_sub_parent.template.json ../config.json
nano ../config.json  # ★マークの項目を編集
```

### 方法2: ウィザードを使う（おすすめ）

```bash
# Linux/Raspberry Pi
./scripts/setup_config.sh

# Windows
.\scripts\setup_config.ps1
```

### 方法3: ワンライナー（上級者向け）

```bash
# 子機を設定（名前、場所、パスワードを指定）
./scripts/setup_config.sh unit "3号機" "7号館1階" "password123"

# 従親機を設定
./scripts/setup_config.sh sub-parent "従親機B" "別館2階"
```

## テンプレート一覧

| ファイル | 用途 |
|---------|------|
| `config_unit.template.json` | 子機（ラズパイ）用 |
| `config_sub_parent.template.json` | 従親機用 |

## 編集が必要な項目

### 子機の場合
- `UNIT_NAME`: 子機の名前（例: 3号機）
- `UNIT_PASSWORD`: パスワード
- `UNIT_LOCATION`: 設置場所（例: 7号館1階）

### 従親機の場合
- `SERVER_NAME`: サーバー名（例: 従親機A）
- `SERVER_LOCATION`: 設置場所（例: 別館1階）

## 親機のIPアドレス

デフォルトは `100.114.99.67` (Tailscale) です。
変更する場合は `SERVER_URL` または `MYSQL_HOST` を編集してください。
