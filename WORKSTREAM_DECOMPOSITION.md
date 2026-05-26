# DotVerse Build Decomposition — Parallel Workstream Plan
# Generated 2026-05-26 | Excludes Stripe (7.1) per instructions
#
# Models: Pro = DeepSeek V4 Pro (arch, logic, planning)
#          Flash = DeepSeek V4 Flash (code, file ops, speed)
#          Qwen = Qwen 3.5 Plus (UI/UX critique, design)

================================================================================
WAVES OVERVIEW
================================================================================

Wave 0 (No Dependencies — Start Immediately):
├── W0-A: Performance Dashboard backend (4.1-PnL, 4.2-Sharpe, 4.3-Drawdown, 4.4-Heatmap)
├── W0-B: Performance Dashboard frontend (4.1-4.4 cards/charts)
├── W0-C: Backtesting UI frontend (6.2)
├── W0-D: WebSocket real-time feed (6.1)
├── W0-E: Free tier caps — beyond 5/day (7.2)
├── W0-F: Mobile responsive layout (8.1)
├── W0-G: On-chain + sentiment data pipeline (9.2)
├── W0-H: Public API (9.3)

Wave 1 (P1 Exchange — Sequential Chain):
├── W1-A: Binance trading execution (1.1) ───┐
├── W1-B: Coinbase trading execution (1.2) ─┤ parallel
│                                          │
├── W1-C: Exchange order UI (1.3) ←────────┘ depends on 1.1+1.2
├── W1-D: One-click signal-to-order (1.4) ← depends on 1.3

Wave 2 (P2 AI/ML — Sequential Chain):
├── W2-A: Outcome-labeled dataset pipeline (2.1) ──┐
├── W2-B: Isotonic regression calibration (2.2) ───┤ sequential
├── W2-C: Qwen signal quality review (2.3) ────────┤
├── W2-D: Calibration dashboard card (2.4) ────────┘

Wave 3 (Phase 2-3 Dependencies):
├── W3-A: Push alerts — web + mobile (6.3) ← better after 6.1 but not blocked
├── W3-B: Tier-gated feature flags (7.3) ← depends on 7.2 (tier caps)
├── W3-C: PWA offline mode (8.2) ← depends on 8.1 (mobile layout)

Wave 4 (Phase 5 Dependencies):
└── W4-A: ML parameter optimization (9.1) ← depends on 2.1 (labeled data)

================================================================================
DETAILED WORKSTREAM TABLE
================================================================================

