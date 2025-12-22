# 🔰 OITELU クイックスタートガイド

**初めて使う方向けの、ステップバイステップガイドです。**

このガイドに従えば、15分程度でシステムを動かせるようになります。

---

## 📋 始める前に確認すること

### 必要なもの

| 項目 | 親機（サーバー） | 子機（Raspberry Pi） |
|:---|:---:|:---:|
| Docker Desktop | ✅ 必須 | - |
| Python 3.7以上 | △ 開発時のみ | ✅ 必須 |
| NFCカードリーダー | △ あると便利 | ✅ 必須 |
| インターネット接続 | ✅ 初回のみ | ✅ 必須 |

### NFCカードリーダーについて

**推奨機種:** Sony PaSoRi RC-S380

その他の対応機種:
- Sony PaSoRi RC-S300
- ACR122U

---

## 🖥️ 親機のセットアップ

### ステップ1: Docker Desktopをインストール

**Windows/Mac:**
1. [Docker公式サイト](https://www.docker.com/products/docker-desktop)からダウンロード
2. インストーラーを実行
3. 再起動後、Docker Desktopを起動

**確認方法:**
```bash
docker --version
# Docker version 24.x.x のように表示されればOK
```

### ステップ2: ソースコードを取得

```bash
# GitHubからクローン
git clone https://github.com/CYLIU2003/oiteru_250827_restAPI
cd oiteru_250827_restAPI
```

### ステップ3: サーバーを起動

```bash
# dockerフォルダに移動
cd docker

# MySQL版で起動（推奨）
docker-compose -f docker-compose.mysql.yml up -d
```

**起動確認:**
- ブラウザで http://localhost:5000 を開く
- 「オイテル登録システム」の画面が表示されればOK！

### ステップ4: 管理画面にログイン

1. http://localhost:5000/admin を開く
2. パスワード: `admin` を入力
3. ダッシュボードが表示されればOK！

---

## 📡 子機のセットアップ（Raspberry Pi）

### ステップ1: Raspberry Piの準備

1. Raspberry Pi OS をインストール
2. Wi-Fiまたは有線LANでインターネットに接続
3. ターミナルを開く

### ステップ2: 必要なソフトをインストール

```bash
# システム更新
sudo apt update && sudo apt upgrade -y

# 必要なパッケージをインストール
sudo apt install -y python3-pip python3-dev libusb-1.0-0-dev git

# NFCライブラリをインストール
pip3 install nfcpy
```

### ステップ3: ソースコードを取得

```bash
git clone https://github.com/CYLIU2003/oiteru_250827_restAPI
cd oiteru_250827_restAPI
```

### ステップ4: 設定ファイルを編集

```bash
# config.jsonを編集
nano config.json
```

**最低限変更が必要な項目:**
```json
{
  "server_url": "http://親機のIPアドレス:5000",
  "unit_name": "子機1号機",
  "unit_password": "任意のパスワード"
}
```

> 💡 **親機のIPアドレスの調べ方:**
> - Windows: `ipconfig` コマンド
> - Mac/Linux: `ip addr` または `ifconfig` コマンド

### ステップ5: 子機を起動

```bash
sudo python3 unit.py
```

**起動確認:**
- 「親機に接続しました」と表示されればOK！
- NFCカードをかざして反応するか確認

---

## 🎯 基本的な使い方

### ユーザー登録（親機で行う）

1. http://localhost:5000 を開く
2. 「利用者登録」をクリック
3. NFCカードをリーダーにかざす
4. 名前などを入力して「登録」

### お菓子を取得（子機で行う）

1. 子機が起動していることを確認
2. NFCカードをかざす
3. お菓子が排出される
4. 利用履歴が自動で記録される

### 管理画面でできること

| 機能 | 説明 |
|:---|:---|
| 👥 利用者一覧 | 登録ユーザーの確認・編集 |
| 📦 子機一覧 | 子機の接続状態・在庫確認 |
| 📋 利用履歴 | 排出成功した履歴を表示 |
| 📊 グラフ表示 | 時間別・日別の利用状況 |
| ⚙️ システム設定 | 自動登録モードなど |

---

## ⭐ 自動登録モードを使う

**自動登録モード**を有効にすると、未登録のカードがタッチされても自動でユーザー登録されます。

### 設定方法

1. 管理画面（http://localhost:5000/admin）にログイン
2. 「⚙️ システム設定」をクリック
3. 「自動登録モード」を「有効」に変更
4. 「保存」をクリック

### 動作の流れ

```
未登録カードをタッチ
    ↓
自動でユーザー登録（初期残数: 2個）
    ↓
即座にお菓子を排出
    ↓
履歴に「自動登録」と記録
```

---

## ❓ よくある質問

### Q: 親機にアクセスできない

**確認ポイント:**
1. Dockerが起動しているか
2. `docker-compose ps` でコンテナが動いているか
3. ファイアウォールでポート5000がブロックされていないか

**解決方法:**
```bash
# ログを確認
docker-compose logs

# 再起動
docker-compose restart
```

### Q: 子機が親機に接続できない

**確認ポイント:**
1. 親機と子機が同じネットワークにあるか
2. `config.json`のIPアドレスが正しいか
3. 親機が起動しているか

**確認方法:**
```bash
# 親機にpingを打つ
ping 親機のIPアドレス
```

### Q: NFCカードが読み取れない

**確認ポイント:**
1. カードリーダーがUSBで接続されているか
2. `lsusb`でリーダーが認識されているか
3. `nfcpy`がインストールされているか

**確認方法:**
```bash
# リーダーが認識されているか確認
lsusb | grep -i sony

# nfcpyで確認
python3 -c "import nfc; print(nfc.ContactlessFrontend('usb'))"
```

---

## 🚀 次のステップ

システムが動いたら、以下の機能も試してみてください：

1. **利用状況の可視化** - グラフで利用傾向を確認
2. **データのバックアップ** - Excelファイルで保存
3. **複数の子機を追加** - 別のRaspberry Piを接続

**さらに詳しく知りたい場合:**
→ [REFERENCE.md](REFERENCE.md) を参照してください

---

## 📞 サポート

問題が解決しない場合は、以下の情報を添えてお問い合わせください：

1. エラーメッセージのスクリーンショット
2. `docker-compose logs` の出力
3. 使用している機器のリスト

---

**最終更新: 2025年12月22日**
