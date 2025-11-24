# OITELUシステム トラブルシューティングガイド

## 🔧 NFCカードリーダー関連の問題

### 問題: "カードリーダー初期化失敗: [Errno 19] No such device"

#### 原因
- USBデバイスの物理的な切断
- Linuxカーネルのデバイスドライバーのクラッシュ
- USB電源供給の不安定さ
- udevルールの問題

#### 対策1: 自動復旧機能を使う（推奨）

最新版の`unit_client.py`には以下の機能が組み込まれています:
- **自動リトライ**: 初期化失敗時に最大5回まで自動的に再試行
- **複数USBパス対応**: 異なるPaSoRiモデルに対応
- **切断検知**: 実行中にデバイスが切断された場合も自動再接続
- **詳細ログ**: 親機のダッシュボードでエラー履歴を確認可能

```bash
# 最新版のunit_client.pyを実行するだけでOK
sudo python3 unit_client.py
```

#### 対策2: ハードウェアチェック

```bash
# 1. NFCリーダーが認識されているか確認
lsusb | grep -i sony
# 出力例: Bus 001 Device 005: ID 054c:06c3 Sony Corp. 

# 2. デバイスファイルの確認
ls -l /dev/bus/usb/001/005  # 上記のBus/Device番号に合わせる

# 3. nfcpyが認識できるか確認
python3 -c "import nfc; clf = nfc.ContactlessFrontend('usb'); print('OK'); clf.close()"
```

#### 対策3: USB接続の改善

1. **直接接続**: USBハブを使わず、Raspberry Piに直接接続
2. **ケーブル交換**: 短い高品質なUSBケーブルに交換
3. **ポート変更**: 別のUSBポートに挿し直してみる
4. **電源確認**: 2.5A以上のACアダプタを使用

#### 対策4: udevルールの設定

NFCリーダーへのアクセス権限を確実にするため、udevルールを追加:

```bash
# ルールファイルを作成
sudo nano /etc/udev/rules.d/99-nfc.rules

# 以下を記述（PaSoRi RC-S380の場合）
SUBSYSTEM=="usb", ATTRS{idVendor}=="054c", ATTRS{idProduct}=="06c3", MODE="0666", GROUP="plugdev"

# ルールを再読み込み
sudo udevadm control --reload-rules
sudo udevadm trigger

# カードリーダーを抜き差し
```

#### 対策5: systemdサービス化（最強の対策）

スクリプトをsystemdサービスとして登録すると、異常終了時に自動的に再起動されます:

```bash
# 1. サービスファイルをコピー
sudo cp oiteru-unit.service /etc/systemd/system/

# 2. WorkingDirectoryとExecStartのパスを自分の環境に合わせて編集
sudo nano /etc/systemd/system/oiteru-unit.service

# 3. サービスを有効化
sudo systemctl daemon-reload
sudo systemctl enable oiteru-unit.service
sudo systemctl start oiteru-unit.service

# 4. 状態確認
sudo systemctl status oiteru-unit.service

# 5. ログをリアルタイム表示
sudo journalctl -u oiteru-unit.service -f
```

これで、以下の場合に自動的に再起動されます:
- スクリプトがクラッシュした場合
- NFCリーダーのエラーで終了した場合
- Raspberry Pi再起動時

#### 対策6: カーネルモジュールのリセット

```bash
# USB関連のカーネルモジュールをリロード
sudo modprobe -r pn533_usb pn533
sudo modprobe pn533_usb pn533

# または、udevサービスを再起動
sudo systemctl restart udev
```

#### 対策7: 手動USBリセット（最終手段）

```bash
# usb-resetコマンドがない場合はインストール
sudo apt-get install usbutils

# デバイスIDを確認
lsusb | grep Sony
# 例: Bus 001 Device 005: ID 054c:06c3

# USBデバイスをリセット
sudo usbreset 054c:06c3

# または、デバイスパスでリセット
sudo usbreset /dev/bus/usb/001/005
```

---

## 🌐 ネットワーク関連の問題

### 問題: "親機に接続できません"

#### 対策
1. Tailscaleの状態を確認: `tailscale status`
2. 親機のIPアドレスが正しいか確認
3. ファイアウォール設定を確認: `sudo ufw status`
4. pingテスト: `ping <親機のIP>`

---

## ⚙️ モーター制御の問題

### 問題: "モーターが動きません"

#### 対策
1. GUI画面の「ハードウェア状態」ボタンで配線をチェック
2. 外部電源の確認（5V 2A以上）
3. コンソールログでエラーメッセージを確認

---

## 📝 ログの確認方法

### 子機側のログ
```bash
# systemdサービスのログ
sudo journalctl -u oiteru-unit.service -n 100

# リアルタイム表示
sudo journalctl -u oiteru-unit.service -f

# エラーのみフィルタ
sudo journalctl -u oiteru-unit.service -p err
```

### 親機側のログ
ブラウザで `http://<親機IP>:5000/admin` にアクセスし、「子機ログ」メニューから確認できます。

---

## 🆘 それでも解決しない場合

1. **完全再起動**: Raspberry Piとカードリーダーの電源を完全に切り、30秒待ってから再起動
2. **別のUSBポート**: すべてのUSBポートで試してみる
3. **別のカードリーダー**: 可能であれば別のNFCリーダーで試す
4. **OSの再インストール**: 最終手段として、Raspberry Pi OSのクリーンインストール
