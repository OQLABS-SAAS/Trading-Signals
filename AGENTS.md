# DotVerse — Agent Protocol

This project uses a strict **multi-agent workflow**. Every non-trivial change goes through specialist agents — never solo.

Source of truth: `~/.hermes/skills/software-development/dotverse-build-protocol/SKILL.md`

## Agent Roster

| # | Agent | Role | When |
|---|-------|------|------|
| 1 | **Architect** | Data flow, blast radius, endpoint design, placement | Before any backend or structural change |
| 2 | **QA** | Edge cases, null/undefined, failure modes, response shapes | Before any endpoint or frontend change |
| 3 | **UX** | Beginner comprehension, colors, mobile, labels, jargon check | Before any frontend change |
| 4 | **Coding** | Write the actual code — receives specs from Architect + UX | The implementation step |
| 5 | **Debug** | Root cause tracing, failure chain analysis | When a bug is reported |
| 6 | **Verification** | Read ALL modified files, report discrepancies vs claims | FINAL GATE before every push |

## IRON RULE

**NEVER solo on DotVerse.** Every action — research, debugging, coding, verification — goes through `delegate_task`. The moment this project is touched, solo mode is dead for the rest of the session.

## Deploy

- `git push origin main` → Railway auto-deploys to `dot-verse.up.railway.app`
- Verification agent must approve before any push

## Key Patterns (inherited from protocol skill)

- `dvFetch` silently returns null on any error — **never fix it**, 40+ callers depend on the contract. Return HTTP 200 with `ready: false` for data-unavailable cases instead.
- `SessionLocal` doesn't exist in this codebase — `_DBSession` is the correct variable (line 11590).
- Scripts in `innerHTML` don't execute — move them outside the template literal.
- Tooltips break after `innerHTML` re-render — always check `el.isConnected` before computing position.
- **Always read the actual error first** — hit the endpoint, read the response body, check the logs. Never write a fix for what you *think* is broken.

## Stack

- **Backend:** Flask (single-file `app.py`, ~14K lines)
- **Frontend:** Single-file HTML (`static/index-v2-prototype.html`, ~20K lines)
- **Auth:** Google OAuth only
- **Database:** PostgreSQL via SQLAlchemy + `_DBSession`
- **Deploy:** Railway
- **Signals:** SMC, RSI divergence, regime detection, MTF trend, VIX, footprint
