# OITERU クイックスタート

親機は、起動スクリプトを tmux 内で実行します。tmux から離脱しても親機は動き続けます。

## Linux 親機

初回だけ、`.env` を作成して MySQL の接続情報・管理者パスワードを設定します。

```bash
cp .env.example .env
nano .env
```

次に MySQL を準備します。MySQL が未導入の場合は `--install` を付けます。

```bash
scripts/setup_local_mysql.sh --install
```

親機を tmux で起動します。

```bash
tmux new -s oiteru-parent
./scripts/start_oiteru.sh
```

`start_oiteru.sh` の表示に従って、カードリーダー・Docker・親機の確認を進めます。起動後、tmux から抜けるには `Ctrl-b`、続けて `d` を押します。

再び画面を開くときは次を実行します。

```bash
tmux attach -t oiteru-parent
```

tmux セッションの一覧は次で確認できます。

```bash
tmux ls
```

親機を停止するときは、tmux へ入って `Ctrl-c` を押すか、次を実行します。

```bash
tmux kill-session -t oiteru-parent
```

## Windows 親機

PowerShell を開き、リポジトリ直下で次を実行します。

```powershell
.\scripts\start_parent.ps1
```

このスクリプトは仮想環境と MySQL 接続を確認して親機を起動します。Windows 側は tmux 運用の対象外です。

## BIOS 風 CUI について

BIOS 風の対話画面は、親機起動スクリプトではなくランチャーです。

```bash
cd scripts
./launcher.sh
```

表示された選択肢で `2` を選ぶと CUI 版ランチャーが開きます。これは親機・子機・Docker などを選択する補助画面です。学内実証の親機を通常起動する場合は、上記の `start_oiteru.sh` を tmux で実行してください。

## 起動確認

親機の起動後、別のシェルで確認します。

```bash
curl http://127.0.0.1:5000/api/health
```

`"status":"ok"` が返れば起動しています。管理画面は `http://127.0.0.1:5000/admin`、HTTPS 運用では組織で割り当てた親機 URL の `/admin` を開きます。

詳細な子機登録、運用、障害対応は [docs/operations.md](docs/operations.md) を参照してください。

最終更新: 2026-08-23
