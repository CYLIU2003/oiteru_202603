# 🚀 OITELUシステム クイックスタートガイド

**最短5分でシステムを起動！**

---

## 📋 準備するもの

- ✅ Raspberry Pi（子機）
- ✅ NFCリーダー（パソリ RC-S380など）
- ✅ PC（親機サーバー用）
- ✅ Wi-Fiまたは有線ネットワーク

---

## 🎯 ステップ1: 親機サーバーを起動（3分）

### Docker使用の場合（推奨）

```bash
# プロジェクトフォルダに移動
cd oiteru_250827_restAPI

# サーバーを起動
docker-compose up -d
```

ブラウザで `http://localhost:5000` を開いて動作確認！

### Pythonで直接起動の場合

```bash
pip install -r requirements.txt
python app.py
```

---

## 🤖 ステップ2: 子機を起動（2分）

### 準備

1. プロジェクトフォルダをRaspberry Piにコピー
2. NFCリーダーをUSBポートに接続

### 起動（すべて自動！）

```bash
cd oiteru_250827_restAPI
python unit_client.py --no-gui
```

**初回起動時に自動実行される内容：**
- ✅ 仮想環境の作成（`~/.hirameki`）
- ✅ 必要なライブラリのインストール
- ✅ sudo権限の自動取得

### 親機を自動で見つける

起動後、選択肢が表示されます：

```
オプションを選択してください:
  1. そのまま起動
  2. 設定メニューを開く
  3. 親機を自動探知して起動
選択 [1-3]: 3  ← これを選択！
```

`3`を選択すると、ネットワーク上の親機を自動で探して接続します！

---

## ✅ 動作確認

1. 子機のターミナルに `✅ リーダー接続完了` と表示される
2. NFCカードを子機のリーダーにかざす
3. 親機のブラウザで利用履歴を確認

---

## 🔧 次回以降の起動

### 完全自動起動

```bash
# 子機
python unit_client.py --no-gui --auto

# 親機（Docker）
docker-compose up -d
```

設定メニューなしで即座に起動します。

---

## 📚 詳細設定

詳しい設定方法は以下のドキュメントを参照してください：

- [📖 完全マニュアル](MANUAL.md) - 詳しい手順とトラブルシューティング
- [⚙️ 設定リファレンス](SPECIFICATION.md) - 全設定項目の説明
- [🔄 変更履歴](CHANGELOG.md) - 新機能と改善点

---

## 💡 便利なコマンド

### 子機の起動オプション

```bash
# CUIモード（対話型設定）
python unit_client.py --no-gui

# 完全自動起動（設定済み）
python unit_client.py --no-gui --auto

# 親機を自動探知して起動
python unit_client.py --no-gui --find-server

# GUIモード（デスクトップ環境）
python unit_client.py
```

### 親機の管理

```bash
# サーバー起動
docker-compose up -d

# ログ確認
docker-compose logs -f

# サーバー停止
docker-compose down

# 管理画面にアクセス
# ブラウザで http://localhost:5000/admin
```

---

## 🆘 トラブル時の対処

### 親機が見つからない

```bash
# Tailscaleがインストールされているか確認
tailscale status

# 手動でサーバーURLを設定
python unit_client.py --no-gui
# → 選択肢で「2」を選んで設定メニューを開く
```

### NFCリーダーが認識されない

```bash
# USBデバイスの確認
lsusb

# udevルールの適用
sudo udevadm control --reload-rules
sudo udevadm trigger
```

### 権限エラー

**解決済み！** 最新版は自動でsudo権限を取得します。
手動で`sudo`を付ける必要はありません。

---

## 🎉 システムの特徴

- **ゼロコンフィグ**: 必要な環境は自動で作成
- **自動探知**: 親機のIPアドレスを手動設定不要
- **簡単設定**: 対話型メニューで直感的に設定
- **安全**: sudo権限やライブラリ管理を自動化
- **柔軟**: GUI/CUIどちらのモードでも動作

---

**もっと詳しく知りたい？** → [完全マニュアルを見る](MANUAL.md)
