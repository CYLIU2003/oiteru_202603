# 画面の設計方針（デジタル庁デザインシステム準拠・やさしいキャンパス配色）

OITERU の全画面（利用者向け画面・管理者向け画面）は Flask + Jinja2 で描画し、[デジタル庁デザインシステム（DADS）React 実装例](https://github.com/digital-go-jp/design-system-example-components-react)（参照コミット `e637c68`）の構造・アクセシビリティ設計に、`DESIGN.md` の穏やかなキャンパス配色（Gentle Campus DADS Palette）を組み合わせた統一スタイルシート `static/css/dads-oiteru.css` を適用しています。

## スタイル構成と読み込み順

`templates/base.html` で以下の順に読み込み、従来の Material Design 3 由来スタイルを温かみのある高コントラストな DADS 表現へ統一しています。

1. `static/css/style20250506.css`（既存ベース・互換維持）
2. `static/css/dads-oiteru.css`（**正規 Gentle Campus DADS トークン・全共通コンポーネント・グローバルシェル・レガシーブリッジ**）
3. `static/css/oiteru-shell.css`（トークン互換の軽量補助層）
4. 各画面固有の補助 CSS（`static/css/public-service.css`, `static/css/register.css` — すべて `--dads-*` トークンを参照し、ヘッダーや書体を独自上書きしない）

## やさしいキャンパス配色（Gentle Campus DADS Palette）

すべての文字・ボタン組み合わせで WCAG AA（コントラスト比 4.5:1 以上）を満たしつつ、刺激の強い原色・真っ黒な罫線を排した落ち着いた配色を採用しています。

- **ベース＆ニュートラル**: 温かみのあるオフホワイト紙面（`--dads-canvas: #f6f7f4`）、白カード（`#ffffff` + 柔らかな枠線 `#d4dce0` と繊細な影）、見出し・本文には深いスレートネイビー（`--dads-gray-900: #1b3444` / `--dads-gray-800: #2b3e4a` / `--dads-gray-700: #465863`）。
- **キーカラー（キャンパス・セルリアン）**: 一次操作・強調に落ち着いた青（`--dads-blue-900: #1d6b91`、ホバー・リンク `--dads-blue-1000: #165575`、淡い背景 `--dads-blue-50: #eef5f9`）。
- **セマンティックカラー**:
  - 正常・オンライン（ボタニカルセージ）: `--dads-success-2: #2a6f56` / `--dads-green-50: #f1f7f4`
  - 注意・フォーカス補助（ウォームハニー）: `--dads-warning-2: #8a5d1e` / `--dads-yellow-300: #f4ce5c` / `--dads-yellow-400: #d9a234`
  - 警告・要対応（ウォームアプリコット）: `--dads-orange-800: #ad4f1f` / `--dads-orange-50: #fdf5ee`
  - エラー・重大（ローズテラコッタ）: `--dads-error-1: #b8424a` / `--dads-red-900: #a83a42` / `--dads-red-50: #fcf4f4`

## 情報設計（IA）と共通ナビゲーション

- **共通ヘッダー（`templates/base.html`）**
  - 左側: 東京都市大学 × 東急グループ ブランドロゴ、サービス名 `OITERU`、管理画面エリア時は `管理画面` チップを表示。
  - 右側: 淡いウォーム背景（`#f5f7f5`・枠線 `#dce3e5`）の非クリック端末・時刻ステータス帯とユーティリティ操作を配置。
  - 管理者ログイン中の管理画面では、どのページからでも `利用者画面を見る` および POST 送信（CSRF 保護付き）の `ログアウト` が実行可能。
- **DADS HorizontalMenu（一次ナビゲーション）**
  - 利用者エリア: `ホーム` / `学生証の登録` / `利用状況の確認`
  - 管理エリア（ログイン中）: `業務トップ` / `補充・故障対応` / `子機監視` / `利用者管理` / `利用履歴・統計` / `システム設定`
  - 選択中タブは `3px solid var(--dads-blue-900)` の下線インジケーターと `aria-current="page"` / `aria-current="location"` で明示。
- **パンくずリスト（`{% block breadcrumbs %}`）**
  - 下層画面すべてで `<nav class="dads-breadcrumbs" aria-label="現在位置">` を `<main>` 先頭に配置し、現在位置と戻り先を一貫して案内。

## コンポーネント設計と操作の優先度

- **ボタン 3 階層（角丸 8px/6px）**:
  - 一次操作: `.dads-btn .dads-btn-solid`（`#1d6b91`、1 カード／1 フローにつき最大 1 つ）
  - 二次操作: `.dads-btn .dads-btn-outline`（白背景・セルリアン枠）
  - 補助操作: `.dads-btn .dads-btn-text`（下線付きテキストボタン）
  - 破壊的操作: `.dads-btn .dads-btn-danger` / `.dads-btn-danger-outline`（ローズテラコッタ、削除・拒否など限定使用）
- **KPI カード・状態通知・チップ**:
  - KPI カード（`.dads-kpi-card`）は白地を基調とし、状態は左端の 4px アクセントバーと数値の落ち着いた色調のみで区別（カード全面を原色で塗らない）。
  - フラッシュメッセージおよび画面内通知はカラーチップ型 `NotificationBanner`（`.dads-banner`: 6px 左ライン + 1px 淡色枠 + 温かみのある白地 + インライン SVG アイコン）で描画。
  - 稼働・在庫・利用可否は色だけでなく文字と `ChipLabel`（`.dads-chip-*`）で示す。
- **フォーム・テーブル・開閉要素**:
  - 入力欄（`.dads-input`, `.dads-select`, `.dads-textarea`）はラベル・必須/任意表示・サポートテキストを上部に配置。
  - テーブル（`.dads-table`）はソフトなヘッダー下線（`2px solid #b4c0c6`）と行罫線（`1px solid #e3e8eb`）で視認性を確保。
  - オンオフ設定は DADS `SwitchOnOff`（`.dads-switch`）、補足仕様や詳細設定はネイティブ `<details class="dads-disclosure">` を使用。
- **キーボードアクセシビリティとセキュリティ**:
  - 全操作要素の `:focus-visible` に DADS 準拠フォーカスリング（`outline: 4px solid #1b3444` + `outline-offset: 2px` + `box-shadow: 0 0 0 2px #f4ce5c`）を適用。
  - スキップリンク（`.shell-skip-link`）、`[hidden]` 非表示保証、`forced-colors` / `prefers-reduced-motion`、既存の CSRF 保護・XSS 安全な DOM 更新を維持。
