# OITERU かんたんスタートガイド

このガイドは、`OITERU` をできるだけ迷わず起動するための手順書です。

特に子機については、`tmux` を使う方法だけに絞って説明します。

## 1. まず知っておくこと

### OITERUの役割

| 名前 | 何をするか |
| --- | --- |
| 親機 | メインサーバー。利用履歴、設定、管理画面を持つ |
| 従親機 | 親機のデータを使うサブサーバー |
| 子機 | Raspberry Piで動く端末。カード読み取りと排出を行う |

### よく使うURL

- 親機: `http://100.114.99.67:5000`
- 管理画面: `http://100.114.99.67:5000/admin`

### この取説書の前提

- レポジトリのフォルダ名は `oiteru_202603`
- 子機は `tmux` で起動する
- 子機を SSH から起動しても、`tmux` を使えばセッションを閉じても継続できる

---

## 2. フォルダの場所を確認する

まず、作業するPCやRaspberry Piで、プロジェクトの場所に移動します。

### Windows の例

```powershell
cd D:\oiteru_202603
```

### Raspberry Pi の例

```bash
cd ~/oiteru_202603
```

もし `cd` で入れない場合は、実際の保存場所に合わせて読み替えてください。

---

## 3. 親機の起動方法

親機は Windows 側で動かす想定です。

### 一番おすすめの起動方法

```powershell
cd D:\oiteru_202603
docker-compose -f docker-compose.mysql.yml up -d
```

### 起動確認

```powershell
docker ps
```

`oiteru_mysql` と Web サービスが `Up` になっていればOKです。

### 停止方法

```powershell
cd D:\oiteru_202603
docker-compose -f docker-compose.mysql.yml down
```

---

## 4. 従親機の起動方法

従親機は、親機のデータベースを参照するサブサーバーです。

### 起動方法

```powershell
cd D:\oiteru_202603
.\venv-start.ps1 sub-parent
```

### 補足

- 親機に接続できるネットワークにいる必要があります
- `config.json` や環境変数の内容が運用に合っているか確認してください

---

## 5. 子機の起動方法

ここが一番大事です。

子機は Raspberry Pi で動かし、**`tmux` を使って起動します。**

この方法なら、SSH を切断しても子機を動かし続けやすく、あとから画面に戻ってログも確認できます。

### 5-0. Windows PowerShell から Raspberry Pi に SSH 接続する

まず、Windows の PowerShell を開きます。

そのあと、次のように入力して Raspberry Pi に接続します。

```powershell
ssh pi@<ラズパイのIPアドレス>
```

例:

```powershell
ssh pi@192.168.1.50
```

Tailscale を使っている場合は、Tailscale 側のアドレスや名前でも接続できます。

```powershell
ssh pi@100.x.x.x
```

初回は次のような確認が出ることがあります。

```text
Are you sure you want to continue connecting (yes/no/[fingerprint])?
```

この場合は `yes` と入力して Enter を押します。

その後、パスワードを聞かれたら Raspberry Pi のログインパスワードを入力します。

接続に成功すると、PowerShell の表示が Raspberry Pi 側の表示に変わります。

---

### 5-1. 事前に `config.json` を確認する

最低でも次の3つを確認してください。

```json
{
    "SERVER_URL": "http://100.114.99.67:5000",
    "UNIT_NAME": "2号機",
    "UNIT_PASSWORD": "password123"
}
```

### 項目の意味

| 項目 | 意味 |
| --- | --- |
| `SERVER_URL` | 親機のURL |
| `UNIT_NAME` | 子機の名前 |
| `UNIT_PASSWORD` | 子機のパスワード |

---

### 5-2. `tmux` をインストールする

初回だけ実行します。

```bash
sudo apt update
sudo apt install -y tmux
```

---

### 5-3. `tmux` セッションを作る

```bash
tmux new -s oiteru
```

これで `oiteru` という名前の画面に入ります。

---

### 5-4. プロジェクトのフォルダへ移動する

```bash
cd ~/oiteru_202603
```

---

### 5-5. 子機を起動する

```bash
./venv-start.sh unit
```

これで子機が起動します。

子機はデフォルトで CUI モードで動きます。

---

### 5-6. `tmux` から一時的に抜ける

子機を動かしたまま画面から離れたいときは、次のキー操作をします。

```text
Ctrl + B を押してから D を押す
```

これで `tmux` を抜けても、子機はそのまま動き続けます。

---

### 5-7. もう一度子機の画面に戻る

```bash
tmux attach -t oiteru
```

---

### 5-8. 停止方法

1. 子機の画面に戻る

```bash
tmux attach -t oiteru
```

2. `Ctrl + C` を押して子機を止める

3. 必要なら `exit` で `tmux` を終了する

---

## 6. 子機が正しく動いているか確認する

### 画面上で確認すること

- NFCの状態が表示される
- 在庫情報が表示される
- エラーで止まっていない

### 管理画面で確認すること

ブラウザで以下を開きます。

```text
http://100.114.99.67:5000/admin
```

確認したいこと:

- 子機が一覧に出ている
- オンラインとして見えている
- 在庫や設定が取得できている

---

## 7. よくあるトラブル

### 親機につながらない

確認ポイント:

- `SERVER_URL` が `http://100.114.99.67:5000` になっているか
- 親機が起動しているか
- Tailscale やネットワーク接続が生きているか

### `tmux` がないと言われる

```bash
sudo apt update
sudo apt install -y tmux
```

### `duplicate session: oiteru` と出る

すでに同じ名前のセッションがあります。

既存の画面に戻るとき:

```bash
tmux attach -t oiteru
```

一覧を見るとき:

```bash
tmux ls
```

### パッケージ不足エラーが出る

たとえば `ModuleNotFoundError` が出たときは、仮想環境のセットアップを見直してください。

```bash
cd ~/oiteru_202603
./venv-start.sh unit
```

このプロジェクトでは `archive/unit_client.py` 側で仮想環境の自動セットアップも行う作りになっています。

### NFC が読めない

```bash
lsusb
```

NFC リーダーが見えているか確認してください。

### モーターが動かない

確認ポイント:

- 配線が正しいか
- `config.json` のモーター設定が合っているか
- センサーが詰まり判定を出していないか

---

## 8. 迷ったときの最短手順

### 親機

```powershell
cd D:\oiteru_202603
docker-compose -f docker-compose.mysql.yml up -d
```

### 子機

```bash
sudo apt install -y tmux
tmux new -s oiteru
cd ~/oiteru_202603
./venv-start.sh unit
```

抜けるとき:

```text
Ctrl + B -> D
```

戻るとき:

```bash
tmux attach -t oiteru
```

---

## 9. 困ったときに管理者へ伝えること

- 何をしたか
- 何が起きたか
- 画面に出たエラー文
- 子機名 (`UNIT_NAME`)

---

## 更新日

- 2026-03-06
