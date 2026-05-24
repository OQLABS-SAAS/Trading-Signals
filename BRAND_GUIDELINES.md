# DotVerse — Brand Guidelines
**Version 1.0 · Established 2026-05-15 · Source of truth for all design decisions**

---

## 1. Brand Philosophy

### The Glass Ship

Every surface in DotVerse is translucent. The constellation is always alive beneath. This is not decoration — it is philosophy.

DotVerse is a **precision intelligence instrument**, not a trading terminal. The interface exists to dissolve complexity into clarity. Like a fine mechanical watch where you can see the movement through the caseback, DotVerse lets the underlying data breathe through every panel.

The Patek Philippe reference embedded in the source code (`/* PATEK PHILIPPE */`) captures the aspiration exactly: **functional beauty with no wasted detail**. Every element earns its place. Ornamentation that does not serve the trader is removed.

### The Constellation Metaphor

The name **DotVerse** is not arbitrary:
- **Dot** = a single market signal, a data point, a price node
- **Verse** = universe of intelligence, the full field of market context

The logo is a constellation — multiple dots connected by lines of light. Each node is amber (trust, gold, value), purple (intelligence, depth), green (signal, life). DotVerse connects what the market leaves scattered.

**Tagline:** *"Connect all the dots of intelligence."*

This metaphor governs everything: charts are constellations, signals are nodes that light up, the portfolio is a star map of positions. The background `#gx` canvas animates live star particles — the constellation is never static, never dead.

### Beginners First, Advanced Second

DotVerse's defining commercial principle is that a beginner can place their first trade using DotVerse as their **only guide**. Advanced features exist but are progressively disclosed. This principle resolves every design ambiguity:

- When a feature can be terse or verbose → **verbose with progressive disclosure**
- When a default could go either way → **the safer/educational one**
- When numbers are shown → **plain English reason must accompany every number**
- When a signal fires → **entry, SL, TP, and why, in that order, always**

---

## 2. Color System

### Philosophy: Warmth Over Cold Precision

DotVerse deliberately avoids the cold blue-black of Bloomberg terminals, cold-white dashboards, and harsh neon. The palette is **warm, deep, and legible** — the color of a trading floor at 3am, not a sterile data center.

---

### Primary Tokens

| Token | Hex | RGB | Role |
|-------|-----|-----|------|
| `--bg` | `#07080c` | 7, 8, 12 | Primary background |
| `--gold` | `#c9a84c` | 201, 168, 76 | Brand primary — trust, precision, value |
| `--t1` | `#ede8d8` | 237, 232, 216 | Primary text — warm white |
| `--grn` | `#5de8a0` | 93, 232, 160 | BUY signal / positive state |
| `--red` | `#e8706e` | 232, 112, 110 | SELL signal / warning state |
| `--purp` | `#7c6fe0` | 124, 111, 224 | Accent — intelligence, depth |
| `--t2` | `~rgba(237,232,216,.55)` | — | Secondary text, labels |
| `--t3` | `~rgba(237,232,216,.35)` | — | Tertiary text, placeholders |
| `--border` | `~rgba(237,232,216,.08)` | — | Subtle dividers |

---

### Color Intent — Why Each Color Exists

#### `--bg: #07080c` — The Void with Warmth

This is **not** `#000000`. It is not `#0a0a0a`. The `0c` blue channel is intentional — it gives the black a microscopic warmth, preventing the harshness of pure black while remaining deeper than any panel or surface that sits on top of it. It is the space between stars, not a painted wall.

**Never substitute with cold blue-blacks like `#0F172A` or `#111827`.**

#### `--gold: #c9a84c` — The Brand Soul

Gold is the color of value. In trading, gold is the ultimate safe haven. In luxury goods (Patek Philippe reference), gold represents craftsmanship that compounds over time.