┌────────┬────────────────────────────────┬──────────┬───────────┬─────────────┬──────────────┬──────────────┐
│  ID    │ Item                           │ Effort   │ Model     │ Blocked By  │ Parallel w/  │ Feasibility  │
├────────┼────────────────────────────────┼──────────┼───────────┼─────────────┼──────────────┼──────────────┤
│        │                                │          │           │             │              │              │
│  W0-A  │ Performance Dashboard BACKEND  │ 3-4 days │           │             │              │              │
│        │ ────────────────────────────── │          │           │             │              │              │
│ A1     │ /api/signals/performance-      │ 2-3 days │ Pro+Flash │ None        │ W0-B,W0-*    │ 1 session    │
│        │ metrics (Sharpe, WR, PF,      │          │           │             │              │              │
│        │ avg R, monthly matrix)         │          │ Pro:      │             │              │              │
│        │                                │          │  metrics   │             │              │              │
│        │                                │          │  formula   │             │              │              │
│        │                                │          │  design    │             │              │              │
│        │                                │          │ Flash:     │             │              │              │
│        │                                │          │  endpoint  │             │              │              │
│        │                                │          │  code,     │             │              │              │
│        │                                │          │  SQL       │             │              │              │
│        │                                │          │  query     │             │              │              │
│        │                                │          │  assembly  │             │              │              │
├────────┼────────────────────────────────┼──────────┼───────────┼─────────────┼──────────────┼──────────────┤
│  W0-B  │ Performance Dashboard FRONTEND │ 3-4 days │           │             │              │              │
│ B1     │ PnL/equity curve (Lightweight  │ 1-2 days │ Qwen+Flash│ W0-A        │ W0-A,W0-*    │ 1 session    │
│        │ Charts canvas)                 │          │           │ (endpoint)  │ (after A)    │              │
│        │                                │          │ Flash:    │             │              │              │
│        │                                │          │  chart     │             │              │              │
│        │                                │          │  wiring    │             │              │              │
│        │                                │          │ Qwen:     │             │              │              │
│        │                                │          │  layout    │             │              │              │
│        │                                │          │  review    │             │              │              │
│ B2     │ Sharpe + WR stats row (4 cards)│ 1 day    │ Flash     │ W0-A        │ B1,B3,B4     │ 1 session    │
│ B3     │ Drawdown chart (separate pane) │ 1 day    │ Flash     │ B1 (pane)   │ B2,B4        │ 1 session    │
│        │                                │          │           │ + W0-A      │              │              │
│ B4     │ Monthly returns heatmap        │ 1 day    │ Flash     │ W0-A        │ B2,B3        │ 1 session    │
│        │ (calendar grid)               │          │ + Qwen    │             │              │              │
│        │                                │          │ review    │             │              │              │
├────────┼────────────────────────────────┼──────────┼───────────┼─────────────┼──────────────┼──────────────┤
│  W0-C  │ Backtesting UI (6.2)           │ 3-4 days │           │             │              │              │
│ C1     │ Strategy picker dropdown       │ 1 day    │ Flash     │ None        │ W0-D,W0-*    │ 1 session    │
│        │ (7 lenses)                     │          │           │ (backend    │              │              │
│        │                                │          │           │  exists)    │              │              │
│ C2     │ Results dashboard (WR, PF,     │ 2-3 days │ Pro+Flash │ C1          │ W0-D,W0-*    │ 1 session    │
│        │ max DD, trade list)            │          │           │             │              │              │
│        │                                │          │ Pro:      │             │              │              │
│        │                                │          │  results   │             │              │              │
│        │                                │          │  schema    │             │              │              │
│        │                                │          │  layout    │             │              │              │
│        │                                │          │ Flash:     │             │              │              │
│        │                                │          │  poll      │             │              │              │
│        │                                │          │  wiring,   │             │              │              │
│        │                                │          │  charts    │             │              │              │
│ C3     │ Job status polling + progress  │ 1 day    │ Flash     │ C1          │ C2           │ 1 session    │
│        │ UI (/backtest/result/{job_id}) │          │           │             │              │              │
│        │                                │          │           │             │              │              │
│        │ NOTE: C1-C3 feasible as single │          │           │             │              │              │
│        │ session (backend exists:       │          │           │             │              │              │
│        │ /backtest/enqueue + RQ +       │          │           │             │              │              │
│        │ /backtest/result/<job_id>)     │          │           │             │              │              │
├────────┼────────────────────────────────┼──────────┼───────────┼─────────────┼──────────────┼──────────────┤
│  W0-D  │ WebSocket Real-Time Feed (6.1) │ 4-5 days │ Pro       │ None        │ W0-C,W0-*    │ 2 sessions   │
│        │                                │          │           │             │              │              │
│        │ Pro designs architecture:      │          │           │             │              │              │
│        │ - Binance WS for crypto        │          │           │             │              │              │
│        │ - Twelve Data WS for stocks/   │          │           │             │              │              │
│        │   forex                        │          │           │             │              │              │
│        │ - Socket.IO or SSE bridge to   │          │           │             │              │              │
│        │   frontend                     │          │           │             │              │              │
│        │ - Replace setInterval 60s      │          │           │             │              │              │
│        │   polling                      │          │           │             │              │              │
│        │                                │          │           │             │              │              │
│        │ Session 1: architecture +      │          │           │             │              │              │
│        │   Binance WS backend (Pro)     │          │           │             │              │              │
│        │ Session 2: TwelveData WS,      │          │           │             │              │              │
│        │   frontend bridge, cleanup     │          │           │             │              │              │
├────────┼────────────────────────────────┼──────────┼───────────┼─────────────┼──────────────┼──────────────┤
│  W0-E  │ Free Tier Caps Beyond 5/Day    │ 2-3 days │ Flash     │ None        │ All W0       │ 1 session    │
│        │ (7.2)                          │          │           │ (5/day cap  │              │              │
│        │                                │          │           │  exists at  │              │              │
│        │ Caps to add:                   │          │           │  line 9425) │              │              │
│        │ - 3 backtests/day              │          │           │             │              │              │
│        │ - 2 active watches cap         │          │           │             │              │              │
│        │ - 3 positions cap              │          │           │             │              │              │
│        │ - 1 asset class cap            │          │           │             │              │              │
│        │ - 1h timeframe only            │          │           │             │              │              │
│        │                                │          │           │             │              │              │
│        │ All use existing pattern:      │          │           │             │              │              │
│        │ Redis counter + `require_tier` │          │           │             │              │              │
│        │ decorator + upgrade prompts    │          │           │             │              │              │
├────────┼────────────────────────────────┼──────────┼───────────┼─────────────┼──────────────┼──────────────┤
│  W0-F  │ Mobile Responsive Layout (8.1) │ 4-5 days │ Qwen+Flash│ None        │ All non-UI   │ 1 session    │
│        │                                │          │           │ (standalone)│              │ (design)     │
│        │                                │          │ Qwen:     │             │              │ +1 session   │
│        │                                │          │  design    │             │              │ (impl)       │
│        │                                │          │  audit +   │             │              │              │
│        │                                │          │  CSS wire  │             │              │              │
│        │                                │          │ Flash:     │             │              │              │
│        │                                │          │  implement │             │              │              │
│        │                                │          │  break-    │             │              │              │
│        │                                │          │  points,   │             │              │              │
│        │                                │          │  bottom     │             │              │              │
│        │                                │          │  tab bar,  │             │              │              │
│        │                                │          │  stack      │             │              │              │
│        │                                │          │  cards      │             │              │              │
│        │                                │          │  vertically │             │              │              │
│        │                                │          │             │              │              │              │
│        │ Better as 2 sessions: Session  │          │           │             │              │              │
│        │ 1 = Qwen design pass on all    │          │           │             │              │              │
│        │ pages → CSS/template changes.  │          │           │             │              │              │
│        │ Session 2 = Flash implementation│         │           │             │              │              │
├────────┼────────────────────────────────┼──────────┼───────────┼─────────────┼──────────────┼──────────────┤
│  W0-G  │ On-Chain + Sentiment Data (9.2)│ 5-7 days │ Pro+Flash │ None        │ All W0       │ 2 sessions   │
│        │                                │          │           │ (Elite tier │              │              │
│        │                                │          │           │  gating     │              │              │
│        │                                │          │           │  optional   │              │              │
│        │                                │          │           │  at first)  │              │              │
│        │ Pro designs:                   │          │           │             │              │              │
│        │ - Glassnode/CoinMetrics API    │          │           │             │              │              │
│        │   schema + normalize           │          │           │             │              │              │
│        │ - Social sentiment multiplexer │          │           │             │              │              │
│        │   (Twitter/LunarCrush)         │          │           │             │              │              │
│        │ - UNDERSTAND card wireframes   │          │           │             │              │              │
│        │ Flash implements:              │          │           │             │              │              │
│        │ - API clients, caching,        │          │           │             │              │              │
│        │   frontend cards               │          │           │             │              │              │
│        │                                │          │           │             │              │              │
│        │ Session 1 (Pro): architecture, │          │           │             │              │              │
│        │   API research, schema design  │          │           │             │              │              │
│        │ Session 2 (Flash): full        │          │           │             │              │              │
│        │   implementation               │          │           │             │              │              │
├────────┼────────────────────────────────┼──────────┼───────────┼─────────────┼──────────────┼──────────────┤
│  W0-H  │ Public API (9.3)               │ 3-4 days │ Pro+Flash │ None        │ All W0       │ 1 session    │
│        │                                │          │           │ (Elite tier │              │              │
│        │                                │          │           │  gating     │              │              │
│        │                                │          │           │  optional   │              │              │
│        │                                │          │           │  at first)  │              │              │
│        │ Pro designs:                   │          │           │             │              │              │
│        │ - OpenAPI spec                 │          │           │             │              │              │
│        │ - API key model + generation   │          │           │             │              │              │
│        │ - Rate limiting per tier       │          │           │             │              │              │
│        │ - Endpoint design              │          │           │             │              │              │
│        │ Flash implements:              │          │           │             │              │              │
│        │ - Routes, key mgmt, docs       │          │           │             │              │              │
├────────┼────────────────────────────────┼──────────┼───────────┼─────────────┼──────────────┼──────────────┤
│        │                                │          │           │             │              │              │
│  W1-A  │ Binance Spot Trading (1.1)     │ 5-7 days │ Pro+Flash │ None        │ W1-B,W0-all  │ 1 session    │
│        │                                │          │           │             │              │              │
│        │ Pro: API auth flow (HMAC       │          │           │             │              │              │
│        │ SHA256), order state machine,  │          │           │             │              │              │
│        │ error taxonomy, rate limiting   │          │           │             │              │              │
│        │ Flash: endpoint code, key      │          │           │             │              │              │
│        │ mgmt (ExchangeKey model        │          │           │             │              │              │
│        │ exists + Fernet encryption     │          │           │             │              │              │
│        │ ready)                         │          │           │             │              │              │
│        │                                │          │           │             │              │              │
│        │ Existing infra:                │          │           │             │              │              │
│        │ - fetch_binance_ohlcv exists   │          │           │             │              │              │
│        │ - _to_binance_symbol exists    │          │           │             │              │              │
│        │ - ExchangeKey table exists     │          │           │             │              │              │
│        │ - Fernet encryption exists     │          │           │             │              │              │
│        │ - _browser_session exists      │          │           │             │              │              │
├────────┼────────────────────────────────┼──────────┼───────────┼─────────────┼──────────────┼──────────────┤
│  W1-B  │ Coinbase Advanced Trade (1.2)  │ 5-7 days │ Pro+Flash │ None        │ W1-A,W0-all  │ 1 session    │
│        │                                │          │           │             │              │              │
│        │ Pro: CB Advanced Trade API auth│          │           │             │              │              │
│        │ (CB-ACCESS-* headers), order   │          │           │             │              │              │
│        │ lifecycle, fills feed          │          │           │             │              │              │
│        │ Flash: endpoints, same         │          │           │             │              │              │
│        │ ExchangeKey model reuse        │          │           │             │              │              │
│        │                                │          │           │             │              │              │
│        │ PARALLEL with W1-A — no shared │          │           │             │              │              │
│        │ code beyond ExchangeKey model  │          │           │             │              │              │
│        │ (both read from it, neither    │          │           │             │              │              │
│        │ modifies it)                   │          │           │             │              │              │
├────────┼────────────────────────────────┼──────────┼───────────┼─────────────┼──────────────┼──────────────┤
│  W1-C  │ Exchange Order UI — ACT Tab    │ 3-4 days │ BLOCKED   │ W1-A + W1-B │ W0-all       │ 1 session    │
│        │ (1.3)                          │          │           │ (MUST have  │              │              │
│        │                                │          │           │  backend    │              │              │
│        │                                │          │           │  endpoints) │              │              │
│        │                                │          │ Qwen+Flash│             │              │              │
│        │ Qwen: order ticket layout,     │          │           │             │              │              │
│        │ confirm dialog design,         │          │           │             │              │              │
│        │ exchange selector UX           │          │           │             │              │              │
│        │ Flash: wire all endpoints,     │          │           │             │              │              │
│        │ reuse sizeTab position-sizing, │          │           │             │              │              │
│        │ order status feed              │          │           │             │              │              │
├────────┼────────────────────────────────┼──────────┼───────────┼─────────────┼──────────────┼──────────────┤
│  W1-D  │ One-Click Signal-to-Order      │ 2-3 days │ BLOCKED   │ W1-C        │ None          │ 1 session    │
│        │ (1.4)                          │          │           │ (needs      │              │              │
│        │                                │          │           │  order UI)  │              │              │
│        │                                │          │ Flash     │             │              │              │
│        │ Simple feature: button on      │          │           │             │              │              │
│        │ signal cards → pre-fill order  │          │           │             │              │              │
│        │ ticket (entry/stop/tp from     │          │           │             │              │              │
│        │ signal). Pure frontend wiring  │          │           │             │              │              │
│        │ once 1.3 exists.               │          │           │             │              │              │
├────────┼────────────────────────────────┼──────────┼───────────┼─────────────┼──────────────┼──────────────┤
│        │                                │          │           │             │              │              │
│  W2-A  │ Outcome-Labeled Dataset (2.1)  │ 2-3 days │ Pro+Flash │ None        │ W0-all       │ 1 session    │
│        │                                │          │           │ (uses       │              │              │
│        │                                │          │           │  existing   │              │              │
│        │                                │          │           │  Signal-    │              │              │
│        │                                │          │           │  History)   │              │              │
│        │ Pro: CalibrationLabel table    │          │           │             │              │              │
│        │ schema, feature vector design  │          │           │             │              │              │
│        │ (confidence_raw, indicators,   │          │           │             │              │              │
│        │ regime, spread_cost → WIN/LOSS)│          │           │             │              │              │
│        │ Flash: SQLAlchemy model,       │          │           │             │              │              │
│        │ migration, backfill script,    │          │           │             │              │              │
│        │ minimum-50 assertion           │          │           │             │              │              │
├────────┼────────────────────────────────┼──────────┼───────────┼─────────────┼──────────────┼──────────────┤
│  W2-B  │ Isotonic Regression (2.2)      │ 3-4 days │ BLOCKED   │ W2-A        │ W0-all       │ 1 session    │
│        │                                │          │           │ (needs      │              │              │
│        │                                │          │           │  labeled    │              │              │
│        │                                │          │           │  data)      │              │              │
│        │ Pro: isotonic fit algorithm,   │          │           │             │              │              │
│        │ calibration curve math,        │          │           │             │              │              │
│        │ weekly recalibration schedule   │          │           │             │              │              │
│        │ (APScheduler)                  │          │           │             │              │              │
│        │ Flash: numpy/scipy impl,       │          │           │             │              │              │
│        │ calibrated_confidence field,   │          │           │             │              │              │
│        │ cache invalidation             │          │           │             │              │              │
├────────┼────────────────────────────────┼──────────┼───────────┼─────────────┼──────────────┼──────────────┤
│  W2-C  │ Qwen Signal Quality Review     │ 2-3 days │ BLOCKED   │ W2-B (needs │ None          │ 1 session    │
│        │ (2.3)                          │          │           │  calibrated │              │              │
│        │                                │          │           │  conf.)     │              │              │
│        │                                │          │ Pro+Qwen  │             │              │              │
│        │ Pro: prompt engineering,       │          │           │             │              │              │
│        │ response schema, 1hr cache     │          │           │             │              │              │
│        │ Qwen: review prompt quality,   │          │           │             │              │              │
│        │ validate output format, tune   │          │           │             │              │              │
│        │ Flash: API call wiring, caching│          │           │             │              │              │
├────────┼────────────────────────────────┼──────────┼───────────┼─────────────┼──────────────┼──────────────┤
│  W2-D  │ Calibration Dashboard Card     │ 1-2 days │ BLOCKED   │ W2-B        │ W0-all       │ 1 session    │
│        │ (2.4)                          │          │           │             │              │              │
│        │                                │          │ Qwen+Flash│             │              │              │
│        │ Qwen: reliability curve chart  │          │           │             │              │              │
│        │ design, calibration error UX   │          │           │             │              │              │
│        │ Flash: wire to PERFORMANCE tab,│          │           │             │              │              │
│        │ "not enough data" state        │          │           │             │              │              │
├────────┼────────────────────────────────┼──────────┼───────────┼─────────────┼──────────────┼──────────────┤
│        │                                │          │           │             │              │              │
│  W3-A  │ Push Alerts Web + Mobile (6.3) │ 2-3 days │ Flash     │ Better with │ All W0-3     │ 1 session    │
│        │                                │          │           │ W0-D (WS)   │              │              │
│        │                                │          │           │ but NOT     │              │              │
│        │                                │          │           │ blocked     │              │              │
│        │ Browser push (Service Worker   │          │           │             │              │              │
│        │ + Web Push API), threshold     │          │           │             │              │              │
│        │ alerts, daily digest email.    │          │           │             │              │              │
│        │ _push_notification function    │          │           │             │              │              │
│        │ already exists + Telegram.     │          │           │             │              │              │
│        │ PWA manifest exists.           │          │           │             │              │              │
├────────┼────────────────────────────────┼──────────┼───────────┼─────────────┼──────────────┼──────────────┤
│  W3-B  │ Tier-Gated Feature Flags (7.3) │ 1-2 days │ BLOCKED   │ W0-E        │ W3-A         │ 1 session    │
│        │                                │          │           │ (tier caps  │              │              │
│        │                                │          │           │  define     │              │              │
│        │                                │          │           │  what's     │              │              │
│        │                                │          │           │  gated)     │              │              │
│        │ Pro+Flash: design + implement  │          │           │             │              │              │
│        │ /api/user/features endpoint,   │          │           │             │              │              │
│        │ frontend flag reader, replace  │          │           │             │              │              │
│        │ all hardcoded tier checks.     │          │           │             │              │              │
│        │ require_tier decorator already │          │           │             │              │              │
│        │ exists as foundation.          │          │           │             │              │              │
├────────┼────────────────────────────────┼──────────┼───────────┼─────────────┼──────────────┼──────────────┤
│  W3-C  │ PWA Offline Mode (8.2)         │ 2-3 days │ BLOCKED   │ W0-F        │ W3-A,W3-B    │ 1 session    │
│        │                                │          │           │ (mobile     │              │              │
│        │                                │          │           │  layout)    │              │              │
│        │                                │          │ Flash     │             │              │              │
│        │ Service Worker caching, offline│          │           │             │              │              │
│        │ indicator banner. PWA manifest │          │           │             │              │              │
│        │ exists at quantverse-pwa/.     │          │           │             │              │              │
├────────┼────────────────────────────────┼──────────┼───────────┼─────────────┼──────────────┼──────────────┤
│        │                                │          │           │             │              │              │
│  W4-A  │ ML Parameter Optimization (9.1)│ 4-5 days │ BLOCKED   │ W2-A        │ W0-G,W0-H    │ 2 sessions   │
│        │                                │          │           │ (labeled    │              │              │
│        │                                │          │           │  data)      │              │              │
│        │ Pro: grid search architecture, │          │           │ Also blocked│              │              │
│        │ OptimisationResult table       │          │           │ by Stripe   │              │              │
│        │ schema, weekly schedule        │          │           │ (7.1) for   │              │              │
│        │                                │          │           │ Elite tier  │              │              │
│        │ Flash: RQ background job, grid │          │           │             │              │              │
│        │ search loop, param injection   │          │           │             │              │              │
│        │ into signal engine             │          │           │             │              │              │
│        │                                │          │           │             │              │              │
│        │ Session 1 (Pro): architecture  │          │           │             │              │              │
│        │ Session 2 (Flash): implement   │          │           │             │              │              │
└────────┴────────────────────────────────┴──────────┴───────────┴─────────────┴──────────────┴──────────────┘

