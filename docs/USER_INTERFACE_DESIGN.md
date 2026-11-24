# 画面の設計方針（デジタル庁デザインシステム準拠）

OITERU の全画面（利用者向け画面・管理者向け画面）は Flask + Jinja2 で描画し、[デジタル庁デザインシステム（DADS）React 実装例](https://github.com/digital-go-jp/design-system-example-components-react)（参照コミット `e637c68`）に準拠した統一スタイルシート `static/css/dads-oiteru.css` を適用しています。

## スタイル構成と読み込み順

`templates/base.html` で以下の順に読み込み、従来の Material Design 3 由来スタイル（丸薬ボタンや影）を DADS 準拠のフラット・高コントラストな表現へ統一しています。

1. `static/css/style20250506.css`（既存ベース・互換維持）
2. `static/css/dads-oiteru.css`（**正規 DADS トークン・全共通コンポーネント・グローバルシェル・レガシーブリッジ**）
3. `static/css/oiteru-shell.css`（トークン互換の軽量補助層）
4. 各画面固有の補助 CSS（`static/css/public-service.css`, `static/css/register.css` — すべて `--dads-*` トークンを参照し、ヘッダーや書体を独自上書きしない）

## 情報設計（IA）と共通ナビゲーション

- **共通ヘッダー（`templates/base.html`）**
  - 左側: 東京都市大学 × 東急グループ ブランドロゴ、サービス名 `OITERU`、管理画面エリア時は `管理画面` チップを表示。
  - 右側: 非クリックの端末・時刻ステータス帯（親機 NFC リーダー・接続中子機・現在時刻）とユーティリティ操作を配置。
  - 管理者ログイン中の管理画面では、どのページからでも `利用者画面を見る` および POST 送信（CSRF 保護付き）の `ログアウト` が実行可能。
- **DADS HorizontalMenu（一次ナビゲーション）**
  - 利用者エリア: `ホーム` / `学生証の登録` / `利用状況の確認`
  - 管理エリア（ログイン中）: `業務トップ` / `補充・故障対応` / `子機監視` / `利用者管理` / `利用履歴・統計` / `システム設定`
  - 選択中タブは `4px solid #0017c1` の下線インジケーターと `aria-current="page"` / `aria-current="location"` で明示。
- **パンくずリスト（`{% block breadcrumbs %}`）**
  - 下層画面すべてで `<nav class="dads-breadcrumbs" aria-label="現在位置">` を `<main>` 先頭に配置し、現在位置と戻り先を一貫して案内。

## コンポーネント設計と操作の優先度

- **ボタン 3 階層（角丸 8px/6px・影なし）**:
  - 一次操作: `.dads-btn .dads-btn-solid`（`#0017c1`、1 カード／1 フローにつき最大 1 つ）
  - 二次操作: `.dads-btn .dads-btn-outline`（白背景・青枠）
  - 補助操作: `.dads-btn .dads-btn-text`（下線付きテキストボタン）
  - 破壊的操作: `.dads-btn .dads-btn-danger` / `.dads-btn-danger-outline`（削除・拒否など限定使用）
- **状態通知とラベル**:
  - フラッシュメッセージおよび画面内通知はカラーチップ型 `NotificationBanner`（`.dads-banner` + インライン SVG アイコン）で描画し、外部アイコンフォントへの依存を排除。
  - 稼働・在庫・利用可否は色だけでなく文字と `ChipLabel`（`.dads-chip-*`）で示す。
- **フォーム・テーブル・開閉要素**:
  - 入力欄（`.dads-input`, `.dads-select`, `.dads-textarea`）はラベル（`.dads-label`）・必須/任意表示・サポートテキスト（`.dads-support-text`）を入力欄の上部に配置。
  - オンオフ設定は DADS `SwitchOnOff`（`.dads-switch`）、補足仕様や詳細設定はネイティブ `<details class="dads-disclosure">` を使用。
- **キーボードアクセシビリティ**:
  - 全操作要素の `:focus-visible` に DADS 規定のフォーカスリング（`outline: 4px solid #000` + `outline-offset: 2px` + `box-shadow: 0 0 0 2px #ffd43d`）を適用。リンクは背景 `#ffd43d` も併用。
  - スキップリンク（`.shell-skip-link`）および `forced-colors` / `prefers-reduced-motion` に対応。
- **セキュリティ・既存 API 互換**:
  - 既存のサーバールート、NFC リーダー処理、CSRF 保護（フォーム自動注入および `fetch` ヘッダー付与）、子機監視 API をそのまま維持し、動的 DOM 描画では未エスケープの `innerHTML` 挿入を避ける。