DotVerse gold is **muted, aged gold** — not yellow (#FFD700), not orange (#FFA500), not bright fintech amber (#F59E0B). The desaturation pulls it toward bronze, referencing **earned trust** rather than flashy promise.

This exact value (`#c9a84c`) is hard-coded in 7 alias tokens: `--gold`, `--amb`, `--cr`, `--orange`, `--crys`, `--yg`, `--topaz`. All 7 resolve to the same hex. This is intentional — different semantic roles (amber for warnings, gold for brand, crystal for highlights) all draw from the same trust reservoir.

**The gold is never used at full opacity as a fill.** It appears as:
- Gradients: `rgba(201,168,76,.28)` → `rgba(201,168,76,.14)` (button fills)
- Glows: `box-shadow: 0 0 16px rgba(201,168,76,.20)` (hover states)
- Text: `rgba(201,168,76,.9)` (active nav items, key labels)
- Solid: Only for the logo nodes and highest-emphasis data points

#### `--t1: #ede8d8` — Cream, Not Clinical White

Pure white (#ffffff) on dark backgrounds creates clinical harshness — it reads as a spreadsheet, not an intelligence instrument. `#ede8d8` is cream-tinted, pulling toward warm parchment. It is the color of a printed chart from a premium research house, not a computer screen.

**Never use `#ffffff` for body text in DotVerse UI.**

#### `--grn: #5de8a0` — Mint Signal Green

This green is **mint, not lime, not toxic green**. It is the color of a positive ECG, not a traffic light. The saturation is high enough to clearly communicate BUY/positive, but the blue-green lean prevents alarm. A beginner should feel **confidence and calm**, not urgency, when they see a BUY signal.

Note: Signal badges in practice use `#62f29d` (slightly brighter mint) — these are close enough to be treated as the same. The design intent is identical.

#### `--red: #e8706e` — Soft Caution Red

This red is **never aggressive**. It is not `#FF0000`, not `#ef4444`. The desaturation and warmth communicate **caution and attention**, not panic. A SELL signal should tell the trader to pause and think, not trigger a fight-or-flight response.

Signal badges use `#f07070` (slightly brighter) — same design intent. Warm, readable, professional.

#### `--purp: #7c6fe0` — Intelligence Accent

Purple does not appear in the logo constellation and in accent uses throughout the UI. It communicates **depth of intelligence** — the analytical layer beneath the signal. When you see purple in DotVerse, it marks something that required computation to produce (confidence labels, AI narrative, deep analysis markers).

---

### Glass Surface Formula

All panels, cards, and containers use the glass formula. This is non-negotiable:

```css
background: rgba(9, 8, 13, 0.66);
backdrop-filter: blur(18px) saturate(160%) brightness(1.05);
border: 1px solid rgba(237, 232, 216, 0.07);
border-radius: 14px;
```

The `saturate(160%)` makes the constellation background pulse through with slightly more vivid color. The `brightness(1.05)` prevents panels from feeling muddy. The `0.66` opacity is the balance point: opaque enough to read text, transparent enough to feel alive.

**Surfaces are never fully opaque.** A panel with `background: #1a1a1a` breaks the Glass Ship philosophy.

---

### Color Usage Rules

| Context | Token | Never Use |
|---------|-------|-----------|
| Body text | `--t1` | `#ffffff` |
| Secondary labels | `rgba(var(--t1), .55)` | gray-500 equivalents |
| Primary action | `--gold` at low opacity | solid gold fill |
| BUY / Positive | `--grn` | `#00ff00`, `#22c55e` |
| SELL / Warning | `--red` | `#ff0000`, `#ef4444` |
| Card backgrounds | glass formula | solid dark colors |
| Icon stroke | `currentColor` | fixed hex on icons |
| Background | `--bg` | `#000`, `#111`, cold blue-blacks |

---

## 3. Typography System

### The Hierarchy

Three typefaces. Each has exactly one role. They are never swapped.

| Font | Variable | Role | Character |
|------|----------|------|-----------|
| **Syne** | `--syne` | Display, headings, hero text | Geometric, distinctive, luxury editorial |
| **Space Grotesk** | `--ui` | UI body, labels, navigation, buttons | Clean, modern, highly legible at small sizes |
| **IBM Plex Mono** | `--mono` | Prices, numbers, code, data values | Tabular figures, professional data density |

### Why These Three

**Syne** was selected for the same reason Patek Philippe uses bespoke dials — it signals that this is not a generic product. Syne has geometric tension and editorial confidence. It is the voice of the brand when speaking about itself.

**Space Grotesk** is the workhorse. Where Syne makes statements, Space Grotesk communicates. Every navigation label, every button, every coaching message uses Space Grotesk. It is warm enough to not feel robotic, precise enough for a financial tool.

**IBM Plex Mono** is the instrument panel font. When the app shows `$61,638.50` or `RSI 67.4`, the human needs to read and compare numbers without letter-spacing confusion. IBM Plex Mono gives every digit the same width (tabular figures), meaning columns of prices never wobble.

### Type Scale

| Name | Size | Font | Weight | Use |
|------|------|------|--------|-----|
| Hero | 48–64px | Syne | 700 | Landing page hero only |
| Display | 28–36px | Syne | 600 | Section heroes, modal titles |
| Heading | 20–24px | Syne | 600 | Card headers, tab titles |
| Sub-heading | 16–18px | Space Grotesk | 600 | Form section labels |
| Body | 14–15px | Space Grotesk | 400 | Coaching text, descriptions |
| Label | 12–13px | Space Grotesk | 500 | Input labels, metadata |
| Micro | 11px | Space Grotesk | 400 | Legal, timestamps |
| Data large | 18–24px | IBM Plex Mono | 600 | Entry price, P&L, key figures |
| Data body | 13–15px | IBM Plex Mono | 400 | RSI values, ATR, all indicators |
| Data small | 11–12px | IBM Plex Mono | 400 | Sub-labels on data cells |

### Typography Rules

- Line height: **1.6** for body text, **1.3** for data/mono, **1.15** for display/hero
- Letter spacing: **-0.02em** on display/heading, **0** on body, **0.04em** on mono labels
- Never use pure `#ffffff` — always `--t1` (`#ede8d8`) or its opacity variants
- Minimum body size: **13px** (prevents iOS zoom, maintains readability on dark bg)
- Data values always in `--mono` — even when they appear inline with Space Grotesk text

---

## 4. Logo System

### Primary Mark — The Constellation

The DotVerse logo is a **constellation of dots** connected by fine lines. This is an SVG, never rasterized, never emoji-substituted.

**Node colors:**
- Amber nodes: `#b8814a` — the signal nodes, the "dots" of DotVerse
- Purple node: `#7c6fe0` — the intelligence node, the analytical center
- Green node: `#62f29d` — the signal output node, the moment of decision

**Line color:** `rgba(201, 168, 76, 0.3)` — gold at low opacity, suggesting connection without weight

### Wordmark

**DOTVERSE** set in Syne, weight 700, tracked at `0.12em`. The wordmark is always uppercase. Color is `--t1` on dark, or `--gold` as a single-color variant.

### Logo Combinations

| Variant | Use |
|---------|-----|
| Icon + Wordmark horizontal | Primary — navigation bars, auth screens |
| Icon only | Favicon, app icon, loading states |
| Wordmark only | When icon has already been established in context |

### Logo Rules

- Minimum clear space: equal to the height of one letter on all sides
- Never recolor individual constellation nodes — the amber/purple/green triad is fixed
- Never flatten the SVG into an icon font character
- Never add drop shadows or glows to the logo itself (the constellation already glows through CSS)
- Dark background only — the logo was designed for the dark Glass Ship context

---

## 5. Iconography

### System

All icons are **inline SVG, stroke-based, no fill**. They inherit color via `stroke="currentColor"`.

```svg
<!-- Standard icon template -->
<svg width="16" height="16" viewBox="0 0 16 16" fill="none"
     stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
  <!-- path here -->
</svg>
```

### Rules

- Stroke width: `2.2` for body icons, `2.5` for small inline (≤12px) icons
- Color: inherits from parent — never hardcoded hex on icon `stroke`
- No emoji as icons — ever. `⚡ ⚠ 📊 🔔` → SVG equivalents
- No fill-based icon sets (Heroicons solid, FontAwesome solid) — outline/stroke only
- Icon sets to reference: Lucide, Heroicons (outline), Feather

### Icon Color Semantics

| Color | Token | Meaning |
|-------|-------|---------|
| Amber / Gold | `--gold` | Neutral actions, brand moments, key CTAs |
| Mint Green | `--grn` | Safe, positive, confirmed, proceed |
| Soft Red | `--red` | Risk, warning, destructive action |
| Warm White | `--t1` at 60% | Secondary / informational |

---

## 6. Motion & Animation

### Philosophy

Motion in DotVerse communicates **system intelligence**. When a panel expands, it reveals — like lifting the watch caseback. When a signal fires, the badge slides in with weight. Nothing bounces, nothing spins decoratively. Every animation has a meaning.

### Token Reference

| Token | Value | Use |
|-------|-------|-----|
| Duration micro | `150ms` | Button hover states, color transitions |
| Duration standard | `280–320ms` | Panel expand/collapse, modal enter |
| Duration slow | `380–420ms` | Card slide-in, page section reveal |
| Easing enter | `cubic-bezier(.4,0,.2,1)` | Elements appearing (Material ease) |
| Easing exit | `cubic-bezier(.4,0,1,1)` | Elements leaving (faster than enter) |
| Easing spring | `cubic-bezier(.34,1.4,.64,1)` | Badge pop, success confirmation |

### Expand Animation (Panels / Cards)

The standard DotVerse expand animation uses **grid row reveal** — not `max-height` (causes jank), not `height` (requires JS measurement):

```css
.panel-body {
  display: grid;
  grid-template-rows: 0fr;
  transition: grid-template-rows 0.38s cubic-bezier(.4,0,.2,1);
}
.panel-body.open {
  grid-template-rows: 1fr;
}
.panel-inner {
  overflow: hidden;
  transform: translateY(-6px);
  opacity: 0;
  transition: transform 0.32s cubic-bezier(.4,0,.2,1),
              opacity 0.28s ease;
}
.panel-body.open .panel-inner {
  transform: translateY(0);
  opacity: 1;
}
```

Chevron rotation: `transform: rotate(180deg)` on `.open`, `transition: transform 0.32s`.

### Constellation Background

The `#gx` canvas animates continuously at `requestAnimationFrame` speed. Particles move at 0.15–0.3px/frame, connecting with gold lines when within 120px. This is the heartbeat of the app — it must never be disabled or frozen by UI state changes.

### Rules

- `prefers-reduced-motion`: honor it. Wrap all non-essential animations in the media query.
- Never animate `width`, `height`, `top`, `left` — use `transform` only
- Never block user interaction during animation
- Exit animations run at 60–70% of enter duration (exit at 220ms if enter is 320ms)

---

## 7. Component Language

### Signal Cards

The signal card is the primary output of DotVerse. It must always contain:

1. **Ticker + Asset Type** — NVDA · Stocks
2. **Signal Badge** — BUY / SELL / HOLD with color (green/red/amber)
3. **Trade Type** — Scalp / Day / Swing / Position + one-line description
4. **Confidence Ring** — percentage with CONFIRMED / LIKELY / HYPOTHESIS label
5. **Entry Price** — in `--mono`, large
6. **Stop Loss** — exact price, plain English: "if price hits $X, exit"
7. **TP1 / TP2 / TP3** — with R:R ratios
8. **Plain English Reason** — why this signal, one paragraph, no jargon

### Buttons

Three tiers only:

| Tier | Style | Use |
|------|-------|-----|
| Primary | Gold gradient + gold glow on hover | One per screen max. The main action. |
| Secondary / Ghost | Transparent bg, warm white border at 13% opacity | Supporting actions |
| Pill / Filter | Subtle bg, colored active state | Filters, timeframe selection, tab-like navigation |

Hover state for all: amber `box-shadow` glow (`0 0 14px rgba(201,168,76,.25)`). No flat state changes without the glow.

### Glass Cards

```css
/* Standard card */
background: rgba(9, 8, 13, 0.66);
backdrop-filter: blur(18px) saturate(160%) brightness(1.05);
border: 1px solid rgba(237, 232, 216, 0.07);
border-radius: 14px;
padding: 20px;
```

Elevated cards (modals, overlays): increase to `rgba(9,8,13,.80)`, reduce blur to `blur(12px)`.

### Coaching / Guidance Panels

Every form input that involves money must have a coaching state. The pattern:

1. **Header** — "Step X — [Action Name]" in gold
2. **Plain English explanation** — what this field means, why it matters
3. **Dollar examples** — "1% of $10,000 = $100 maximum loss"
4. **Helpful action** — a button that auto-fills the safe default

Never show an error as the first state. Show guidance, then surface the error if the user proceeds incorrectly.

---

## 8. The Pipeline Framework

The MARKET → SIGNAL → UNDERSTAND → SIZE → ACT journey is the backbone of DotVerse's UX. It is not a visual decorative element — it is the **mental model the app is trying to build in the trader's mind**.

| Stage | What It Means | DotVerse Feature |
|-------|---------------|------------------|
| **MARKET** | What is the broader context? Fear/greed, news, correlation | Fear & Greed panel, News feed, Correlation heatmap |
| **SIGNAL** | What is the system telling me? | Signal analysis (BUY/SELL/HOLD), Scanner, Signal history |
| **UNDERSTAND** | Why? What does this mean for my strategy? | Confidence label, plain English reason, indicators, MTF |
| **SIZE** | How much should I risk? | Calculator, position sizing, risk coaching |
| **ACT** | Execute, monitor, manage | Pine Script export, watchlist, Telegram alerts, portfolio |

Every new feature must map to one of these five stages. If it doesn't fit, question whether it belongs in DotVerse.

---

## 9. Voice & Tone

### The Brand Voice

DotVerse speaks as a **knowledgeable mentor, not an algorithm**. It teaches while it signals. It warns while it explains. It never assumes the user knows what R:R means.

| Context | Tone | Example |
|---------|------|---------|
| Signal cards | Clear, precise, educational | "BUY signal — price is above both moving averages and RSI shows momentum. Entry: $61,540." |
| Coaching text | Warm, patient, beginner-aware | "Your stop loss is the maximum you're willing to lose on this trade. At 1%, that's $100 of your $10,000." |
| Error states | Direct, solution-oriented | "SL is on the wrong side of entry for a BUY trade. Your stop loss should be below your entry price." |
| Warnings | Honest, not alarmist | "Risking 5% per trade is considered aggressive. Most professional traders use 1-2%." |
| Empty states | Helpful, forward-looking | "Run an analysis first — pick a ticker above and I'll walk you through the signal step by step." |

### Rules

- Never use jargon without a definition nearby
- Never abbreviate without spelling out first (R:R → Risk-to-Reward)
- Always pair a number with its real-world meaning ("1% = $100 on a $10,000 account")
- Never say "invalid" — say what is wrong and how to fix it
- Never leave the user without a next action

---

## 10. Pricing Page vs App

The `pricing.html` marketing page is a **separate design context**. It uses:
- Different fonts: Anybody (display), Fira Code (mono), Sora (body)
- Different gold: `#f5a623` (brighter, more commercial)
- Different bg: `#0C0A08` (slightly different warm black)

This is intentional. The marketing page is optimized for **conversion** — it needs to be punchy and direct. The app is optimized for **daily use** — it needs to be calm and precise.

**Do not import marketing page typography or gold values into the app, and vice versa.**

---

## 11. The Anti-Patterns

Things that exist elsewhere in fintech UI that DotVerse deliberately rejects:

| Anti-pattern | Why Rejected |
|---|---|
| Cold blue-black backgrounds | Feels like Bloomberg/TradingView clone. DotVerse is warm, premium. |
| Pure white text `#ffffff` | Clinical, harsh. We use cream `#ede8d8`. |
| Bright neon greens `#00ff00` | Alarm response, not confidence. Mint `#5de8a0` is calm. |
| Emoji as icons | Inconsistent rendering. SVG only. |
| Fully opaque panels | Breaks the Glass Ship. The constellation must breathe through. |
| One-number signals | "BUY" alone is not enough. Entry, SL, TP, reason — all required. |
| Jargon-only output | Beginners first. Every number needs a plain English companion. |
| Aggressive risk defaults | Default is 1%, not 5%. Safety first, education second, aggression last. |
| Features hidden behind menus | Kelly Criterion, ATR multipliers → progressive disclosure, not buried |

---

## 12. Quick Reference Card

```
BACKGROUND    #07080c   — warm deep black, never cold
BRAND GOLD    #c9a84c   — muted bronze-gold, trust and precision
TEXT PRIMARY  #ede8d8   — warm cream, never pure white
SIGNAL GREEN  #5de8a0   — mint, calm positive
SIGNAL RED    #e8706e   — soft, professional caution
ACCENT PURPLE #7c6fe0   — intelligence depth

HEADING FONT  Syne 700
BODY FONT     Space Grotesk 400/500/600
DATA FONT     IBM Plex Mono 400/600

GLASS CARD    rgba(9,8,13,.66) + blur(18px) saturate(160%) brightness(1.05)
HOVER GLOW    0 0 14px rgba(201,168,76,.25)

ANIMATION     280-320ms cubic-bezier(.4,0,.2,1) enter
              190-220ms cubic-bezier(.4,0,1,1)  exit

PIPELINE      MARKET → SIGNAL → UNDERSTAND → SIZE → ACT
TAGLINE       "Connect all the dots of intelligence."
ETHOS         Beginners first. Every number needs a reason.
REFERENCE     Patek Philippe — luxury precision, nothing wasted
```

---

*This document is the design source of truth for DotVerse. When in doubt, refer back to the Glass Ship philosophy: every surface is translucent, the constellation is always alive, and every feature teaches as it signals.*