================================================================================
EXECUTION ORDER (Optimal Parallel Schedule)
================================================================================

SESSION 1 — Launch All Wave 0 in Parallel (Max Throughput)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Agent A (Pro): W0-A — Performance metrics backend (formulas, endpoint design)
Agent B (Flash): W0-C — Backtesting UI (strategy picker + results dashboard)
Agent C (Pro): W0-D Session 1 — WebSocket architecture + Binance WS
Agent D (Flash): W0-E — Free tier caps beyond 5/day (all 5 caps)
Agent E (Qwen): W0-F Session 1 — Mobile layout CSS audit + design
Agent F (Pro): W0-G Session 1 — On-chain data architecture + API research
Agent G (Pro): W0-H — Public API design (OpenAPI spec, key model)
→ These 7 have ZERO shared dependencies — truly parallel.

SESSION 2 — Continue Wave 0 + Start P1/P2
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Agent H (Flash): W0-B — Performance dashboard frontend (depends on W0-A endpoint)
Agent I (Flash): W0-F Session 2 — Mobile layout implementation (Qwen pass done)
Agent J (Flash): W0-G Session 2 — On-chain implementation (Pro design done)
Agent K (Pro+Flash): W1-A — Binance trading backend (5-7d, start now)
Agent L (Pro+Flash): W1-B — Coinbase trading backend (5-7d, start now — parallel with W1-A!)
Agent M (Pro+Flash): W2-A — Labeled dataset pipeline (no deps, start now)

