# DotVerse — Mobile App Design Brief

## What is DotVerse?

DotVerse is an AI-powered trading signals platform. It scans markets, finds trading opportunities, explains WHY each trade makes sense in plain English, and helps you execute it. Built for beginners who want institutional-grade analysis without the jargon.

## Target User

Retail traders who:
- Don't have time to stare at charts all day
- Want clear, explained trade ideas (not just buy/sell signals)
- Need to understand WHY before risking money
- Want risk management built-in, not an afterthought

## Core User Flow (6-Step Pipeline)

The app is built around a pipeline. Each step feeds into the next:

### Step 1: Market
"Is now a good time to trade?"
Global market conditions: volatility, session status (Asian/London/NY open/closed), trending assets, macro signals (VIX, regime detection).

### Step 2: Signal
"Find your next trade"
Scan results shown as cards. Each card shows:
- Ticker + direction (BUY/SELL/HOLD)
- Confidence score (as a colored ring)
- Quality score (as a colored ring with breakdown on tap)
- Risk/Reward ratio
- Timeframe (Scalp/Day/Swing/Position)
- Entry price, Stop Loss, Take Profit
- Spread cost indicator
- One-line reason for the trade
- SMC patterns detected (FVG, liquidity grab, displacement, CHOCH)

### Step 3: Understand
"Know what you're entering"
Deep dive on a selected signal:
- SMC structure analysis (which smart money patterns support/oppose)
- Risk/Reward breakdown
- Market context (regime, trend alignment)
- Strategy notes

### Step 4: Verdict
"Multi-agent AI analysis"
Each signal gets analyzed by independent AI agents covering:
- Technical analysis verdict
- Risk assessment
- Market context
- Final consensus

### Step 5: Size
"How much to risk"
Position sizing with:
- Account balance input
- Risk percentage (1-2% recommended)
- Calculated position size based on SL distance
- Kelly criterion / optimal f (advanced toggle)

### Step 6: Act
"Place your trade"
- MT5 account status (balance, equity, connection)
- Open positions
- One-tap execution (or manual entry instructions)
- Automation rules: set stop loss, take profit, trailing stop

## Design Direction: Linear-Inspired Dark Theme

### Overall Vibe
Near-black canvas with content emerging from darkness. Ultra-clean, minimal, precise. Think Linear.app but for trading — signals and numbers should feel authoritative and calm, not noisy.

### Color Palette

**Backgrounds:**
- Page background: #08090a (near-black)
- Card/surface: rgba(255,255,255,0.02) to rgba(255,255,255,0.05)
- Elevated surfaces: #191a1b

**Text:**
- Primary: #f7f8f8 (near-white)
- Secondary: #d0d6e0 (silver-gray)
- Tertiary: #8a8f98 (muted gray)
- Labels/disabled: #62666d

**Accent (single brand color, used sparingly):**
- Primary CTA: #5e6ad2 (indigo)
- Interactive elements: #7170ff (violet)
- Hover: #828fff

**Status colors (for signals only):**
- BUY: #5de8a0 (green)
- SELL: #e8706e (red)
- HOLD: #c9a84c (amber)

**Borders:**
- Default: rgba(255,255,255,0.08) — semi-transparent white, never solid dark
- Subtle: rgba(255,255,255,0.05)

### Typography

- Primary font: Inter (all text)
- Mono font: JetBrains Mono (numbers, prices, scores)
- Default weight: Inter 510 (between regular 400 and medium 500) — this is the "signature" Linear weight
- Headings: weight 590 (semibold)
- Body: weight 400
- Sizes: 10px (micro labels) → 14px (body) → 18px (card titles) → 24px+ (screen titles)
- Tight letter-spacing on large text, normal on small

### Component Style

**Cards containing signal data:**
- Translucent background (never solid white)
- Thin semi-transparent white border (1px, rgba(255,255,255,0.08))
- Rounded corners (8px)
- Subtle top accent stripe colored by signal direction (green for BUY, red for SELL)

**Buttons:**
- Primary: indigo background (#5e6ad2), white text, 8px radius
- Secondary: transparent, thin border, subtle white bg on hover
- No heavy shadows — use background luminance for elevation

**Score rings:**
- SVG circular progress rings for confidence and quality scores
- Dynamic color based on score tier (green/lime/amber/red)
- Score number displayed centered inside the ring

## Mobile Navigation

Bottom tab bar with 4-5 tabs:
1. **Market** — session status, overview, trending
2. **Signals** — scan results, signal cards (the main screen)
3. **Portfolio** — PnL, positions, performance
4. **Automations** — saved trading rules, bots
5. **Settings** — account, exchange connections, preferences

Pipeline steps accessible from a signal card: tap a card → opens detail view with step selector (Understand → Verdict → Size → Act) as horizontal tabs or a step indicator at the top.

## Key Screens to Design

1. **Onboarding** — "How do you trade?" picker (Beginner/Trader/Pro)
2. **Dashboard** — market conditions, recent signals, quick analyze
3. **Signal Feed** — scrollable list of signal cards with filters (timeframe, asset class)
4. **Signal Detail** — deep dive with pipeline step navigation
5. **Portfolio** — PnL chart, win rate, drawdown, open positions
6. **Automations** — saved rules, active bots
7. **Settings** — exchange connections (MT5, Binance, etc.), account, notification prefs

## Competitor Examples (for reference)

Look at the screenshots in design-refs/ folder on the Desktop:
- Linear.app — clean dark theme, precise UI (the primary inspiration)
- Vercel — black/white minimal, serious institutional feel
- For competitor trading apps: TradingView mobile, 3Commas, Coinrule

## Design Principles

1. **Dark-first** — not a light app with a dark mode toggle. The darkness IS the design.
2. **One brand color** — indigo/violet used ONLY for CTAs and primary actions. Everything else is grayscale.
3. **Numbers should feel authoritative** — mono font, clean alignment, no decorative fluff
4. **Beginner-friendly** — every label in plain English. No "confluence", "regime", "SMC divergence" without immediate plain-English explanation
5. **Status at a glance** — BUY = green, SELL = red, HOLD = amber. Even on a tiny phone screen, the direction is obvious
6. **Progressive disclosure** — surface level shows the decision (BUY/SELL with score). Tap for the explanation. Go deeper for the analysis.

## Tech Stack (for Rocket)

- Mobile: React Native or Flutter (preference?)
- API: existing DotVerse backend at dot-verse.up.railway.app
- Auth: Google OAuth (existing)
- Real-time: WebSocket for live signal updates
- Design system: follow the tokens above for consistent look
