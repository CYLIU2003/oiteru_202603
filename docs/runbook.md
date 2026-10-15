# 親機 かんたん運用ガイド

親機は **hirameki-3** という Linux PC で、電源が入っていれば自動で動きます。
はじめての人がやることは「動いているか確かめる」と「止まっていたら戻す」の 2 つだけです。

## はじめての人へ（5 分で読めます）

覚えるのはこの 3 つだけです。

| ことば | 中身 |
|---|---|
| 親機の PC | `hirameki-3`（研究室の Linux PC） |
| 親機のプログラムの名前 | `oiteru-parent` |
| 動いているかの確認先 | `http://localhost:5000/api/health` |

### ① 親機に入る

研究室の Windows PC で PowerShell を開き、次の 1 行を打ちます。
初めての人は、先輩に SSH の設定をしてもらってから使います。

```powershell
ssh hirameki-3
```

### ② 動いているか確かめる

```bash
systemctl is-active oiteru-parent
```

`active` と出たら正常です。ここで終わりです。
`inactive` や `failed` と出たら ③ へ進みます。

### ③ 止まっていたら戻す

```bash
sudo systemctl restart oiteru-parent
```

パスワードを聞かれたら、hirameki-3 のログインパスワードを入れます（画面には表示されません）。
30 秒ほど待ってから、もう一度 ② をやります。

### ④ それでも戻らないとき

自分で設定を直さず、次のコマンドの結果を先輩に送ります。
送る前に、パスワードやカード番号が写っていないかだけ確認してください。

```bash
sudo journalctl -u oiteru-parent -n 50 --no-pager
```

### やらないでほしいこと

- 電源ボタンの長押しや、コンセントを抜くこと（記録が壊れることがあります。止めるときは `sudo shutdown -h now`）
- tmux などで、親機をもう 1 つ別に起動すること
- `.env` の中身やパスワードを、チャットや資料に貼ること

---

ここから下は、先輩と開発担当向けです。はじめての人は読まなくて大丈夫です。

## 仕組み（先輩・開発担当向け）

親機は systemd サービス `oiteru-parent.service` として動きます。中身は
`gunicorn --config gunicorn.conf.py wsgi:app` で、ポート 5000 を使います。

- OS を再起動すると、MySQL → カードリーダー初期化 → 親機の順に自動で起動します。
- 親機が異常終了すると、10 秒後に自動で再起動します。
- MySQL が更新などで止まっても、親機は巻き込まれて止まったままにはなりません。
  MySQL が戻れば、親機も自動で動き続けます。
- ログは journald に保存されます（`journalctl -u oiteru-parent`）。

### 初めて導入するとき・設定を更新したとき

```bash
cd ~/デスクトップ/oiteru_202603   # リポジトリの場所
git pull
sudo scripts/install_parent_service.sh
```

このスクリプトは、利用者名とパスを自動で埋め込んだ unit を `/etc/systemd/system/` に置きます。
そのあと自動起動を有効にし、親機を起動して `/api/health` の応答まで確認します。
`.env` がない、tmux 版の親機が動いているなど、問題がある場合は何も変えずに止まります。
書き込まずに内容だけ見たい場合は `--dry-run` を付けます。

### 停止

| 目的 | コマンド | 次に OS を起動したとき |
|---|---|---|
| 再起動 | `sudo systemctl restart oiteru-parent` | 自動で起動する |
| メンテナンスで一時停止 | `sudo systemctl stop oiteru-parent` | 自動で起動する |
| 長期停止（実証終了・移設） | `sudo systemctl disable --now oiteru-parent` | 起動しない |

### 保守で手動起動するとき（tmux）

画面を見ながら動かしたいときだけ、tmux を使います。
**必ず先に systemd 版を止め、終わったら戻します。** 両方を同時に動かすと、ポート 5000 が衝突します。

```bash
sudo systemctl stop oiteru-parent
scripts/tmux_oiteru.sh start parent
# 作業が終わったら
scripts/tmux_oiteru.sh stop parent
sudo systemctl start oiteru-parent
```

### 障害時の確認

まず次の 3 つで状態を確認します。

```bash
systemctl status oiteru-parent mysql --no-pager
sudo journalctl -u oiteru-parent -n 100 --no-pager
curl -s http://localhost:5000/api/health
```

| 症状 | 原因の当たり | 対処 |
|---|---|---|
| `active` なのに `/api/health` が応答しない | 一時的なハングアップ | `sudo systemctl restart oiteru-parent` |
| ログに「セキュリティ設定エラーにより起動を停止」 | `.env` の必須値が足りない（`FLASK_SECRET_KEY` が 32 文字未満など） | ログに出た項目を `.env` で直し、`restart` |
| ログに MySQL の接続エラー | MySQL の停止、または接続情報の誤り | `sudo systemctl restart mysql` を実行し、`mysql -u <MYSQL_USER> -p <MYSQL_DATABASE> -e "SELECT 1;"` で確認 |
| `Address already in use` が繰り返し出る | tmux や手動起動の残りがポート 5000 を使っている | `scripts/tmux_oiteru.sh stop parent` を実行し、`sudo ss -ltnp \| grep :5000` で確認 |
| `Start request repeated too quickly` | 設定不備のまま再起動を繰り返した | 原因を直してから `sudo systemctl reset-failed oiteru-parent` → `start` |
| 親機の NFC リーダーでカード登録できない | リーダーを認識していない | USB を挿し直し、`sudo systemctl restart oiteru-card-reader` を実行。`.venv/bin/python tools/check_nfc_reader.py` で確認 |
| 排出されたのに履歴が残っていない | 排出後に DB へ記録できなかった | 再起動しない。時刻と子機名をメモし、[operations.md](operations.md) の手順で調べる |

子機、バックアップ、補充の手順は [operations.md](operations.md) を見てください。

### 開発用 PC（Windows）について

日常の開発は Windows PC で行います。`scripts/oiteru_restart_auto.ps1` などの Windows 用スクリプトは開発用です。
本番（hirameki-3）では使いません。