SESSION 3 — P1/P2 Continuation + Phase 2-3
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Agent N (Qwen+Flash): W1-C — Order UI (depends on W1-A+W1-B done)
Agent O (Pro+Flash): W2-B — Isotonic regression (depends on W2-A)
Agent P (Flash): W0-D Session 2 — TwelveData WS + frontend bridge
Agent Q (Flash): W3-A — Push alerts web+mobile (can start anytime)
Agent R (Pro+Flash): W3-B — Feature flags (depends on W0-E)

SESSION 4 — Deepen P1/P2 + Remaining Work
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Agent S (Flash): W1-D — One-click signal-to-order (depends on W1-C)
Agent T (Pro+Qwen): W2-C — Qwen review (depends on W2-B)
Agent U (Qwen+Flash): W2-D — Calibration card (depends on W2-B)
Agent V (Flash): W3-C — PWA offline (depends on W0-F)
Agent W (Pro+Flash): W4-A Session 1 — ML optimization architecture

SESSION 5 — Final Wave
━━━━━━━━━━━━━━━━━━━
Agent X (Flash): W4-A Session 2 — ML optimization implementation

================================================================================
CRITICAL PATH SUMMARY
================================================================================

Longest sequential chain: W2-A → W2-B → W2-C → W2-D (AI/ML)
This is 8-12 elapsed days even with max parallelism because each step
blocks the next.

