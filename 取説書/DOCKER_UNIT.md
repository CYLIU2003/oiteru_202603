# 子機クライアント Docker対応ガイド

## 📦 概要

子機クライアントをDockerコンテナで実行できるようになりました。
これにより、環境構築や依存関係の管理が不要になります。

**注意**: 初回ビルドは10-15分程度かかります（パッケージのコンパイルが必要なため）。
通常起動（仮想環境自動作成）の方が起動は速いですが、Docker起動は環境の一貫性が保証されます。

---

## 🚀 クイックスタート

### 方法1: 起動スクリプトを使用（推奨）

```bash
./start_unit.sh
```

起動スクリプトを実行すると、以下の選択肢が表示されます：
1. **通常起動** - 仮想環境を自動作成して実行
2. **Docker起動** - コンテナで実行
3. キャンセル

### 方法2: docker-composeコマンドを直接使用

```bash
# バックグラウンドで起動
docker-compose -f docker-compose.unit.yml up -d

# ログを表示しながら起動
docker-compose -f docker-compose.unit.yml up

# 停止
docker-compose -f docker-compose.unit.yml down

# ログ確認
docker-compose -f docker-compose.unit.yml logs -f
```

---

## 📋 前提条件

### Dockerのインストール

```bash
# Dockerをインストール
curl -fsSL https://get.docker.com | sh

# 現在のユーザーをdockerグループに追加
sudo usermod -aG docker $USER

# 再ログインまたは以下を実行
newgrp docker

# docker-composeをインストール（必要な場合）
sudo apt-get install docker-compose
```

---

## ⚙️ 設定

### 初回設定

Docker起動前に設定ファイルを作成します：

```bash
# 通常起動で設定を作成
python unit_client.py --no-gui

# 設定メニューで以下を設定:
# - サーバーURL
# - 子機名
# - その他のハードウェア設定
```

設定は `config.json` に保存され、Dockerコンテナでも使用されます。

### 設定の確認・変更

```bash
# 設定ファイルを編集
nano config.json

# または通常起動で設定変更
python unit_client.py --no-gui
# → 「2. 設定メニューを開く」を選択
```

---

## 🔧 Docker起動の特徴

### メリット

- ✅ **環境構築不要**: 依存ライブラリを自動インストール
- ✅ **一貫性**: どのRaspberry Piでも同じ環境で動作
- ✅ **隔離性**: システムに影響を与えない
- ✅ **自動起動**: `restart: unless-stopped`で自動再起動

### デメリット

- ⚠️ **特権モード必要**: GPIO/USB/I2Cアクセスのため`privileged: true`
- ⚠️ **初回ビルド時間**: イメージビルドに数分かかる（初回のみ）

---

## 🛠️ トラブルシューティング

### NFCリーダーが認識されない

```bash
# USBデバイスを確認
lsusb

# コンテナを再起動
docker-compose -f docker-compose.unit.yml restart

# udevルールを適用（ホスト側）
sudo udevadm control --reload-rules
sudo udevadm trigger
```

### GPIO/I2Cが使えない

```bash
# I2Cが有効か確認
sudo raspi-config
# → Interface Options → I2C → Enable

# 権限を確認
ls -l /dev/i2c-1
ls -l /dev/gpiomem

# コンテナを特権モードで再起動
docker-compose -f docker-compose.unit.yml down
docker-compose -f docker-compose.unit.yml up -d
```

### コンテナが起動しない

```bash
# ログを確認
docker-compose -f docker-compose.unit.yml logs

# イメージを再ビルド
docker-compose -f docker-compose.unit.yml build --no-cache
docker-compose -f docker-compose.unit.yml up -d
```

---

## 📊 通常起動 vs Docker起動

| 項目 | 通常起動 | Docker起動 |
|------|----------|------------|
| 環境構築 | 自動（初回のみ） | 不要 |
| 起動速度 | 速い | やや遅い |
| 隔離性 | 低い | 高い |
| 管理 | 簡単 | やや複雑 |
| 推奨用途 | 開発・テスト | 本番運用 |

---

## 💡 推奨される使い方

### 開発・テスト時

```bash
# 通常起動で設定を調整
python unit_client.py --no-gui
```

### 本番運用時

```bash
# Docker起動で安定運用
./start_unit.sh
# → 「2. Docker起動」を選択
# → 「1. 起動（バックグラウンド）」を選択
```

### 自動起動設定（システム起動時）

```bash
# systemdサービスファイルを作成
sudo nano /etc/systemd/system/oiteru-unit.service
```

```ini
[Unit]
Description=OITERU Unit Client
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/hirameki-2/Desktop/oiteru_250827_restAPI
ExecStart=/usr/bin/docker-compose -f docker-compose.unit.yml up -d
ExecStop=/usr/bin/docker-compose -f docker-compose.unit.yml down
User=hirameki-2

[Install]
WantedBy=multi-user.target
```

```bash
# サービスを有効化
sudo systemctl daemon-reload
sudo systemctl enable oiteru-unit.service
sudo systemctl start oiteru-unit.service

# ステータス確認
sudo systemctl status oiteru-unit.service
```

---

## 📚 関連ドキュメント

- [メインREADME](../README.md)
- [完全マニュアル](MANUAL.md)
- [クイックスタート](QUICKSTART.md)
