# 開発の第一歩：コードを書く前に、テストを動かす

**自分の PC にプロジェクトをコピーし、テストの成功を見るところまで進めます。**
実機・カードリーダー・MySQL・管理者パスワードは、この練習には不要です。
研究室の稼働中の親機ではなく、自分の開発用 PC を使ってください。

## 0. 必要なものを準備する

| 必要なもの | 何に使うか | 入手先 |
| --- | --- | --- |
| Git | GitHub からプログラムをコピーする | [Git 公式](https://git-scm.com/downloads) |
| Python | プログラムとテストを実行する | [Python 公式](https://www.python.org/downloads/) |
| インターネット接続 | プログラムと必要なパッケージを取得する | 学内等で利用できる接続 |

Python は **3.12 以上**を使います（CI＝GitHub の自動チェックは 3.12。3.12・3.13・3.14 で動作を確認済み）。
すでに 3.12 以上が入っていれば、新しく入れる必要はありません。既存の Python は消さないでください。
Windows のインストーラーでは、`Add python.exe to PATH` がある場合はチェックを付けます。
[公式の Windows インストール説明](https://docs.python.org/3.12/using/windows.html#installation-steps) も参照できます。

### コマンドを入力する画面を開く

- Windows：スタートメニューで `PowerShell` を検索して開く。管理者として開く必要はありません。
- macOS：アプリケーションの「ユーティリティ」から「ターミナル」を開く。
- Linux：アプリ一覧から「端末」または「ターミナル」を開く。

この画面に、以下の枠の中のコマンドを **1 行ずつ**貼り、Enter を押します。
行頭の `PS C:\...>` や `$` は入力を待っている印です。以下のコマンドに付け足す必要はありません。
文字が流れた後、入力待ちの行が戻ったら次へ進みます。エラーが出た行では止まってください。

## 1. Git と Python が使えるか確認する

**Windows（PowerShell）：**

```powershell
git --version
python --version
```

**macOS / Linux（ターミナル）：**

```bash
git --version
python3 --version
```

**できた目印：** `git version ...` と、`Python 3.12.x`・`Python 3.13.x`・`Python 3.14.x` のどれかが出ます。

| `Python ...` の表示 | すること |
| --- | --- |
| 3.12 以上 | そのまま手順 2 へ進む |
| 3.11 以下 | 公式サイトから 3.12 以上を追加で入れ、PowerShell を開き直してもう一度確認する |
| 見つからない・ストア画面が開く | インストールを確認し、PowerShell を開き直す |

Windows で `python --version` が古いままでも、`py -0` の一覧に `3.12` 以上があれば使えます。
その場合は手順 3 の `python -m venv .venv` を `py -3.12 -m venv .venv` に置き換えます（`3.12` は一覧にある番号）。

## 2. プロジェクトをコピーする

`cd` はフォルダを移動する操作、`git clone` は GitHub からコピーする操作です。
練習用に、ホームフォルダの `oiteru-practice` という新しいフォルダを使います。

**Windows：**

```powershell
cd $HOME
git clone https://github.com/CYLIU2003/oiteru_202603.git oiteru-practice
cd oiteru-practice
Get-ChildItem
```

**macOS / Linux：**

```bash
cd ~
git clone https://github.com/CYLIU2003/oiteru_202603.git oiteru-practice
cd oiteru-practice
ls
```

**できた目印：** `README.md`、`requirements-dev.txt`、`tests` などが一覧に出ます。
`oiteru-practice` がすでに存在すると出たら削除せず、先輩と既存のフォルダを使うか確認します。

## 3. このプロジェクト専用の Python 環境を作る

`.venv` は、必要なパッケージを他のプロジェクトと分けて入れる場所です。
この手順では毎回 `.venv` 内の Python を指定するので、「環境を有効化する」操作は不要です。

**Windows：**

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

**macOS / Linux：**

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
```

初回はダウンロードに 1〜3 分ほどかかります。入力待ちに戻るまで待ってください。
**できた目印：** インストールの最後に `ERROR` がなく、入力待ちに戻ります。
最後に `[notice] A new release of pip is available` と出ることがありますが、無視して構いません（案内されたコマンドも実行不要です）。
すでに導入済みなら `Requirement already satisfied` と出ることもあります。
Ubuntu などで `venv` がないと案内されたら、先輩と `python3-venv` の導入を確認します。

## 4. テストを動かす

**Windows：**

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

**macOS / Linux：**

```bash
.venv/bin/python -m pytest -q
```

**できた目印：** 最後の集計に `passed` と表示され、`failed` や `ERROR` がありません。
件数は改修で変わるので、決まった数である必要はありません。

| 表示 | 意味 |
| --- | --- |
| `.` / `passed` | テスト成功 |
| `s` / `skipped` | DB や特定 OS が必要なテストを今回は実行していない |
| `F` / `failed` | 期待した動作と違った |
| `E` / `ERROR` | 読み込みや準備中などに問題があった |

MySQL は入れなくて大丈夫です。MySQL を使うテストは通常スキップされます。
ハードウェアのテストはモック（実機の代役）などで動きます。
この成功はプログラムの確認であり、実物のモーターや DB の動作確認ではありません。

## 5. 今日はここで終了。次に開くとき

テストが成功したら、ターミナルを閉じて構いません。次回はコピーや環境作成をやり直しません。

**Windows：**

```powershell
cd "$HOME\oiteru-practice"
.\.venv\Scripts\python.exe -m pytest -q
```

**macOS / Linux：**

```bash
cd ~/oiteru-practice
.venv/bin/python -m pytest -q
```

自分の変更がある場合は、先に `git status` で確認します。
更新やブランチの操作は、最初は先輩と一緒に行ってください。

## 止まったときは、失敗した行から確認する

| 症状 | 確認すること |
| --- | --- |
| `requirements-dev.txt` が見つからない | 今いるフォルダに README があるか。手順 2 の `cd` ができたか |
| `.venv` の Python が見つからない | 手順 3 の環境作成が終わったか。Windows 用と Linux 用を混ぜていないか |
| `No module named pytest` | 同じ `.venv` の Python でパッケージを入れたか |
| パッケージのダウンロードが失敗する | ネットワークと最初に出たエラー。設定を推測で変えずに共有する |
| テストが失敗する | 実行したコマンドと最後の集計、失敗したテスト名を控える |

[困ったときのメモ](../QUICK_START.md#help) に「どの手順の何行目か」も添えて担当者へ伝えます。
`.env` の内容やカード番号を送る必要はありません。

## 次にコードを直すとき

[AGENTS.md](../AGENTS.md) の責務分離・DB・認証・ログのルールを先に確認してください。
SQL は repository、業務の判断は service に置き、route や template から DB を直接操作しません。
管理画面と `/api/v1/admin/*` は認証を必要とし、利用者向け画面はログイン不要のまま保ちます。

CI と同じ構文・未定義名のチェックは、次のコマンドです。

```bash
.venv/bin/python -m ruff check --select E9,F63,F7,F82 app tests unit server.py db_server.py unit.py stepper_driver.py wsgi.py
git diff --check
```

Windows では、先頭の Python を `.\.venv\Scripts\python.exe` に置き換えます。
MySQL 統合テストは、開発用 DB に対して `OITERU_TEST_MYSQL=1` を設定して行います。
名前が `_test` で終わる DB を毎回削除・再作成するため、本番には接続しません。

関連資料：[初回セットアップ](setup.md) / [設定ファイル](configuration.md) / [画面の役割](user_flow.md)。
