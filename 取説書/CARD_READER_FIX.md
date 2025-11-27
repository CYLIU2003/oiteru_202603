# カードリーダー復旧手順 (クイックガイド)

## 🔧 症状
カードリーダーがWSL2で認識されなくなった

## ✅ 復旧手順

### 方法1: PowerShellで手動接続 (推奨)

1. **PowerShellを管理者権限で開く**
   - `Win + X` → "Windows PowerShell (管理者)" または "ターミナル (管理者)"

2. **USBデバイス一覧を確認**
   ```powershell
   usbipd list
   ```
   
   出力例:
   ```
   BUSID  VID:PID    DEVICE                                                        STATE
   1-5    054c:06c3  Sony FeliCa Port/PaSoRi, USB Smart Card reader               Not shared
   ```

3. **カードリーダーのBUSIDをメモ** (例: `1-5`)

4. **WSL2に接続**
   ```powershell
   # 初回のみ: bind (共有化)
   usbipd bind --busid 1-5
   
   # WSL2にアタッチ
   usbipd attach --wsl --busid 1-5
   ```

5. **WSL2で確認**
   ```bash
   lsusb | grep Sony
   ```
   
   成功すると:
   ```
   Bus 001 Device 002: ID 054c:06c3 Sony Corp. FeliCa S330 [PaSoRi]
   ```

### 方法2: バッチファイルで自動接続

1. エクスプローラーで開く:
   ```
   C:\Users\Owner\Desktop\oiteru_250827_restAPI\
   ```

2. `attach_card_reader.bat` を右クリック → **"管理者として実行"**

3. BUSID が `1-5` でない場合は、正しいBUSIDを入力

4. WSL2で確認:
   ```bash
   lsusb | grep Sony
   ```

### 方法3: Dockerコンテナ内で確認

```bash
# コンテナに入る
docker exec -it oiteru_flask bash

# カードリーダー初期化
/app/init_card_reader.sh

# 確認
pcsc_scan
```

## 🚨 トラブルシューティング

### カードリーダーが見つからない

1. **物理接続の確認**
   - USBケーブルを抜き差し
   - 別のUSBポートに接続

2. **Windowsで認識されているか確認**
   ```powershell
   usbipd list
   ```

3. **デバイスマネージャーで確認**
   - `Win + X` → デバイスマネージャー
   - "スマート カード リーダー" または "ユニバーサル シリアル バス コントローラー"
   - 黄色い警告マークがある場合はドライバー再インストール

### "Not shared" と表示される

```powershell
usbipd bind --busid 1-5
```

### "Access denied" エラー

- PowerShellを **管理者権限** で実行してください

### 接続後もWSL2で見えない

```powershell
# デタッチ
usbipd detach --busid 1-5

# 再アタッチ
usbipd attach --wsl --busid 1-5
```

### pcscdが起動しない

```bash
# WSL2で実行
sudo service pcscd restart
sudo service pcscd status
```

### Docker内で認識されない

```bash
# コンテナ再起動
docker restart oiteru_flask

# ログ確認
docker logs oiteru_flask
```

## 📋 確認コマンド集

### Windows (PowerShell管理者)
```powershell
# デバイス一覧
usbipd list

# 接続状態確認
usbipd list | Select-String "054c"

# 接続
usbipd attach --wsl --busid 1-5

# 切断
usbipd detach --busid 1-5
```

### WSL2 (Linux)
```bash
# USB デバイス一覧
lsusb

# カードリーダー検索
lsusb | grep -i "sony\|054c\|pasori"

# pcscd状態
sudo service pcscd status

# カード読み取りテスト
pcsc_scan
```

### Docker
```bash
# コンテナ内で実行
docker exec -it oiteru_flask /app/init_card_reader.sh

# ログ確認
docker logs oiteru_flask | grep -i "nfc\|card\|reader"
```

## 🔄 完全リセット手順

すべてうまくいかない場合:

1. **Dockerコンテナ停止**
   ```bash
   docker-compose -f docker-compose.mysql.yml down
   ```

2. **WSL2からデタッチ**
   ```powershell
   usbipd detach --busid 1-5
   ```

3. **USBケーブル抜き差し**

4. **再接続**
   ```powershell
   usbipd attach --wsl --busid 1-5
   ```

5. **Docker再起動**
   ```bash
   docker-compose -f docker-compose.mysql.yml up -d
   ```

6. **確認**
   ```bash
   docker logs oiteru_flask
   lsusb | grep Sony
   ```

## 📞 よくある質問

**Q: BUSIDはいつも同じですか?**
A: USB ポートを変えると変わる可能性があります。`usbipd list`で毎回確認してください。

**Q: 再起動後も接続は維持されますか?**
A: いいえ。PC再起動後は再度 `usbipd attach` が必要です。

**Q: 自動接続できますか?**
A: タスクスケジューラーで起動時に `attach_card_reader.bat` を実行するよう設定できます。

**Q: 複数のカードリーダーを接続できますか?**
A: はい。それぞれのBUSIDで個別に `usbipd attach` してください。

---

**作成日**: 2025年11月27日  
**対象システム**: OITELU親機 (Windows + WSL2 + Docker)
