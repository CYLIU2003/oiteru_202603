---
name: OITERU Material
description: オイテルシステム UI デザインシステム - Material Design 3 準拠
colors:
  primary: "#1A6FB5"
  onPrimary: "#FFFFFF"
  primaryContainer: "#D3E4FF"
  onPrimaryContainer: "#001D36"
  secondary: "#535F70"
  onSecondary: "#FFFFFF"
  secondaryContainer: "#D7E3F7"
  onSecondaryContainer: "#101C2B"
  tertiary: "#6B5778"
  onTertiary: "#FFFFFF"
  tertiaryContainer: "#F2DAFF"
  onTertiaryContainer: "#251431"
  error: "#BA1A1A"
  onError: "#FFFFFF"
  errorContainer: "#FFDAD6"
  onErrorContainer: "#410002"
  success: "#2E7D32"
  onSuccess: "#FFFFFF"
  successContainer: "#C8E6C9"
  onSuccessContainer: "#0A1F0C"
  background: "#F8FAFB"
  onBackground: "#1A1C1E"
  surface: "#FFFFFF"
  onSurface: "#1A1C1E"
  surfaceVariant: "#E0E3E8"
  onSurfaceVariant: "#43474E"
  outline: "#73777F"
  outlineVariant: "#C3C7CE"
typography:
  displayLarge:
    fontFamily: "'Noto Sans JP', sans-serif"
    fontSize: 2.5rem
    fontWeight: 700
  headlineLarge:
    fontFamily: "'Noto Sans JP', sans-serif"
    fontSize: 2rem
    fontWeight: 700
  headlineMedium:
    fontFamily: "'Noto Sans JP', sans-serif"
    fontSize: 1.75rem
    fontWeight: 600
  headlineSmall:
    fontFamily: "'Noto Sans JP', sans-serif"
    fontSize: 1.5rem
    fontWeight: 600
  titleLarge:
    fontFamily: "'Noto Sans JP', sans-serif"
    fontSize: 1.25rem
    fontWeight: 600
  titleMedium:
    fontFamily: "'Noto Sans JP', sans-serif"
    fontSize: 1rem
    fontWeight: 600
  bodyLarge:
    fontFamily: "'Noto Sans JP', sans-serif"
    fontSize: 1rem
    fontWeight: 400
  bodyMedium:
    fontFamily: "'Noto Sans JP', sans-serif"
    fontSize: 0.875rem
    fontWeight: 400
  labelLarge:
    fontFamily: "'Noto Sans JP', sans-serif"
    fontSize: 0.875rem
    fontWeight: 600
  labelSmall:
    fontFamily: "'Noto Sans JP', sans-serif"
    fontSize: 0.75rem
    fontWeight: 500
elevation:
  level0: "none"
  level1: "0 1px 2px 0 rgba(0,0,0,0.05), 0 1px 3px 1px rgba(0,0,0,0.05)"
  level2: "0 1px 2px 0 rgba(0,0,0,0.08), 0 2px 6px 2px rgba(0,0,0,0.05)"
  level3: "0 4px 8px 3px rgba(0,0,0,0.08), 0 1px 3px 0 rgba(0,0,0,0.1)"
  level4: "0 6px 10px 4px rgba(0,0,0,0.08), 0 2px 6px 2px rgba(0,0,0,0.05)"
  level5: "0 8px 12px 6px rgba(0,0,0,0.08), 0 4px 8px 3px rgba(0,0,0,0.1)"
rounded:
  xs: 4px
  sm: 8px
  md: 12px
  lg: 16px
  xl: 20px
  full: 9999px
spacing:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  xxl: 48px
---

## Overview

OITERU は学内実証用 IoT システムの管理画面です。Material Design 3 の原則に基づき、
クリーンで直感的な UI を提供します。ブルーを基調とした信頼感のある配色で、
生理用品管理というデリケートな用途に配慮した落ち着いたデザインです。

## Colors

プライマリカラーは信頼と安心を象徴するブルー (#1A6FB5)。
エラーは強い警告ではなく、優しい注意として機能します。

- **Primary (#1A6FB5):** メインアクション、ヘッダー、重要な UI 要素
- **Primary Container (#D3E4FF):** 選択状態、情報カードの背景
- **Secondary (#535F70):** 補助テキスト、二次ボタン
- **Tertiary (#6B5778):** グラフや装飾的なアクセント
- **Success (#2E7D32):** 成功状態、オンライン表示、完了メッセージ
- **Error (#BA1A1A):** エラー状態、オフライン表示、警告

## Typography

日本語表示に最適化された Google Fonts `Noto Sans JP` を採用。
見出しは太字 (600-700)、本文は標準 (400)。

## Elevation

5段階の elevation で奥行きを表現。カードやダイアログに適用。

## Iconography

Google Material Symbols（`Material Symbols Outlined`）を使用し、
絵文字の代わりに統一されたアイコン体系を提供します。
