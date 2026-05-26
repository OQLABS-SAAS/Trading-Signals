import re

with open('static/index-v2-prototype.html','r') as f:
    content = f.read()

# All _dvGuide entries
all_keys = set(re.findall(r"'([a-z][a-z0-9_-]+)':\s*\{", content))

# All data-guide attributes in HTML
data_guides = set(re.findall(r'data-guide="([^"]+)"', content))
static_guides = {g for g in data_guides if '${' not in g and '+' not in g}

# Dynamic patterns
dynamic = {g for g in data_guides if '${' in g or '+' in g}

# ORPHAN - data-guide with no entry
orphan = static_guides - all_keys

# UNUSED - entries never connected
unused = all_keys - static_guides

# Categorize unused entries by tab
categories = {
    'Signal Cards/Understand': ['confidence-confirmed', 'confidence-likely', 'confidence-hypothesis', 'quality-score', 'what-to-do-next', 'signal-buy', 'signal-sell', 'signal-hold'],
    'Indicators (Understand)': ['ind-trend-direction', 'ind-momentum-gauge', 'ind-price-momentum', 'ind-market-activity', 'ind-price-range', 'ind-price-swing', 'ind-htf-trend', 'ind-signal-agreement'],
    'Advanced Indicators': ['ind-adv-atr-volatility', 'ind-adv-bollinger', 'ind-adv-confluence', 'ind-adv-ema', 'ind-adv-htf-trend', 'ind-adv-macd', 'ind-adv-rsi'],
    'SMC': ['smc-title', 'smc-fvg-bullish', 'smc-fvg-bearish', 'smc-liquidity-grab-bull', 'smc-liquidity-grab-bear', 'smc-displacement-bull', 'smc-displacement-bear', 'smc-choch-bull', 'smc-choch-bear'],
    'Trade Type': ['trade-type-scalp', 'trade-type-day', 'trade-type-swing', 'trade-type-position'],
    'Macro': ['macro-full', 'macro-reduced', 'macro-notrade', 'trending', 'mixed', 'risk-off', 'volatility'],
    'Auto Settings': ['auto-ai-reanalyze', 'auto-alert-signal', 'auto-alert-sl', 'auto-alert-summary', 'auto-alert-tp', 'auto-be', 'auto-daily-loss', 'auto-drawdown-pause', 'auto-inval', 'auto-macro', 'auto-news-filter', 'auto-recommended', 'auto-scan-entry', 'auto-sent', 'auto-tp1-scale', 'auto-tp2-scale', 'auto-tp3-scale', 'auto-trail', 'auto-weekend-close'],
    'Other': ['rsi', 'rr', 'spread', 'volume', 'timeframe', 'change', 'winrate'],
}

print("=" * 70)
print("FULL TOOLTIP GUIDE AUDIT — DotVerse")
print("=" * 70)
print(f"\nTotal data-guide in HTML (static):   {len(static_guides)}")
print(f"Total data-guide in HTML (dynamic): {len(dynamic)}")
print(f"Total _dvGuide entries:             {len(all_keys)}")
print(f"Orphan data-guide (no entry):       {len(orphan)}")
print(f"Unused _dvGuide entries:            {len(unused)}")

print("\n" + "=" * 70)
print("UNUSED _dvGuide ENTRIES BY TAB")
print("=" * 70)
for cat, keys in categories.items():
    found = [k for k in keys if k in unused]
    if found:
        print(f"\n{cat} ({len(found)}):")
        for k in found:
            print(f"  {k}")

# Remaining uncategorized
uncategorized = unused - {k for keys in categories.values() for k in keys}
if uncategorized:
    print(f"\nUncategorized ({len(uncategorized)}):")
    for k in sorted(uncategorized):
        print(f"  {k}")

print("\n" + "=" * 70)
print("ORPHAN data-guide (need _dvGuide entry)")
print("=" * 70)
for g in sorted(orphan):
    print(f"  {g}")

print("\n" + "=" * 70)
print("DYNAMIC data-guide PATTERNS")
print("=" * 70)
for d in sorted(dynamic):
    print(f"  {d}")

# Find which elements have data-guide classified by tab area
print("\n" + "=" * 70)
print("ELEMENTS WITH data-guide BY TAB AREA")
print("=" * 70)

tab_patterns = {
    'Signal/Pipeline': ['opp-', 'conf-', 'qual-', 'wr-pat', 'signal-', 'spread', 'rr-', 'tp', 'stop-loss', 'entry-price', 'win-rate', 'bear-pct', 'bull-pct', 'rsi-', 'candle', 'flow-scale', 'confluence', 'trade-duration', 'trade-session', 'regime', 'mtf-', 'ind-adv-volume', 'verdict-', 'what-to-do'],
    'Size Tab': ['size-', 'calc-', 'kelly', 'ladder', 'risk-', 'asset-type', 'atr-value', 'contract-size', 'trade-size', 'agent-sizing'],
    'Auto Settings': ['auto-'],
    'Portfolio': ['portfolio-'],
    'Market': ['market-', 'macro-', 'fear-greed', 'session-', 'scanner-', 'watchlist-'],
    'Journey': ['journey-'],
}

tabbed = {t: [] for t in tab_patterns}
unknown = []
for g in sorted(static_guides | set(orphan)):
    found_tab = False
    for tab, patterns in tab_patterns.items():
        for p in patterns:
            if g.startswith(p):
                tabbed[tab].append(g)
                found_tab = True
                break
        if found_tab:
            break
    if not found_tab:
        unknown.append(g)

for tab, items in sorted(tabbed.items()):
    if items:
        print(f"\n{tab} ({len(items)}):")
        for g in items:
            status = '❌ NO ENTRY' if g in orphan else '✅'
            print(f"  {status}  {g}")

if unknown:
    print(f"\nOther ({len(unknown)}):")
    for g in unknown:
        print(f"  {g}")
