# Fib 23.6 Confirmed Entry Implementation Plan

## Goal

Add a Today strategy mode that turns a valid DotVerse setup into a Fib pullback/breakout plan:

- Entry: Fib 23.6 after the signal candle confirms beyond that level.
- Stop: Fib 12.
- TP1: Fib 38.2.
- TP2: Fib 61.8.
- Protection: when live price reaches Fib 50, move SL to Fib 38.2.

## Scope

1. Add Today mode selection and persistence.
2. Transform Today candidates before sizing/ranking when Fib mode is active.
3. Show Fib levels and readiness on each selected card.
4. Send strategy metadata with MT5 order payloads.
5. Persist Fib metadata into MT5 orders and watch records.
6. Extend the watch job so the EA receives a `modify_sl` order when Fib 50 is reached.
7. Verify with frontend static contracts, Python unit contracts, syntax checks, local smoke, push, and live static marker checks.

## Safety Rules

- Do not enter if live price has already reached/passed Fib 50 before the order is placed.
- Do not pretend a missing live price is an MT5 fill proof.
- Keep normal DotVerse mode unchanged.
- Keep broker-symbol failures separate from strategy bugs.

## Tests

- `tests/test_mt5_order_request.py`: request normalizer accepts Fib strategy metadata.
- `tests/test_automation_watch_wiring_contracts.py`: Fib metadata creates and persists a watch entry even if normal automation flags are off.
- `tests/test_today_fib_strategy_contracts.py`: Today UI contains the three strategy modes, applies the Fib transform before plan selection, displays Fib levels, and sends Fib metadata in the MT5 order payload.
