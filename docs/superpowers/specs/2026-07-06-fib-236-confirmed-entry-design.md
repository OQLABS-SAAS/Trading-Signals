# Fib 23.6 Confirmed Entry Design

## Goal

Add a Today strategy mode that finds Fibonacci retracement/breakout setups, waits for candle-close confirmation at the 23.6 level, and then allows immediate entry with fixed Fib exits and protection. The design should reduce missed trades without chasing late moves, while reusing DotVerse's existing Today, Size, Act, MT5 order, and automation machinery.

## Strategy Mode

Today should expose a `Today Strategy Mode` selector with:

- `Standard DotVerse`: the current Today brain, risk, backtest, and execution-gate flow.
- `Fixed Micro-Lot Signal`: the simple account-equity sizing rule already added to signals and Telegram alerts.
- `Fib 23.6 Confirmed Entry`: the new Fib strategy preset described here.

`Fib 23.6 Confirmed Entry` replaces the earlier "scout" wording. The system does not place an early scout order. It waits for confirmation first, then enters only if the entry is still clean.

## Fib Setup Rules

The preset supports both directions as one mirrored strategy.

### SELL Setup

- Detect an upward impulse wave from swing low to swing high.
- Calculate Fib levels: `12`, `23.6`, `38.2`, `50`, `61.8`.
- Wait for the signal-timeframe candle to close below `23.6`.
- After confirmation, enter SELL only if price is near the `23.6` level or retests it cleanly.
- Stop loss: Fib `12`.
- TP1: Fib `38.2`.
- TP2: Fib `61.8`.
- Protection rule: when price reaches Fib `50`, move stop loss to Fib `38.2`.

### BUY Setup

- Detect a downward impulse wave from swing high to swing low.
- Calculate Fib levels: `12`, `23.6`, `38.2`, `50`, `61.8`.
- Wait for the signal-timeframe candle to close above `23.6`.
- After confirmation, enter BUY only if price is near the `23.6` level or retests it cleanly.
- Stop loss: Fib `12`.
- TP1: Fib `38.2`.
- TP2: Fib `61.8`.
- Protection rule: when price reaches Fib `50`, move stop loss to Fib `38.2`.

## Confirmation And Entry Timing

Use a two-stage model:

1. Confirmation uses the signal timeframe.
   - A `1H` setup waits for a `1H` candle close beyond `23.6`.
   - A `4H` setup waits for a `4H` candle close beyond `23.6`.
   - This avoids false breaks from lower-timeframe noise.

2. Entry timing uses a faster execution timeframe.
   - After confirmation, Today watches a faster timeframe such as `15m` for `1H/4H` setups.
   - If price is still close to `23.6`, entry is allowed immediately.
   - If price has moved too far from `23.6`, Today waits for a retest.
   - If no retest appears before the setup expires, Today skips the trade.

The preset must not chase. The UI should show states such as:

- `Watching 23.6 close`
- `Confirmed, waiting for clean entry`
- `Entry now: near 23.6`
- `Missed move: waiting for retest`
- `Skipped: price ran too far`

## Fit With Existing Automations

This should reuse existing automation primitives instead of creating a separate engine:

- Existing order placement handles entry, stop loss, TP1, and TP2.
- Existing ladder/leg mechanics handle two profit targets.
- Existing MT5 order lifecycle handles pending/open/modify actions.
- Existing stop modification machinery can be extended for Fib-level stop movement.

The new behavior is a strategy preset plus one new automation rule type:

`move_stop_at_price_level`

For this preset:

- Trigger level: Fib `50`.
- New stop level: Fib `38.2`.
- Applies after the position is open.
- Must dedupe like existing modify-stop/trailing jobs.
- Must respect account ownership and broker account scope.
- Must never conflict with ATR trailing; if this preset is active, Fib stop movement is the active protection rule.

## Today Data Flow

1. Today strategy mode is selected.
2. Candidate scanner finds symbols/timeframes.
3. Fib engine derives impulse wave and Fib levels from OHLC data.
4. Candidate is classified:
   - no clean wave
   - watching confirmation
   - confirmed but waiting for clean entry
   - executable now
   - skipped
5. Today card renders the exact Fib levels and status.
6. If executable, Today builds a normal trade plan:
   - entry near `23.6`
   - stop at `12`
   - TP1 at `38.2`
   - TP2 at `61.8`
   - protection rule from `50` to `38.2`
7. Existing Size/Act/MT5 execution paths place the order and attach automation metadata.

## UI Requirements

The Today card should use trader-readable language:

- `Fib confirmed: BUY allowed now`
- `Fib confirmed: SELL allowed now`
- `Stop loss at Fib 12`
- `TP1 38.2 / TP2 61.8`
- `At Fib 50, DotVerse moves SL to 38.2`
- `No chase: waiting for retest`

The mode selector should be compact and operational, not a landing-page explanation. It belongs in Today controls near the existing risk/goal configuration.

## Safety Rules

- No order before candle-close confirmation.
- No order if the latest price is too far from `23.6`.
- No order if Fib wave quality is weak or swing points are ambiguous.
- No order if broker symbol availability or volume constraints fail.
- No full-size entry unless Today execution gate is true.
- For the current fixed micro-lot direction, the preset should support the same lot rule where applicable.

## Testing Plan

Add focused tests before implementation:

- Fib level math for BUY and SELL waves.
- Confirmation requires signal-timeframe candle close beyond `23.6`.
- BUY maps stop/TP/protection levels correctly.
- SELL maps stop/TP/protection levels correctly.
- Price far from `23.6` returns wait/retest or skip, not executable.
- Today card renders the strategy mode and Fib statuses.
- Order payload carries TP1, TP2, stop, and `move_stop_at_price_level` automation metadata.
- Automation dedupes stop-move requests and respects account ownership.

## Implementation Boundary

This spec is the design only. Implementation should be a separate plan and patch after review. The first implementation slice should be read-only/advisory Today cards with executable gating visible, followed by order/automation wiring only after the advisory contract is verified.
