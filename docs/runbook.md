# 親機 かんたん運用ガイド

親機は **hirameki-3** という Linux PC で、電源が入っていれば自動で動きます。
はじめての人がやることは「動いているか確かめる」と「止まっていたら戻す」の 2 つだけです。

## はじめての人へ（5 分で読めます）

覚えるのはこの 2 つだけです。

| ことば | 中身 |
|---|---|
| 親機の PC | `hirameki-3`（研究室の Linux PC） |
| 親機を見る・直すコマンド | `scripts/parent.sh` |

### ① 親機に入る

研究室の Windows PC で PowerShell を開き、次の 2 行を打ちます。
初めての人は、先輩に SSH の設定をしてもらってから使います。

```powershell
ssh hirameki-3
cd ~/デスクトップ/oiteru_202603
```

### ② 動いているか確かめる

```bash
scripts/parent.sh status
```

最後に「問題ありません。」と出たら正常です。ここで終わりです。
`[NG]` が出たら ③ へ進みます。

### ③ 止まっていたら戻す

```bash
scripts/parent.sh restart
```

パスワードを聞かれたら、hirameki-3 のログインパスワードを入れます（打っても画面には表示されません）。
「親機は応答しています。」と出たら直りました。もう一度 ② をやって確かめます。

### ④ それでも戻らないとき

自分で設定を直さず、次のコマンドの画面を先輩に送ります（Ctrl-c で終了できます）。
送る前に、パスワードやカード番号が写っていないかだけ確認してください。

```bash
scripts/parent.sh logs
```

### 親機が止まっている間、子機はどうなる？

子機は **スタンドアロンモード** に切り替わり、少しの間だけ子機だけで排出を続けます。
親機が戻ると、その間の記録は自動で親機に送られます。後輩が何か操作する必要はありません。

- 使えるのは、親機が止まる前に「使ってよい」と確認できていたカードだけです（1 枚につき 1 個まで）
- 親機が 3 日以上戻らないと、子機も排出を止めます（安全のため）
- 親機が戻ったら、管理画面の履歴に「オフライン利用を同期」と出ていれば完了です
- 「要確認」と付いた記録は、オフライン中に残数を超えて出た分です。先輩に伝えてください

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
- MySQL が更新などで止まっても、親機は巻き込まれて止まったままにはなりません
  （2026-09-01 に MySQL の自動更新で親機が約 5 日止まった事例への対策です）。
- ログは journald に保存されます（`scripts/parent.sh logs`）。

### 初めて導入するとき・更新したとき

```bash
cd ~/デスクトップ/oiteru_202603
git pull
scripts/parent.sh install
```

`sudo` は付けません。必要なところでパスワードを聞かれます。

- 利用者名とパスを自動で埋め込んだ unit を `/etc/systemd/system/` に置きます。前の unit は `.bak.<時刻>` で残します。
- tmux で親機が動いていれば止めてから、systemd 版を起動します。
- `.env` や `.venv` がないときは、何も変えずに止まります。
- 書き込まずに内容だけ見たいときは `scripts/parent.sh install --dry-run` を使います。

### 停止

| 目的 | コマンド | 次に OS を起動したとき |
|---|---|---|
| 再起動 | `scripts/parent.sh restart` | 自動で起動する |
| メンテナンスで一時停止 | `sudo systemctl stop oiteru-parent` | 自動で起動する |
| 長期停止（実証終了・移設） | `sudo systemctl disable --now oiteru-parent` | 起動しない |

### 保守で手動起動するとき（tmux）

画面を見ながら動かしたいときだけ、tmux を使います。
**先に systemd 版を止め、終わったら戻します。** systemd 版が動いている間は、tmux 版は起動を拒否します。

```bash
sudo systemctl stop oiteru-parent
scripts/tmux_oiteru.sh start parent
# 作業が終わったら
scripts/tmux_oiteru.sh stop parent
sudo systemctl start oiteru-parent
```

### 障害時の対処表

| 症状（`scripts/parent.sh logs` に出るもの） | 原因の当たり | 対処 |
|---|---|---|
| 動いているのに応答しない | 一時的なハングアップ | `scripts/parent.sh restart` |
| 「セキュリティ設定エラーにより起動を停止」 | `.env` の必須値が足りない（`FLASK_SECRET_KEY` が 32 文字未満など） | ログに出た項目を `.env` で直して `restart` |
| MySQL の接続エラー | MySQL の停止、または接続情報の誤り | `sudo systemctl restart mysql` を実行し、`mysql -u <MYSQL_USER> -p <MYSQL_DATABASE> -e "SELECT 1;"` で確認 |
| `Address already in use` | 別の親機がポート 5000 を使っている | `scripts/tmux_oiteru.sh stop parent` を実行し、`sudo ss -ltnp \| grep :5000` で確認 |
| `Start request repeated too quickly` | 設定不備のまま再起動を繰り返した | 原因を直してから `sudo systemctl reset-failed oiteru-parent` → `restart` |
| 親機の NFC リーダーでカード登録できない | リーダーを認識していない | USB を挿し直して `sudo systemctl restart oiteru-card-reader`。`.venv/bin/python tools/check_nfc_reader.py` で確認 |
| 排出されたのに履歴が残っていない | 排出後に DB へ記録できなかった | 再起動しない。時刻と子機名をメモし、[operations.md](operations.md) の手順で調べる |

子機、バックアップ、補充の手順は [operations.md](operations.md) を見てください。

### 開発用 PC（Windows）について

日常の開発は Windows PC で行います。Windows 用スクリプトは `scripts/windows/` にあり、本番（hirameki-3）では使いません。
