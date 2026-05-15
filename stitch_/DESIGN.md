---
name: Lumina Analytics
colors:
  surface: '#f7f9fb'
  surface-dim: '#d8dadc'
  surface-bright: '#f7f9fb'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f4f6'
  surface-container: '#eceef0'
  surface-container-high: '#e6e8ea'
  surface-container-highest: '#e0e3e5'
  on-surface: '#191c1e'
  on-surface-variant: '#3e4850'
  inverse-surface: '#2d3133'
  inverse-on-surface: '#eff1f3'
  outline: '#6e7881'
  outline-variant: '#bec8d2'
  surface-tint: '#006591'
  primary: '#006591'
  on-primary: '#ffffff'
  primary-container: '#0ea5e9'
  on-primary-container: '#003751'
  inverse-primary: '#89ceff'
  secondary: '#006c49'
  on-secondary: '#ffffff'
  secondary-container: '#6cf8bb'
  on-secondary-container: '#00714d'
  tertiary: '#6d3bd7'
  on-tertiary: '#ffffff'
  tertiary-container: '#a986ff'
  on-tertiary-container: '#3e0097'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#c9e6ff'
  primary-fixed-dim: '#89ceff'
  on-primary-fixed: '#001e2f'
  on-primary-fixed-variant: '#004c6e'
  secondary-fixed: '#6ffbbe'
  secondary-fixed-dim: '#4edea3'
  on-secondary-fixed: '#002113'
  on-secondary-fixed-variant: '#005236'
  tertiary-fixed: '#e9ddff'
  tertiary-fixed-dim: '#d0bcff'
  on-tertiary-fixed: '#23005c'
  on-tertiary-fixed-variant: '#5516be'
  background: '#f7f9fb'
  on-background: '#191c1e'
  surface-variant: '#e0e3e5'
typography:
  title-main:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.02em
  metric-display:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.03em
  module-title:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
  body-standard:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-pill:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
  subtext:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
  title-main-mobile:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  metric-display-mobile:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 32px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 4px
  gutter: 24px
  margin: 32px
  card-padding: 24px
  container-max: 1440px
---

## Brand & Style
The design system is engineered for high-performance SaaS environments, specifically tailored for live broadcast lead attribution. The brand personality is **precise, transparent, and authoritative**, designed to instill confidence in data accuracy while maintaining an airy, non-intimidating interface.

The design style is **Modern Professional Minimalism**, drawing inspiration from toolsets like Linear and Notion. It prioritizes content over container, utilizing significant whitespace, a restrained color palette, and subtle elevation to create a focused "workplace" atmosphere. The emotional response is one of clarity and control, ensuring that even during high-velocity live broadcasts, the user feels oriented and informed.

## Colors
The palette is built on a foundation of neutral cool grays to ensure the data remains the focal point. 
- **Primary Sky Blue** is reserved for interactive states and brand-defining actions.
- **Helper Colors (Emerald and Purple)** differentiate data streams (Healthy vs. Beauty lines) without creating visual friction.
- **Semantic Status Colors** follow a logical progression from Growth (Emerald) to Critical (Red), allowing for instant peripheral recognition of performance shifts during live reviews.

## Typography
The typography system uses **Inter** for all Latin characters and numerals to ensure maximum legibility for dense data tables and metrics. For Chinese characters, the system defaults to native system sans-serif stacks (PingFang SC, Microsoft YaHei) to maintain a clean, integrated feel. 

Hierarchy is established through weight and size contrast rather than color variety. **Metrics** are bold and slightly tracked-in for impact, while **Subtext** uses a lighter gray to recede into the background.

## Layout & Spacing
The design system utilizes a **Fixed Grid** model for desktop, centered within a 1440px container to prevent excessive line lengths on ultra-wide monitors. 

- **Desktop (1280px+):** 12-column grid, 24px gutters, 32px margins.
- **Tablet (768px - 1279px):** 8-column grid, 16px gutters, 24px margins. Cards reflow to 2-column or 1-column stacks.
- **Mobile (< 767px):** 4-column fluid grid, 16px gutters, 16px margins. 

The vertical rhythm is based on a **4px baseline grid**, ensuring all components, paddings, and icon placements are mathematically consistent.

## Elevation & Depth
Depth is achieved through **Tonal Layering** rather than heavy shadows. The background sits at the lowest level (`#F8FAFC`). 

Interactive cards and containers occupy the primary surface level (`#FFFFFF`). The elevation is communicated via a double-layered shadow: 
1. A tight 1px stroke-like shadow for definition.
2. A soft, diffused 12px blur for lift. 

Borders (`#E2E8F0`) are used sparingly to define boundaries where shadows might overlap, maintaining the "Professional Airy" aesthetic. Hover states for cards increase the shadow's diffusion slightly to indicate interactivity.

## Shapes
The shape language is structured yet friendly. Main data containers and cards use a **16px (rounded-lg)** radius to soften the technical nature of the dashboard. Small UI elements like input fields, buttons, and dropdowns use an **8px (rounded-md)** radius. Status indicators and category tags use a **Full Pill** shape to distinguish them from functional buttons.

## Components
- **Cards:** White background, 16px border-radius, 24px internal padding. Title and action items are aligned to the top.
- **Buttons:** 
  - *Primary:* Sky Blue background, white text, 8px radius. 
  - *Secondary:* White background, #E2E8F0 border, #1E293B text.
- **Pill Labels:** High-contrast background (light tint of the status color) with bolded status-colored text for maximum readability.
- **Input Fields:** 1px #E2E8F0 border, 8px radius, focused state uses a 2px Sky Blue ring with 20% opacity.
- **Lists:** Clean row-based layout with subtle 1px bottom borders. Hover state uses the #F8FAFC background.
- **ECharts Integration:** Charts should use the primary/secondary/tertiary palette. Grid lines should be `#F1F5F9`, and tooltips should mirror the Card style (white, soft shadow).
- **Metric Tiles:** Large 32px bold numbers with a 12px subtext label below, often accompanied by a small Sparkline for 24h trend context.