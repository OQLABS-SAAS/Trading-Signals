# DotVerse Lessons

## Operator test-account EA connection — 2026-07-11

**Context:** A dedicated DotVerse operator/test account was created for Hermes-led Today trading QA so testing does not depend on the user's personal Google OAuth session.

**Observed behavior:**
- Public registration/login can create and authenticate a test account.
- A new account defaults to `free` tier, so MT5 order placement remains blocked by the Pro/Elite gate.
- Scan alerts are readable after login.
- MT5 state remains disconnected until a real MT5 EA pushes fresh telemetry for that user/account.
- A saved DEMO account shell is not the same as an EA-connected terminal.

**Reusable product lesson:**
DotVerse needs an explicit operator/test-account provisioning path: authenticated app account + Pro/Elite test tier + saved DEMO MT5 account + per-account EA secret + fresh EA telemetry. The UI must distinguish:
- saved DEMO account
- EA disconnected/stale
- EA online and DEMO-verified
- order route permitted

**Safety rule:**
Never mark an operator test account as connected by fabricating MT5 state. Demo trade tests require real deployed app session state and fresh EA telemetry.

**Implementation note:**
When an account is saved but EA telemetry is absent, status cards should still show the saved DEMO/LIVE mode while clearly saying EA is disconnected. Execution endpoints must continue requiring fresh EA state before accepting orders.
