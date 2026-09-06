---
version: alpha
name: OITERU Campus Welcome
description: A calm, welcoming student-card registration desk for Tokyo City University.
colors:
  primary: "#17364A"
  secondary: "#566873"
  tertiary: "#006DA8"
  neutral: "#F5F6F3"
  surface: "#FFFFFF"
  on-primary: "#FFFFFF"
  on-tertiary: "#FFFFFF"
  on-surface: "#17364A"
  muted-on-primary: "#C4D5DF"
  outline: "#DCE3E5"
  accent: "#00A7EB"
  success: "#25634C"
  success-container: "#EDF5F0"
  warning: "#80511B"
  warning-container: "#FBF2E6"
typography:
  headline-lg:
    fontFamily: "Yu Gothic, Hiragino Sans, sans-serif"
    fontSize: 44px
    fontWeight: 700
    lineHeight: 1.5
    letterSpacing: 0.03em
  headline-md:
    fontFamily: "Yu Gothic, Hiragino Sans, sans-serif"
    fontSize: 24px
    fontWeight: 700
    lineHeight: 1.5
  body-md:
    fontFamily: "Yu Gothic, Hiragino Sans, sans-serif"
    fontSize: 15px
    fontWeight: 500
    lineHeight: 1.9
  label-md:
    fontFamily: "Yu Gothic, Hiragino Sans, sans-serif"
    fontSize: 12px
    fontWeight: 500
    lineHeight: 1.6
rounded:
  sm: 8px
  md: 16px
  full: 9999px
spacing:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  section: 48px
components:
  page:
    backgroundColor: "{colors.neutral}"
    textColor: "{colors.primary}"
  welcome-caption:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.muted-on-primary}"
  decorative-mark:
    backgroundColor: "{colors.accent}"
  button-primary:
    backgroundColor: "{colors.tertiary}"
    textColor: "{colors.on-tertiary}"
    rounded: "{rounded.sm}"
    height: 56px
    padding: 16px
  button-primary-hover:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
  welcome-panel:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    padding: 40px
  registration-panel:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.on-surface}"
    padding: 40px
  reader-ready:
    backgroundColor: "{colors.success-container}"
    textColor: "{colors.success}"
  reader-offline:
    backgroundColor: "{colors.warning-container}"
    textColor: "{colors.warning}"
---

## Overview

A calm university service desk: clear, welcoming, and purposeful. Scope is the
parent's `/register` screen only; existing administration screens retain their
own styling. Follow https://github.com/google-labs-code/design.md for the format.
The official university logo anchors identity. 生理用品配布 is the visible header label,
using #3E3A39 to match the university wordmark's lettering,
and locally served Kosugi Maru Regular for a softer rounded appearance,
and student-card registration is the sole primary task. The deep blue panel
offers a quiet visual anchor alongside a white, action-oriented workspace.

## Colors

Primary is deep campus navy for headings and the welcome panel. Neutral is a
warm off-white page background. Tertiary is the accessible blue for the one
primary button and links. Accent is the official logo's bright blue, used only
for decorative details. Secondary is readable supporting text. Success and
warning pairs express actual reader availability in text as well as color.

## Typography

Use system Japanese sans-serif fonts, without requiring an external font for
the registration content. Headlines are bold; body copy uses medium weight.
The main heading is 44px on desktop, 34px on tablet, and 30px on mobile. Body text is 15px with
1.9 line height. English labels are small supplementary accents; every action
and instruction must be understandable in Japanese. Keep copy to the purpose,
three steps (prepare the card, place it, and press register), reader state, and navigation.
Each step has one short explanatory sentence.
The purpose sentence below the main heading uses muted-on-primary text at 15px
(14px on mobile), weight 500. Keep it subordinate to the bold white heading.
Omit promotional slogans, duplicate explanations, and breadcrumbs.

## Layout

Center content at a maximum width of 1080px. A compact university header
precedes a two-column registration workspace, 46% welcome / 54% action.
At 720px and below, stack the panels and remove the decorative illustration
to keep the action close to the heading. Use a 4px/8px spacing rhythm and 40px
vertical / 44px horizontal desktop panel padding, reduced to 24px on mobile. Place the three concise
steps directly above the reader notice and primary button. Supporting links
follow the workspace. Hardware telemetry is visually secondary in the header.
A compact header clock shows the browser's local date, weekday, and time with
seconds. Reuse the existing one-second update and tabular numerals; keep its
background transparent and live announcements off to avoid repeated speech.

## Elevation & Depth

Use one subtle workspace shadow (0 16px 48px rgba(23,54,74,.06)) and tonal
separation. Avoid stacking multiple raised cards or thick colored borders.

## Shapes

The outer workspace uses a 16px radius; the primary button and reader notice
use 8px. The student-card drawing
is illustrative, uses no personal data, and does not reproduce an actual ID.
Use only a Japanese student-ID title, portrait silhouette, and two placeholder
lines on a card tilted -8 degrees, with two shadows visible against navy:
8px 18px 18px rgba(0,0,0,.38) and 16px 30px 40px rgba(0,0,0,.24).
Omit small labels. Behind the card, use one faint 300px circular outline,
a partial 248px inner arc, a soft blue radial tint, and a small sparse dot
pattern. Keep these decorative elements behind the card, noninteractive, and
hidden with the illustration on mobile. Avoid payment-card
chips and payment/contactless symbols; the illustration must read as a student ID.

## Components

Keep the official university logo unmodified. The white action panel contains
an ordered list, a factual reader notice, and exactly one full-width primary
button: POST registration when connected, GET recheck when disconnected.
Preserve explicit CSRF protection and server flash messages. Readiness is a
page-load snapshot; label it as such, since the header polls independently.
Buttons have a minimum 56px height; links a visible focus indicator. Support
keyboard navigation and reduced-motion preferences. No new loading animation
or automatic submission is needed.

## Do's and Don'ts

- Do keep the registration action visible in a 1366 × 768 desktop viewport.
- Do use real connection state and preserve server-side errors and results.
- Do maintain WCAG AA text contrast and avoid horizontal overflow at 320px.
- Don't use large clocks, English-only controls, or decorative status cards.
- Don't add stock, privacy, timing, or registration-success claims without evidence.
- Don't spread this visual update into authentication, database, or device logic.
