# 複数親機構成 - クイックスタートガイド

## 📋 概要

今後親機が増える際、複数の親機が同じMySQLデータベースを共有できるようになりました。

## 🚀 使い方

### パターン1: 同一マシンで複数親機を起動(テスト用)

```bash
# セットアップスクリプトを実行
./setup_multi_server.sh

# または直接起動
docker-compose -f docker-compose.multi-server.yml up -d
```

**アクセス先:**
- 親機1号機: http://localhost:5000
- 親機2号機: http://localhost:5001  
- phpMyAdmin: http://localhost:8080

---

### パターン2: 別マシンから外部MySQLに接続

**メインサーバー(1台目)で:**
```bash
docker-compose -f docker-compose.multi-server.yml up -d
```

**サブサーバー(2台目以降)で:**

1. `docker-compose.external-db.yml`を編集:
```yaml
environment:
  - MYSQL_HOST=192.168.1.100  # メインサーバーのIP
  - SERVER_NAME=親機3号機
  - SERVER_LOCATION=3階会議室
```

2. 起動:
```bash
docker-compose -f docker-compose.external-db.yml up -d
```

---

### パターン3: セットアップスクリプトを使う(推奨)

```bash
# 対話型セットアップ
./setup_multi_server.sh

# 指示に従って以下を選択:
# 1. 同一マシン上で複数親機
# 2. 外部MySQLに接続する親機
# 3. 既存のMySQLサーバーを利用
```

---

## ✅ 確認方法

1. **管理画面にアクセス**
   - http://localhost:5000/admin (パスワード: admin)

2. **サーバー情報を確認**
   - ダッシュボード上部に「📡 このサーバーの情報」が表示されます
   - サーバー名、設置場所、サーバーID、データベースタイプが確認できます

3. **データベース接続を確認**
```bash
# MySQLに直接アクセス
docker exec -it oiteru_mysql_shared mysql -u oiteru_user -poiteru_password_2025 -e "USE oiteru; SELECT COUNT(*) FROM users;"
```

---

## 📚 詳細ドキュメント

完全なガイドは以下を参照:
- **取説書/MULTI_SERVER.md** - 複数親機構成の詳細ガイド

## 🔐 セキュリティ注意事項

1. **パスワードを変更する**
   - デフォルトパスワードは必ず変更してください
   
2. **ファイアウォール設定**
   - MySQLポート(3306)は必要なIPからのみ許可

3. **Tailscale使用を推奨**
   - インターネット経由の接続にはTailscale VPNを使用

---

## 🎯 主な用途

| 構成 | 推奨用途 |
|------|----------|
| 同一マシン複数親機 | テスト環境、負荷分散 |
| 別マシン外部接続 | 複数拠点展開、本番環境 |
| 既存MySQL利用 | 既存インフラとの統合 |

---

## 🆘 トラブルシューティング

### 接続できない
```bash
# MySQLログを確認
docker logs oiteru_mysql_shared

# ネットワーク接続テスト
ping <メインサーバーIP>
telnet <メインサーバーIP> 3306
```

### データが見えない
```bash
# データベース確認
docker exec oiteru_mysql_shared mysql -u root -poiteru_root_password_2025 -e "SHOW DATABASES;"
```

詳細は **取説書/MULTI_SERVER.md** を参照してください。
