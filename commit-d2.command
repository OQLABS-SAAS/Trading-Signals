#!/bin/bash
cd "$(dirname "$0")"
rm -f .git/HEAD.lock .git/index.lock .git/MERGE_HEAD.lock .git/CHERRY_PICK_HEAD.lock .git/REBASE_HEAD.lock 2>/dev/null
git add static/index-v2-prototype.html CLAUDE.md
git commit -m "D2: risk-of-ruin panel in Size tab + three role lenses in CLAUDE.md

- szRoRPanel div added to showSize() template (after distance breakdown bars)
- szRoRUpdate() function: reads szAcct + szRisk, computes consecutive losses to
  50% drawdown and 99% wipe, colour-coded green/amber/red by risk level
- Called at end of szCalc() so panel updates live as user types
- Guard: panel hidden when acct=0 or risk<=0; risk>=100 capped at 1 loss
- CLAUDE.md: Systems Architect + Senior Principal Engineer + QA lenses added
  as mandatory pre-implementation gates"
git push origin main
echo ""
echo "Done. You can close this window."
