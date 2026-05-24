#!/bin/bash
cd "$(dirname "$0")"
rm -f .git/HEAD.lock .git/index.lock .git/MERGE_HEAD.lock .git/CHERRY_PICK_HEAD.lock .git/REBASE_HEAD.lock 2>/dev/null
git add app.py static/index-v2-prototype.html
git commit -m "D1: live price strip on signal cards + normalise_ticker in /api/live-price

- app.py: normalise_ticker() in /api/live-price (BTCUSD->BTC-USD etc)
- lp-SYM-i strip on every BUY/SELL card, colour-coded vs entry
- _sfStopLivePrices/_sfStartLivePrices, 30s poll, all 8 nav paths covered
- cache stores displayOpps for index-aligned restore on nav-back
- setNav stops poll on any tab-away; showSignalFeed stops on re-entry"
git push origin main
echo ""
echo "Done. You can close this window."
