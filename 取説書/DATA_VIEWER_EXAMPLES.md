# データビューアー使用例

## クイックスタート

```bash
# 1. 必要なパッケージをインストール
pip install pandas openpyxl

# 2. サマリーを表示
python data_viewer.py summary

# 3. 全データをExcel出力
python data_viewer.py export-all
```

## 実行例

### サマリー表示

```bash
$ python data_viewer.py summary

✓ データベースに接続しました: oiteru.sqlite3

============================================================
OITELU システムサマリー
============================================================

📊 ユーザー統計:
  総ユーザー数:     25
  有効ユーザー数:   23
  総利用回数:       456
  今日の利用回数:   12

🖥️  子機統計:
  総子機数:         3
  利用可能子機数:   2
  総在庫数:         150

============================================================

✓ データベース接続を閉じました
```

### ユーザーデータをExcel出力

```bash
$ python data_viewer.py export-users

✓ データベースに接続しました: oiteru.sqlite3
✓ ユーザーデータを users_export_20251127_143052.xlsx に出力しました
✓ データベース接続を閉じました
```

出力されたExcelファイル（`users_export_YYYYMMDD_HHMMSS.xlsx`）には以下の情報が含まれます：

| 列名 | 説明 |
|------|------|
| ID | ユーザーID |
| カードID | ICカードのID |
| 利用許可 | 許可/不許可 |
| 登録日時 | 登録された日時 |
| 残り在庫 | ユーザーの残り在庫数 |
| 今日の利用 | 本日の利用回数 |
| 総利用回数 | 累計利用回数 |

### 利用統計をExcel出力

```bash
$ python data_viewer.py export-stats

✓ データベースに接続しました: oiteru.sqlite3
✓ 利用統計を usage_stats_20251127_143105.xlsx に出力しました
✓ データベース接続を閉じました
```

出力されたExcelファイル（`usage_stats_YYYYMMDD_HHMMSS.xlsx`）には2つのシートがあります：

**シート1: 時間帯別**
| 時間帯 | 利用回数 |
|--------|----------|
| 00:00  | 0 |
| 01:00  | 0 |
| ...    | ... |
| 12:00  | 45 |
| 13:00  | 67 |
| ...    | ... |

**シート2: 日別**
| 日付 | 利用回数 |
|------|----------|
| 2025-11-01 | 23 |
| 2025-11-02 | 31 |
| 2025-11-03 | 18 |
| ...        | ... |

### 全データを一括出力

```bash
$ python data_viewer.py export-all

✓ データベースに接続しました: oiteru.sqlite3
✓ ユーザーデータを users_20251127_143120.xlsx に出力しました
✓ 利用統計を stats_20251127_143120.xlsx に出力しました

✓ 全てのデータを出力しました
✓ データベース接続を閉じました
```

## 出力ファイルの活用例

### Excelでデータ分析

1. **ピボットテーブルで集計**
   - ユーザーごとの利用回数ランキング
   - 時間帯別の利用傾向分析

2. **グラフ作成**
   - 時間帯別利用グラフ（棒グラフ）
   - 日別利用推移（折れ線グラフ）

3. **フィルタリング**
   - 利用回数が多いユーザーを抽出
   - 特定期間のデータを分析

### PowerPointでプレゼン資料作成

1. Excelで作成したグラフをコピー
2. PowerPointに貼り付け
3. 宣伝活動やレポート作成に活用

### OneDrive/Google Driveで共有

1. 出力したExcelファイルをクラウドにアップロード
2. 共有リンクを作成
3. 閲覧権限のみを付与して安全に共有

## トラブルシューティング

### データベースが見つからない

```bash
# カレントディレクトリを確認
pwd

# データベースファイルの存在確認
ls -l oiteru.sqlite3

# パスを指定して実行
python data_viewer.py summary /path/to/oiteru.sqlite3
```

### openpyxlがインストールされていない

```bash
# エラーメッセージ例
ModuleNotFoundError: No module named 'openpyxl'

# 解決方法
pip install openpyxl
```

### pandasがインストールされていない

```bash
# エラーメッセージ例
ModuleNotFoundError: No module named 'pandas'

# 解決方法
pip install pandas
```

## セキュリティ注意事項

⚠️ **重要**: 出力されたExcelファイルには個人情報（カードID）が含まれます。

- ✅ 必要な人にのみ共有
- ✅ 閲覧権限のみを付与
- ✅ 使用後は削除
- ❌ 公開フォルダに置かない
- ❌ メールで不特定多数に送信しない

## 定期実行の設定

### Windowsタスクスケジューラで自動実行

毎週月曜日の朝9時にデータを自動出力する例：

1. タスクスケジューラを開く
2. 「基本タスクの作成」をクリック
3. 以下のように設定：
   - **名前**: OITELU週次レポート
   - **トリガー**: 毎週月曜日 9:00
   - **操作**: プログラムの開始
   - **プログラム**: `python`
   - **引数**: `data_viewer.py export-all`
   - **開始**: `C:\Users\Owner\Desktop\oiteru_250827_restAPI`

### Linuxのcronで自動実行

```bash
# crontabを編集
crontab -e

# 毎週月曜日 9:00に実行
0 9 * * 1 cd /path/to/oiteru_250827_restAPI && python3 data_viewer.py export-all
```

## まとめ

`data_viewer.py`を使用することで：

- ✅ データベースを安全に参照（読み取り専用）
- ✅ Excel形式で簡単にエクスポート
- ✅ 他のPCと安全にデータ共有
- ✅ データ分析やレポート作成が容易

詳細は [REMOTE_ACCESS.md](../取説書/REMOTE_ACCESS.md) を参照してください。