Runner-up: W1-A/W1-B (parallel) → W1-C → W1-D (Exchange)
This is 7-10 elapsed days.

Everything else can be built in parallel with these chains.

Total project: ~5 sessions if running multiple agents, ~8-10 sessions single-agent.

================================================================================
BLOCKED ITEMS (Cannot Start Yet)
================================================================================

W1-C  ─ blocked by W1-A + W1-B (needs exchange endpoints)
W1-D  ─ blocked by W1-C          (needs order UI)
W2-B  ─ blocked by W2-A          (needs labeled data)
W2-C  ─ blocked by W2-B          (needs calibrated confidence)
W2-D  ─ blocked by W2-B          (needs calibration data for chart)
W3-B  ─ blocked by W0-E          (needs tier caps defined)
W3-C  ─ blocked by W0-F          (needs mobile layout)
W4-A  ─ blocked by W2-A          (needs labeled data)

================================================================================
READY-TO-START (No Dependencies)
================================================================================

W0-A  Performance backend       Pro+Flash   1 session
W0-C  Backtesting UI            Flash       1 session
W0-D  WebSocket feed            Pro         2 sessions
W0-E  Tier caps (beyond 5/day)  Flash       1 session
W0-F  Mobile layout             Qwen+Flash  2 sessions
W0-G  On-chain data             Pro+Flash   2 sessions
W0-H  Public API                Pro+Flash   1 session
W1-A  Binance trading           Pro+Flash   1 session
W1-B  Coinbase trading          Pro+Flash   1 session
W2-A  Labeled dataset           Pro+Flash   1 session
W3-A  Push alerts               Flash       1 session

================================================================================
MODEL ASSIGNMENT RATIONALE
================================================================================

Pro (DeepSeek V4 Pro): Always assigned to:
- Architecture design (schemas, state machines, auth flows)
- Math-heavy logic (isotonic, Sharpe, grid search)
- Protocol design (WebSocket bridge, REST API design)
- Planning/coordination subtasks

Flash (DeepSeek V4 Flash): Always assigned to:
- Boilerplate endpoint code
- File operations, DB migrations
- Frontend wiring, chart library glue
- Simple business logic (rate limits, counters)
- Pure implementation with clear specs

Qwen 3.5 Plus: Always assigned to:
- UI/UX layout design and critique
- CSS responsive breakpoints
- Component design review
- Prompt engineering review (for 2.3)
- Visual quality audit
