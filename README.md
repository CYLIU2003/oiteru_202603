<div align="center">
  <br>
  <img src="static/img/logo20250506.png" alt="OITERU ロゴ" width="320">
  <br><br>

  # OITERU｜学内向け生理用品配布システム

  **カードをかざす → 生理用品が出る → 記録が残る**

  <br>

  ![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
  ![Flask](https://img.shields.io/badge/Flask-Web_API-000000?logo=flask&logoColor=white)
  ![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?logo=mysql&logoColor=white)
  ![Raspberry Pi](https://img.shields.io/badge/Raspberry_Pi-Unit-C51A4A?logo=raspberrypi&logoColor=white)
  ![tmux](https://img.shields.io/badge/tmux-standard-1BB91F?logo=gnubash&logoColor=white)

  <br>
</div>

---

## 目次

1. [これは何のプロジェクト？](#1-これは何のプロジェクト)
2. [OITERU って何？（ざっくり）](#2-oiteru-って何ざっくり)
3. [はじめに — ターミナルって何？](#3-はじめに--ターミナルって何)
4. [必要なものと、それぞれの役割](#4-必要なものとそれぞれの役割)
5. [はじめての準備（全員共通）](#5-はじめての準備全員共通)
6. [親機を起動する（全6ステップ）](#6-親機を起動する全6ステップ)
7. [子機を起動する（全4ステップ）](#7-子機を起動する全4ステップ)
8. [管理画面を見てみよう](#8-管理画面を見てみよう)
9. [tmux の超基本](#9-tmux-の超基本)
10. [ディレクトリ構成（興味がある人だけ）](#10-ディレクトリ構成興味がある人だけ)
11. [「あれ？動かない」となったとき](#11-あれ動かないとなったとき)
12. [開発に参加したい人へ](#12-開発に参加したい人へ)
13. [絶対に守ること](#13-絶対に守ること)
14. [English Summary](#14-english-summary)

---

## 1. これは何のプロジェクト？

### 概要

**オイテル** は、大学の中で生理用品を必要とする学生が、必要なときに受け取れるようにするための配布システムです。

ただ「箱に物品を置いておく」だけではなく、以下の 3 つをセットで設計・開発しています。

| 要素 | 内容 |
|------|------|
| **配布装置（ハードウェア）** | Raspberry Pi ＋ モーター ＋ NFC リーダー。カードをかざすと自動で出てくる装置 |
| **制御システム（ソフトウェア）** | 誰がいつ使ったかを記録し、1日の利用回数制限をする管理システム |
| **運用ルール（現場運用）** | 補充のしやすさ、保守のしやすさ、管理者の負荷を考えた設計 |

利用者が心理的な負担を感じにくく、管理者側も補充・運用しやすい仕組みを目指しました。

---

### 背景 — なぜつくるのか

大学生活の中で、生理用品を急に必要とする場面はあります。しかし、学内でいつでも入手できる環境は十分とは限らず、利用者にとって心理的・時間的な負担が生じる可能性があります。

そこで、**学内に設置可能な配布端末** を開発し、必要な人が自然に利用できる環境を整えることを目指しました。

このプロジェクトでは、社会課題に対して **ハードウェア・ソフトウェア・運用設計を組み合わせ**、実際に使われることを重視したシステム開発に取り組んでいます。

---

### 主な機能

- **NFC カードでかざすだけ** — 学生証などをかざすと生理用品が 1 つ出てくる
- **1日の利用回数制限** — 同じカードで何度も取れないように制御
- **管理画面** — ブラウザで在庫確認・利用履歴の確認ができる
- **子機の遠隔監視** — 各端末が「生きているか」を定期的に親機へ報告
- **補充・保守を考えた設計** — 管理者が補充しやすく、利用者が迷わず使える
- **テスト運用で改善可能** — 実際に使って出てきた課題を段階的に直せる構造

---

### 技術的なポイント

| 軸 | 内容 |
|----|------|
| **配布機構の安定性** | 生理用品を詰まらせず、一定量ずつ取り出せる構造を検討 |
| **制御システムの実装** | Raspberry Pi を中心に、モータ制御や端末動作の制御を設計 |
| **実運用を想定した設計** | 管理者が補充しやすく、利用者が迷わず使える設計 |
| **改善可能なプロトタイプ** | テスト運用を通じて機構・制御・運用面の課題を洗い出し改善できる構成 |

---

### 担当・取り組み（プロジェクト実績）

このプロジェクトでは、企画段階から開発・運用検討まで幅広く関わりました。

- 学内課題の整理とシステムコンセプトの設計
- 配布端末の仕様検討
- Raspberry Pi を用いた制御システムの構成検討
- モータ駆動機構の検討
- テスト運用に向けた改善点の整理
- 新入生や後輩が開発に参加しやすい形への資料化・引き継ぎ準備

> 技術的な実装だけでなく、**利用者視点・管理者視点・継続運用のしやすさ** を考慮したシステム設計の重要性を学びました。就活やポートフォリオで見せる場合は、[English Summary](#14-english-summary) も参照してください。

---

### 今後の改善予定

- 配布機構の安定性向上
- 補充しやすい筐体構造への改善
- 端末状態の確認機能の追加
- 利用状況の記録・可視化
- 複数台運用を想定した管理方法の検討
- 学内で継続的に運用できる体制づくり

---

### GitHub リポジトリの説明文（コピペ用）

**日本語：**

> 学内で生理用品を必要とする学生が必要なときに受け取れるようにする、Raspberry Pi 制御の生理用品配布システムです。配布機構・制御・運用設計を含めて開発しています。

**実績アピール寄り：**

> Raspberry Pi とモータ制御を用いた学内向け生理用品配布システム。社会課題に対し、ハードウェア・ソフトウェア・運用設計を組み合わせて実装したプロジェクトです。

**就活・ポートフォリオ向け：**

> 大学内で生理用品を必要とする学生が、必要なときに自然に受け取れる環境をつくることを目的に、学内向け生理用品配布システム「オイテル」を企画・開発しました。Raspberry Pi を用いた端末制御、モータによる配布機構、補充・保守を考慮した運用設計を行い、実際の学内テスト運用を見据えて改善を進めています。社会課題に対して技術実装と現場運用の両面からアプローチした経験です。

---

## 2. OITERU って何？（ざっくり）

むずかしい説明を抜きにすると、OITERU は **「カードをかざすと生理用品が出てくる機械」** です。

コンビニのコピー機をイメージしてください。カードをかざす → ほしいものが出てくる。それと同じです。

```
利用者が NFC カードをかざす
        ↓
子機（ラズパイ）がカードを読み取って親機に問い合わせる
        ↓
親機が「この人は今日まだ使ってない」と判断したら排出許可を出す
        ↓
子機のモーターが動いて生理用品が 1 つ出る
        ↓
親機のデータベースに「誰が・いつ・どの子機で使ったか」が記録される
```

### 登場人物

| 名前 | 学校で言うと… | やること |
|------|-------------|---------|
| **親機** | 職員室 | データを保存し、管理画面を提供する。校内に 1 台 |
| **子機** | 各階の自動販売機 | NFC を読み、生理用品を出す。各階・各棟に置ける |
| **管理画面** | 先生用の管理簿 | ブラウザで在庫・履歴を確認できる画面 |
| **利用者** | 学生 | カードをかざすだけ。管理画面は操作しない |

---

## 3. はじめに — ターミナルって何？

これから先、**「ターミナル」** というものを使います。

ターミナルとは「PC に文字で指示を出す窓口」です。マウスでクリックする代わりに、キーボードで命令を打ち込みます。ゲームの「チート入力画面」のようなものだと思ってください。

**「なんで文字で打たなきゃいけないの？」**
→ 細かい設定やサーバー起動は、文字のほうが確実かつ速いからです。怖がらなくて大丈夫。**コピー＆ペーストで進められます。**

### ターミナルの開き方

| あなたの PC | 開き方 |
|------------|--------|
| **Ubuntu（Linux）** | `Ctrl + Alt + T` を押す |
| **Raspberry Pi** | 画面左上のメニュー →「Accessories」→「Terminal」 |
| **macOS** | `Command + スペース` →「ターミナル」と入力 → Enter |
| **Windows** | スタートメニュー →「PowerShell」と入力 → Enter |

開くと、次のような画面が出ます。

```
user@pc-name:~$
```

この `$` の右側に、これから紹介するコマンドを打ち込んでいきます。コピペで OK です。

### コピペのやり方

| 操作 | やり方 |
|------|--------|
| コピー | この README のコマンドを選択して `Ctrl + C` |
| 貼り付け（Linux） | ターミナルで `Ctrl + Shift + V` |
| 貼り付け（macOS） | ターミナルで `Command + V` |
| 貼り付け（Windows PowerShell） | 右クリック |
| 実行 | 貼り付けたあと `Enter` キー |

> **注意：** Linux のターミナルでは `Ctrl + V` が使えません。`Ctrl + Shift + V` を使ってください。

---

## 4. 必要なものと、それぞれの役割

### ソフトウェア

| ソフト名 | 一言で | 何に使うの？ |
|---------|--------|------------|
| **Ubuntu** | PC を動かす基本ソフト | 親機用。Windows や Mac と同じ種類のもの |
| **Raspberry Pi OS** | ラズパイを動かす基本ソフト | 子機用 |
| **Python** | プログラムの実行役 | OITERU は Python という言語で書かれている |
| **MySQL** | 超巨大な Excel | 利用履歴や在庫を保存する「データベース」 |
| **tmux** | 画面を閉じても裏で動き続ける仕組み | 親機・子機を起動したまま席を離れられる |
| **Git** | 変更履歴のタイムマシン | GitHub から最新コードをダウンロードする |
| **VS Code** | メモ帳のすごい版 | 設定ファイルを編集する（メモ帳より見やすい） |

### ダウンロード先

| ソフト | URL |
|--------|-----|
| Ubuntu | https://ubuntu.com/download |
| Raspberry Pi Imager | https://www.raspberrypi.com/software/ |
| Raspberry Pi OS | https://www.raspberrypi.com/software/operating-systems/ |
| Python | https://www.python.org/downloads/ |
| Git | https://git-scm.com/downloads |
| MySQL | https://dev.mysql.com/downloads/mysql/ |
| VS Code | https://code.visualstudio.com/download |
| Tailscale（任意） | https://tailscale.com/downloads |

### ハードウェア

| 機器 | 役割 |
|------|------|
| **親機用 PC** | Ubuntu が動く PC またはノート PC |
| **子機用 Raspberry Pi** | 各設置場所に 1 台。NFC リーダーとモーターを接続 |
| **NFC カードリーダー** | かざしたカードを読み取る機械（USB 接続） |
| **NFC カード** | 利用者が持つ学生証や専用カード |
| **モーター** | 生理用品を押し出す機構 |
| **LED** | 利用者に OK/NG を知らせるランプ（緑＝出ます、赤＝出ません） |
| **センサー（任意）** | ちゃんと排出できたか確認する sensor |

---

## 5. はじめての準備（全員共通）

親機でも子機でも、最初にやることは同じです。

### Step 1：ターミナルを開く

[ターミナルの開き方](#ターミナルの開き方) を見て、まずターミナルを開いてください。

### Step 2：プロジェクトをダウンロードする

**今からやること**

GitHub に置いてある OITERU のプログラムを、自分の PC にまるごとコピーします。

```bash
git clone https://github.com/your-team/oiteru_202603.git ~/Desktop/oiteru_202603
```

| 文字列 | 読み方 | 日本語で言うと | 何をしている？ |
|--------|--------|--------------|--------------|
| `git clone` | ギット クローン | 「GitHub からコピーして」 | GitHub 上のプログラムを PC に複製する |
| `https://...` | （URL） | 「この住所から」 | コピー元のインターネット上の場所 |
| `~/Desktop/oiteru_202603` | チルダ デスクトップ オイテル | 「デスクトップに oiteru_202603 というフォルダで」 | 保存先の指定。`~` は自分のホームフォルダ |

> **うまくいくと…**
> `Cloning into '~/Desktop/oiteru_202603'...` と表示され、デスクトップに `oiteru_202603` フォルダができます。

### Step 3：ダウンロードしたフォルダに移動する

**今からやること**

ターミナルの中での「今いる場所」を、さっきダウンロードしたフォルダに変えます。

```bash
cd ~/Desktop/oiteru_202603
```

| 文字列 | 読み方 | 日本語で言うと | 何をしている？ |
|--------|--------|--------------|--------------|
| `cd` | シーディー | 「移動して」 | Change Directory。今いる場所を変える |
| `~/Desktop/oiteru_202603` | （パス） | 「デスクトップの oiteru_202603 フォルダへ」 | 移動先 |

> **うまくいくと…**
> 見た目は何も変わりません。確認したいときは次のコマンドを打ちます。

```bash
pwd
```

| 文字列 | 読み方 | 日本語で言うと | 何をしている？ |
|--------|--------|--------------|--------------|
| `pwd` | ピーダブリューディー | 「今どこにいる？」 | Print Working Directory。現在地を表示する |

> **うまくいくと…**
> `/home/あなたの名前/Desktop/oiteru_202603` のように表示されます。これが「今いる場所」です。

> **フォルダが見つからない場合**
> ```bash
> find ~ -name unit.py 2>/dev/null | grep oiteru
> ```
> これは「ホームフォルダ以下から `unit.py` を探して、`oiteru` が含まれるものを表示して」というコマンドです。表示されたパスに `cd` で移動してください。

### Step 4：最新の状態にする

**今からやること**

チームの誰かが更新しているかもしれないので、最新のコードを GitHub から取り込みます。

```bash
git pull
```

| 文字列 | 読み方 | 日本語で言うと | 何をしている？ |
|--------|--------|--------------|--------------|
| `git pull` | ギット プル | 「最新を引っ張ってきて」 | GitHub 上の最新の変更を自分の PC に反映する |

> **うまくいくと…**
> `Already up to date.` または更新内容がズラズラと表示されます。どちらでも OK です。

### Step 5：必要なソフトをまとめてインストールする

**今からやること**

OITERU を動かすために必要なソフトを、まとめて入れます。次の 1 行をコピペして Enter を押すだけです。

```bash
sudo apt update && sudo apt install -y git tmux python3-full python3-venv python3-pip curl
```

| 文字列 | 読み方 | 日本語で言うと | 何をしている？ |
|--------|--------|--------------|--------------|
| `sudo` | スードゥ | 「管理者権限で」 | SuperUser DO。PC 全体に影響する操作を許可する |
| `apt update` | アプト アップデート | 「ソフト一覧を最新にして」 | インストールできるソフトの情報を更新 |
| `apt install -y` | アプト インストール ワイ | 「次のソフトを入れて」 | ソフトをインストールする。`-y` は確認省略 |
| `git` | ギット | 「Git を」 | コード履歴管理ツール |
| `tmux` | ティーマックス | 「tmux を」 | 画面を閉じてもプログラムを動かし続けるツール |
| `python3-full` | パイソン フル | 「Python 本体を」 | プログラムの実行環境 |
| `python3-venv` | パイソン ヴェンv | 「仮想環境機能を」 | プロジェクト専用の隔離された実行環境を作る機能 |
| `python3-pip` | パイソン ピップ | 「ライブラリ管理を」 | Python の追加パーツをインストールするツール |
| `curl` | カール | 「通信テストを」 | URL にアクセスして接続確認をするツール |

> **うまくいくと…**
> たくさん文字が流れて、最後に `done.` のような表示が出ます。エラーが出なければ OK です。

---

## 6. 親機を起動する（全6ステップ）

親機は **「データを保存する係」＋「管理画面を提供する係」** の PC です。

### Step 6-1：設定ファイル `.env` を作る

**今からやること**

テンプレートをコピーして、自分専用の設定ファイルを作ります。

```bash
cp .env.example .env
```

| 文字列 | 読み方 | 日本語で言うと | 何をしている？ |
|--------|--------|--------------|--------------|
| `cp` | コピー | 「コピーして」 | ファイルを複製する |
| `.env.example` | ドット イーエヌブイ エグザンプル | 「このテンプレートを」 | プロジェクトに最初から入っている見本ファイル |
| `.env` | ドット イーエヌブイ | 「.env という名前で」 | 自分用の設定ファイル。**GitHub に絶対上げない** |

> **うまくいくと…**
> 見た目は何も変わりません。`ls -la` と打つと `.env` が一覧に出ます。

### Step 6-2：`.env` を編集する

**今からやること**

コピーした設定ファイルの中身を、自分の環境に合わせて書き換えます。

#### 方法A：VS Code で編集する（おすすめ）

VS Code をインストール済みなら、次のコマンドで開けます。

```bash
code .env
```

マウスでカーソルを動かして、普通のメモ帳のように編集できます。書き終わったら `Ctrl + S` で保存、`Ctrl + W` でタブを閉じます。

#### 方法B：ターミナル上で編集する（VS Code が無い場合）

```bash
nano .env
```

| 文字列 | 読み方 | 日本語で言うと | 何をしている？ |
|--------|--------|--------------|--------------|
| `nano` | ナノ | 「nano エディタで開いて」 | ターミナル内で動くシンプルなエディタ |

**nano での操作方法：**

| 操作 | キー |
|------|------|
| カーソル移動 | 矢印キー（↑↓←→） |
| 保存する | `Ctrl + O`（オー）→ `Enter` |
| 閉じる | `Ctrl + X` |

---

**編集する内容：** 以下の 4 項目を必ず変更してください。

| 変数名 | 何の設定？ | 変更後の例 |
|--------|-----------|-----------|
| `FLASK_SECRET_KEY` | セッション暗号化の鍵。32文字以上の適当な文字列 | `a1b2c3d4e5f6...（適当に長く打つ）` |
| `OITERU_ADMIN_PASSWORD` | 管理画面にログインするときのパスワード | `my-password-2026` |
| `MYSQL_PASSWORD` | データベース接続用パスワード | `my-db-password` |
| `MYSQL_ROOT_PASSWORD` | データベース管理者パスワード | `my-root-password` |

> **4 つすべて `change-this-...` のままにしないでください。** そのままだと後続のスクリプトが止まります。

### Step 6-3：MySQL（データベース）をインストールする

**今からやること**

利用履歴や在庫情報を保存する「データベースソフト」を入れます。

```bash
sudo apt install -y mysql-server
```

| 文字列 | 読み方 | 日本語で言うと | 何をしている？ |
|--------|--------|--------------|--------------|
| `mysql-server` | マイエスキューエル サーバー | 「MySQL 本体を」 | データを保存・管理するソフト |

> **うまくいくと…**
> インストールが完了します。エラーが出たらインターネット接続を確認してください。

### Step 6-4：MySQL を初期設定する

**今からやること**

OITERU 用のデータベースとユーザーを自動作成するスクリプトを実行します。

```bash
scripts/setup_local_mysql.sh
```

| 文字列 | 読み方 | 日本語で言うと | 何をしている？ |
|--------|--------|--------------|--------------|
| `scripts/setup_local_mysql.sh` | セットアップ ローカル マイエスキューエル | 「MySQL 準備スクリプト」 | `.env` を読んで、データベースとユーザーを自動で作る |

> **うまくいくと…**
> `Database setup complete.` のようなメッセージが出ます。
>
> `.env` の `MYSQL_PASSWORD` が `change-this-mysql-password` のままだと「パスワードを変えてください」と言って止まります。Step 6-2 を先にやってください。

**確認：MySQL が動いているか**

```bash
systemctl status mysql
```

| 文字列 | 読み方 | 日本語で言うと | 何をしている？ |
|--------|--------|--------------|--------------|
| `systemctl status` | システムシーティーエル ステータス | 「サービスの状態を表示」 | OS の裏で動いているプログラムの状態を見る |
| `mysql` | マイエスキューエル | 「MySQL の」 | 見たい対象 |

> **うまくいくと…**
> `Active: active (running)` と表示されれば OK です。

**確認：DB に接続できるか**

```bash
mysql -u oiteru_user -p oiteru -e "SELECT 1;"
```

| 文字列 | 読み方 | 日本語で言うと | 何をしている？ |
|--------|--------|--------------|--------------|
| `mysql` | マイエスキューエル | 「MySQL に接続」 | データベースに接続するコマンド |
| `-u oiteru_user` | ユー オイテルユーザー | 「ユーザー名は oiteru_user」 | データベースに接続するときの名前 |
| `-p oiteru` | ピー オイテル | 「パスワード入力、DB名は oiteru」 | 接続先のデータベース指定 |
| `-e "SELECT 1;"` | イー セレクト ワン | 「1 を返してテスト」 | 最も簡単な SQL 文。接続テスト用 |

> **うまくいくと…**
> `1` と表示されれば接続成功です。

### Step 6-5：tmux で親機を起動する

**今からやること**

tmux という「画面を閉じても動き続ける仕組み」の中で、親機プログラムを起動します。

```bash
scripts/tmux_oiteru.sh start parent
```

| 文字列 | 読み方 | 日本語で言うと | 何をしている？ |
|--------|--------|--------------|--------------|
| `scripts/tmux_oiteru.sh` | ティーマックス オイテル スクリプト | 「tmux 起動スクリプト」 | tmux の起動・停止を簡単にする補助ツール |
| `start parent` | スタート ペアレント | 「親機を起動して」 | 親機のプログラムを tmux の中で起動する |

> **うまくいくと…**
> `Session oiteru-parent started.` と表示されます。

**起動中の画面を見る：**

```bash
scripts/tmux_oiteru.sh attach parent
```

| 文字列 | 読み方 | 日本語で言うと | 何をしている？ |
|--------|--------|--------------|--------------|
| `attach parent` | アタッチ ペアレント | 「親機の画面を表示して」 | 起動中の親機プログラムのログ画面を表示する |

> **うまくいくと…**
> 画面にログ（動作記録）が流れ始めます。エラーが表示されたら [「あれ？動かない」](#11-あれ動かないとなったとき) を見てください。

### Step 6-6：管理画面をブラウザで開く

**今からやること**

ブラウザ（Chrome や Firefox）で管理画面を開きます。

**親機と同じ PC で見る場合：**

```
http://localhost:5000/admin
```

**別の PC から見る場合：**

```
http://<親機のIPアドレス>:5000/admin
```

> **IP アドレスの調べ方：**
> ```bash
> hostname -I
> ```
> 表示された `192.168.x.x` のような数字が IP アドレスです。`127.0.0.1` は無視してください。

**ログイン画面：**

![管理画面ログイン](docs/img/admin-login.png)
<!-- TODO: 実際のログイン画面のスクリーンショットに差し替えてください -->

パスワードは `.env` に書いた `OITERU_ADMIN_PASSWORD` です。

---

## 7. 子機を起動する（全4ステップ）

子機は **「NFC カードを読んで、モーターで生理用品を出す」** Raspberry Pi です。

> 子機のセットアップは Raspberry Pi 上で行います。親機とは別のマシンです。

### Step 7-1：プロジェクトをダウンロードする（子機側でもう一度）

親機と同じ手順を、子機（Raspberry Pi）でも行います。

```bash
git clone https://github.com/your-team/oiteru_202603.git ~/Desktop/oiteru_202603
cd ~/Desktop/oiteru_202603
git pull
```

[Step 5-2〜5-4](#5-はじめての準備全員共通) と同じ流れです。詳細は前の章を参照してください。

### Step 7-2：設定ファイル `config.json` を作って編集する

**今からやること**

子機用の設定テンプレートをコピーして、中身を書き換えます。

```bash
cp config.example.json config.json
```

```bash
code config.json
```

| 文字列 | 読み方 | 日本語で言うと | 何をしている？ |
|--------|--------|--------------|--------------|
| `config.example.json` | コンフィグ エグザンプル | 「子機設定のテンプレート」 | プロジェクトに最初から入っている見本 |
| `config.json` | コンフィグ ジェイソン | 「自分用の設定ファイル」 | **GitHub に絶対上げない** |

**編集する内容：** 以下の 3 項目を必ず変更してください。

| キー | 何の設定？ | 変更後の例 |
|------|-----------|-----------|
| `SERVER_URL` | 親機の URL。子機が「親機どこ？」と探すときの住所 | `http://192.168.1.10:5000` |
| `UNIT_NAME` | この子機の名前。管理画面に表示される | `unit-01`（子機ごとに変える） |
| `UNIT_PASSWORD` | 親機と子機の間の認証パスワード | `change-this` |

> **うまくいくと…**
> 保存できれば OK です。VS Code なら `Ctrl + S`。

### Step 7-3：Raspberry Pi の追加準備

NFC やモーター制御に必要なソフトを入れます。

```bash
sudo apt install -y pigpio
sudo systemctl enable pigpiod
sudo systemctl start pigpiod
```

| 文字列 | 読み方 | 日本語で言うと | 何をしている？ |
|--------|--------|--------------|--------------|
| `pigpio` | ピッグ パイオ | 「GPIO 制御ソフト」 | Raspberry Pi の入出力ピンを制御するソフト |
| `systemctl enable` | システムシーティーエル イネーブル | 「自動起動を設定」 | OS 起動時に自動で pigpio を立ち上げる |
| `systemctl start` | システムシーティーエル スタート | 「今すぐ起動」 | pigpio を今すぐ起動する |

> **うまくいくと…**
> エラーが出なければ OK です。

### Step 7-4：tmux で子機を起動する

**今からやること**

親機と同じく、tmux の中で子機プログラムを起動します。

```bash
scripts/tmux_oiteru.sh start unit
scripts/tmux_oiteru.sh attach unit
```

| 文字列 | 読み方 | 日本語で言うと | 何をしている？ |
|--------|--------|--------------|--------------|
| `start unit` | スタート ユニット | 「子機を起動して」 | 子機のプログラムを tmux の中で起動する |
| `attach unit` | アタッチ ユニット | 「子機の画面を表示して」 | 起動中の子機のログ画面を表示する |

> **うまくいくと…**
> 画面に「NFC リーダー待機中」のようなログが流れます。
>
> 管理画面の「子機一覧」に表示されれば成功です。

![子機一覧](docs/img/unit-list.png)
<!-- TODO: 実際の子機一覧画面のスクリーンショットに差し替えてください -->

---

## 8. 管理画面を見てみよう

ブラウザで `http://（親機のIP）:5000/admin` を開きます。

### 最初に確認すること

| 確認したいこと | どこを見る？ |
|-------------|------------|
| ログインできるか | ログイン画面。パスワードは `.env` の `OITERU_ADMIN_PASSWORD` |
| 子機が一覧にいるか | 子機一覧画面。`unit-01` などが表示されていれば OK |
| 子機の最終接続時刻が動いているか | 子機詳細画面。数分以内の時刻なら heartbeat が届いている証拠 |
| 在庫数が正しいか | 子機詳細画面 |
| 利用履歴が残っているか | 履歴画面。カードをかざした後に新しい行が増えていれば OK |

![利用履歴](docs/img/history.png)
<!-- TODO: 実際の利用履歴画面のスクリーンショットに差し替えてください -->

### 日常の運用でやること

1. 補充前に管理画面で対象子機の在庫と最終接続時刻を確認
2. 補充後に「現在の在庫数」を管理画面で更新
3. 子機の設定を変えたら heartbeat の同期完了を確認
4. **管理画面のパスワードはチャットやメモに平文で貼らない**

---

## 9. tmux の超基本

tmux を使う理由は 1 つだけ：**ターミナルを閉じても、起動したプログラムが止まらない** からです。

覚えることは 3 つだけです。

| やりたいこと | コマンド |
|-------------|---------|
| **親機・子機が動いているか確認** | `scripts/tmux_oiteru.sh status` |
| **親機のログ画面を見る** | `scripts/tmux_oiteru.sh attach parent` |
| **子機のログ画面を見る** | `scripts/tmux_oiteru.sh attach unit` |

### 画面から抜ける（重要）

ログ画面を見終わったら、この操作で抜けます。**プログラムは止まりません。**

```
Ctrl + B  →  指を離す  →  D
```

1. `Ctrl` キーを押しながら `B` を押す（両方離す）
2. その後 `D` を押す
3. `[detached]` と表示されて元の画面に戻る

> これだけ覚えてください。`Ctrl+B → D` が tmux の 8 割です。

### その他の操作（必要なときだけ）

| やりたいこと | コマンド |
|-------------|---------|
| いま動いている tmux 一覧 | `tmux ls` |
| 親機を止める | `scripts/tmux_oiteru.sh stop parent` |
| 子機を止める | `scripts/tmux_oiteru.sh stop unit` |
| 親機を再起動 | `scripts/tmux_oiteru.sh restart parent` |
| ログを見る | `scripts/tmux_oiteru.sh logs parent` |

---

## 10. ディレクトリ構成（興味がある人だけ）

```
oiteru_202603/
├── db_server.py              ← 親機の起動ファイル（これを tmux で起動する）
├── unit.py                   ← 子機の起動ファイル（これを tmux で起動する）
├── server.py                 ← 旧バージョン（通常使わない）
├── .env.example              ← 親機設定のテンプレート
├── config.example.json       ← 子機設定のテンプレート
├── requirements.txt          ← 親機で必要な Python ライブラリ一覧
├── requirements-client.txt   ← 子機で必要な Python ライブラリ一覧
├── scripts/                  ← 起動・セットアップ用スクリプト置き場
├── docs/                     ← 詳しい説明書置き場
│   ├── img/                  ← スクリーンショット置き場
│   ├── onboarding.md         ← 開発参加者向けガイド
│   └── operations.md         ← 日常運用・障害時対応
├── 取説書/                   ← 初心者向け完全マニュアル
├── templates/                ← 管理画面の HTML
├── static/                   ← CSS/JS などの静的ファイル
├── tests/                    ← 自動テストコード
└── tools/                    ← ユーティリティツール
```

---

## 11. 「あれ？動かない」となったとき

エラーが出ても慌てないでください。以下の「エラー → 日本語訳 → 対処法」を順に試してください。

### 管理画面が開かない

**エラーの例：** `このサイトにアクセスできません` `Connection refused`

**日本語で言うと：** 「親機に接続できませんでした。親機が起動していないか、URL が間違っています」

**試すこと：**

```bash
scripts/tmux_oiteru.sh status parent    # 親機は動いてる？
curl http://localhost:5000              # 親機は応答する？
scripts/tmux_oiteru.sh logs parent      # ログにエラーが出てない？
```

- `.env` の `OITERU_ADMIN_PASSWORD` が正しいか確認
- 親機を再起動してみる：`scripts/tmux_oiteru.sh restart parent`

---

### tmux 画面から戻れなくなった

**エラーの例：** 画面が固まった、何を押しても反応しない

**日本語で言うと：** 「tmux の画面にアタッチしたまま抜け方を忘れた状態です。プログラムは止まっていません」

**試すこと：**

```bash
tmux ls                                  # 動いている tmux の一覧
scripts/tmux_oiteru.sh status            # 親機・子機の状態
scripts/tmux_oiteru.sh attach parent     # 親機に再接続
```

---

### 子機が親機に接続できない

**エラーの例：** `Connection refused` `timeout` `Name or service not known`

**日本語で言うと：** 「子機から親機に通信が届いていません。親機の IP アドレスが違うか、ネットワークが分断されています」

**試すこと（子機側で実行）：**

```bash
curl http://<親機のIPアドレス>:5000       # 親機に通信が届くかテスト
```

- `config.json` の `SERVER_URL` が正しい親機の IP か確認
- 親機と子機が同じネットワーク（同じ Wi-Fi や LAN）にいるか確認
- 親機側のファイアウォールを確認（ポート 5000 が開いている必要あり）

---

### MySQL に接続できない

**エラーの例：** `Access denied for user` `Can't connect to MySQL server`

**日本語で言うと：**
- `Access denied` → 「ユーザー名かパスワードが間違っています」
- `Can't connect` → 「MySQL が起動していません」

**試すこと：**

```bash
systemctl status mysql                                  # MySQL 起動してる？
mysql -u oiteru_user -p oiteru -e "SELECT 1;"           # 接続テスト
```

- `.env` の `MYSQL_HOST`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE` を確認
- パスワードが `change-this-mysql-password` のままなら Step 6-2 で変更

---

### NFC カードが読めない

**エラーの例：** カードをかざしても反応がない

**日本語で言うと：** 「NFC リーダーが認識されていないか、子機プログラムがカード待ちになっていません」

**試すこと：**

```bash
lsusb                                  # USB 機器一覧。NFC リーダーが表示されるか
```

- USB リーダーを抜き差ししてから子機を再起動：`scripts/tmux_oiteru.sh restart unit`
- Raspberry Pi の USB ポートによって電力不足になることがある → 別のポートを試す
- NFC リーダーが対応機種か確認（プロジェクト指定のリーダーを使ってください）

---

### `externally-managed-environment` と表示される

**エラーの例：**

```
error: externally-managed-environment
```

**日本語で言うと：** 「Raspberry Pi OS の新しいバージョンでは、直接 `pip install` できません。仮想環境（venv）を使う必要があります」

**試すこと：**

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-client.txt
```

通常は `./venv-start.sh unit` が自動でやってくれます。そちらを使ってください。

---

### `scripts/tmux_oiteru.sh: Permission denied` と表示される

**エラーの例：**

```
bash: scripts/tmux_oiteru.sh: Permission denied
```

**日本語で言うと：** 「スクリプトに実行権限がありません」

**試すこと：**

```bash
chmod +x scripts/tmux_oiteru.sh
```

| 文字列 | 読み方 | 日本語で言うと | 何をしている？ |
|--------|--------|--------------|--------------|
| `chmod +x` | シーモッド プラスエックス | 「実行権限を付与」 | ファイルを実行可能にする |

---

### どうしても直らないとき

以下のファイルに詳しいトラブルシューティングがあります。

| 資料 | 内容 |
|------|------|
| [取説書/QUICKSTART.md](取説書/QUICKSTART.md) | 全トラブル対応（500行超の完全ガイド） |
| [docs/operations.md](docs/operations.md) | 障害時一次対応マニュアル |

---

## 12. 開発に参加したい人へ

コードを書いて参加したい人は、次の順番で始めてください。

1. **`docs/onboarding.md` を最初に読む** — 開発のルールと禁止事項が書いてあります
2. 小さい修正から始める（README の修正、スクリプトの改善など）
3. 1 つの PR（Pull Request）には 1 つの目的だけ入れる

### どこを触ればいい？

| やりたいこと | 主なファイル |
|-------------|------------|
| 管理画面の API を直す | `db_server.py`, `templates/` |
| DB の処理を直す | `db_adapter.py`, `.env.example` |
| 子機の通信を直す | `unit.py` |
| ハード（モーター・LED）制御を直す | `unit.py` |
| 起動手順を改善する | `scripts/`, `README.md` |
| 運用ルールを更新する | `docs/operations.md` |

### 開発で心がけること

| ルール | 理由 |
|--------|------|
| **標準 DB は MySQL 8** | SQLite 前提の新規コードは追加しない |
| route handler に直接 SQL を書かない | 責務を分離するため |
| 実機依存コード（GPIO/NFC）はインターフェースを切る | モックでテストできるようにする |
| コードを変えたら README、`.env.example`、docs も更新する | 全員が迷わないため |
| 1 PR = 1 目的 | 大きな変更を避け、レビューしやすくする |

---

## 13. 絶対に守ること

### やってはいけないこと

| 禁止事項 | 理由 |
|---------|------|
| `.env` や `config.json` を Git でコミットする | パスワードなどの秘密情報が GitHub 上に公開されてしまう |
| パスワードをコードの中に直接書く | 誰でも見られる。セキュリティ上の重大なリスク |
| `.env` のパスワードを `change-this-...` のままにする | 初期値のまま動かすと誰でも入れてしまう |
| 管理画面のパスワードをチャットで共有する | 関係ない人に知られるリスク |
| `print()` だけでログを出す（開発者の場合） | あとで障害調査するときに追跡できない |

### Git に入れてはいけないファイル

以下のファイルは **絶対にコミット（`git add` / `git commit`）しないでください**。

| ファイル | 理由 |
|---------|------|
| `.env` | 管理者パスワード、DB パスワードを含む |
| `config.json` | 子機パスワード、親機 URL、設置場所を含む |
| `logs/` 以下のファイル | 運用ログ（利用者情報が含まれる可能性） |
| `*.log` | 同上 |
| `*.sqlite3` | 旧 DB ファイル（ローカルのデータ） |

**コミット前の確認：**

```bash
git status --short
```

ここに `.env` や `config.json` が表示されたら、コミットしないでください。

---

## 14. English Summary

### OITERU: Campus Sanitary Product Distribution System

OITERU is a campus-oriented sanitary product distribution system designed to help students access sanitary products when needed.

The project focuses not only on providing physical items, but also on designing a practical distribution device, control mechanism, and operational workflow for real campus use. The goal is to reduce psychological barriers for users while making the system easy for administrators to refill, maintain, and improve.

The prototype uses a Raspberry Pi-based control system and a motor-driven dispensing mechanism. Through this project, the team worked on the system concept, hardware configuration, control design, and operational planning for campus deployment.

This project gave practical experience in developing a system that combines hardware, software, and real-world operation. It also emphasized the importance of user-centered design, maintainability, and continuous improvement in social implementation.

### Key features

- NFC card-based dispensing (tap a card → receive a product)
- Daily usage limits per user
- Web-based admin panel for inventory and history
- Remote monitoring of each child unit via heartbeat
- Designed for easy refilling and maintenance
- Iterative improvement through real-world testing

### Tech stack

- **Language:** Python 3.10+
- **Web framework:** Flask
- **Database:** MySQL 8.0 (InnoDB)
- **Child unit:** Raspberry Pi + pigpio + NFC reader + motor control
- **Session management:** tmux
- **Standard OS:** Ubuntu (parent) / Raspberry Pi OS (child)

### Quick start (parent machine)

```bash
git clone https://github.com/your-team/oiteru_202603.git ~/Desktop/oiteru_202603
cd ~/Desktop/oiteru_202603
sudo apt update && sudo apt install -y git tmux python3-full python3-venv python3-pip mysql-server curl
cp .env.example .env       # Then edit .env with your own passwords
scripts/setup_local_mysql.sh
scripts/tmux_oiteru.sh start parent
scripts/tmux_oiteru.sh attach parent
```

Open `http://<parent-IP>:5000/admin` in your browser. Login password is the `OITERU_ADMIN_PASSWORD` you set in `.env`.

### Quick start (child unit — Raspberry Pi)

```bash
git clone https://github.com/your-team/oiteru_202603.git ~/Desktop/oiteru_202603
cd ~/Desktop/oiteru_202603
sudo apt update && sudo apt install -y git tmux python3-full python3-venv python3-pip curl pigpio
sudo systemctl enable pigpiod && sudo systemctl start pigpiod
cp config.example.json config.json   # Then edit config.json
scripts/tmux_oiteru.sh start unit
scripts/tmux_oiteru.sh attach unit
```

### For contributors

See [docs/onboarding.md](docs/onboarding.md) for development rules and setup. All PRs must be small and single-purpose. Standard DB is MySQL 8 — do not add SQLite-dependent code.

---

## 参考リンク

| 資料 | 内容 |
|------|------|
| [取説書/QUICKSTART.md](取説書/QUICKSTART.md) | 詳細起動手順＋Windows 開発＋全トラブル対応 |
| [docs/onboarding.md](docs/onboarding.md) | 開発参加者向けルールとセットアップ |
| [docs/operations.md](docs/operations.md) | 日常運用・障害時対応マニュアル |
| [scripts/README.md](scripts/README.md) | スクリプト一覧と使い方 |
| [AGENTS.md](AGENTS.md) | プロジェクト方針とルール（上級者／AI 向け） |

---

> **最終更新:** 2026-06-17
