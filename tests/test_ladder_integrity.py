"""A3 — Multi-ladder placement integrity tests.

Two layers:
  1. Static contract tests (plain Python) — grep the HTML for structural
     contracts: retry button marker, retry-only-failed-legs filter, retry cap
     constant, and _dvLadderOutcome function definition.
  2. Behavioral JS tests — extract _dvLadderOutcome via brace-balanced extractor,
     run via node subprocess, assert exact values for the four canonical cases:
       • 1 of 4 failing  → placed=3 failed=1 summaryText="3 of 4 orders placed"
       • all ok          → placed=4 failed=0 summaryText="All 4 orders placed"
       • all fail        → placed=0 failed=4 summaryText="All 4 orders failed"
       • empty           → placed=0 failed=0 total=0

All tests run from the repo root (pytest cwd); Path is relative to that.
"""
import json
import subprocess
from pathlib import Path

import pytest

HTML = Path("static/index-v2-prototype.html").read_text()

# ── Narrow to _szLadderSubmitGo so we don't pick up Today-tab strings ──
_SUBMIT_START = "async function _szLadderSubmitGo() {"
_SUBMIT_END   = "function szTypeChange(){"
_start = HTML.index(_SUBMIT_START)
_end   = HTML.index(_SUBMIT_END, _start)
BLOCK  = HTML[_start:_end]


# ─────────────────────────────────────────────────────────────────────────────
# 1. _dvLadderOutcome pure function exists in HTML
# ─────────────────────────────────────────────────────────────────────────────

def test_dvLadderOutcome_function_defined():
    """_dvLadderOutcome must be defined as a top-level function."""
    assert "function _dvLadderOutcome(" in HTML


def test_dvLadderOutcome_returns_placed():
    """_dvLadderOutcome must return a 'placed' field."""
    idx = HTML.index("function _dvLadderOutcome(")
    fn_end = HTML.index("}", idx)
    snippet = HTML[idx:fn_end + 200]
    assert "placed" in snippet


def test_dvLadderOutcome_returns_failed():
    """_dvLadderOutcome must return a 'failed' field."""
    idx = HTML.index("function _dvLadderOutcome(")
    fn_end = HTML.index("}", idx)
    snippet = HTML[idx:fn_end + 200]
    assert "failed" in snippet


def test_dvLadderOutcome_returns_total():
    """_dvLadderOutcome must return a 'total' field."""
    idx = HTML.index("function _dvLadderOutcome(")
    fn_end = HTML.index("}", idx)
    snippet = HTML[idx:fn_end + 200]
    assert "total" in snippet


def test_dvLadderOutcome_returns_failedLegs():
    """_dvLadderOutcome must return a 'failedLegs' array."""
    assert "failedLegs" in HTML


def test_dvLadderOutcome_returns_summaryText():
    """_dvLadderOutcome must return a 'summaryText' string."""
    assert "summaryText" in HTML


def test_dvLadderOutcome_handles_empty_input():
    """_dvLadderOutcome must handle null/empty input gracefully."""
    idx = HTML.index("function _dvLadderOutcome(")
    snippet = HTML[idx:idx + 400]
    assert "!results||!results.length" in snippet or "results.length" in snippet


# ─────────────────────────────────────────────────────────────────────────────
# 2. Static contract: retry button marker exists in submit block
# ─────────────────────────────────────────────────────────────────────────────

def test_retry_button_marker_exists():
    """'szLadderRetryBtn' must appear in the submit block for the retry button."""
    assert 'id="szLadderRetryBtn"' in BLOCK


def test_retry_button_label_contains_fail_count():
    """Retry button label must embed the fail count."""
    assert "Retry ' + fail + ' failed leg" in BLOCK


# ─────────────────────────────────────────────────────────────────────────────
# 3. Static contract: retry path filters to failed legs only (!ok)
# ─────────────────────────────────────────────────────────────────────────────

def test_retry_path_iterates_failed_legs_only():
    """Retry loop must iterate _szFailedLegs (not re-expand _szBuildExecutionLegs)."""
    assert "for (var ri = 0; ri < _szFailedLegs.length; ri++)" in BLOCK


def test_retry_path_uses_leg_snapshot():
    """Retry must use fl._legSnapshot to reconstruct the request."""
    assert "fl._legSnapshot" in BLOCK


def test_retry_path_filters_ok_false():
    """newFail must be populated by filtering retry results for !r.ok."""
    assert "retryResults.filter(function(r){ return !r.ok; })" in BLOCK


def test_retry_path_does_not_rebuild_execution_legs():
    """Retry onclick closure must NOT call _szBuildExecutionLegs()."""
    wire_start = BLOCK.index("if (fail > 0) {")
    wire_body  = BLOCK[wire_start:wire_start + 1200]
    assert "_szBuildExecutionLegs()" not in wire_body


def test_ok_legs_accumulated_on_retry():
    """Newly-placed legs from retry must be merged into _szOkLegs."""
    assert "_szOkLegs = _szOkLegs.concat(newOk);" in BLOCK


def test_failed_legs_updated_after_retry():
    """After retry, _szFailedLegs must be updated to only still-failing legs."""
    assert "_szFailedLegs = newFail;" in BLOCK


# ─────────────────────────────────────────────────────────────────────────────
# 4. Static contract: retry cap constant and exhaustion message
# ─────────────────────────────────────────────────────────────────────────────

def test_retry_cap_constant_present():
    """_LADDER_RETRY_CAP constant must be defined in the HTML."""
    assert "_LADDER_RETRY_CAP" in HTML


def test_retry_cap_constant_value():
    """_LADDER_RETRY_CAP must be set to 2."""
    assert "var _LADDER_RETRY_CAP = 2;" in HTML


def test_retry_cap_exhaustion_message():
    """When cap is exhausted, the message 'Still failing' must be shown."""
    assert "Still failing" in BLOCK


def test_retry_cap_exhaustion_directs_back_to_size():
    """Exhaustion message must mention trying again from Size."""
    assert "try again from Size" in BLOCK


def test_retry_count_variable_declared():
    """_szRetryCount must be declared inside the submit function."""
    assert "var _szRetryCount = 0;" in BLOCK


def test_retry_count_incremented_on_retry():
    """_szRetryCount must be incremented inside the retry onclick handler."""
    assert "_szRetryCount++;" in BLOCK


def test_retry_cap_checked_before_showing_button():
    """Cap check must guard whether the retry button or exhaustion msg is shown."""
    assert "capExhausted" in BLOCK or "_szRetryCount >= _LADDER_RETRY_CAP" in BLOCK


# ─────────────────────────────────────────────────────────────────────────────
# 5. _dvLadderOutcome called from _szRenderLegStatus
# ─────────────────────────────────────────────────────────────────────────────

def test_render_leg_status_calls_dvLadderOutcome():
    """_szRenderLegStatus must call _dvLadderOutcome to compute outcome."""
    render_start = BLOCK.index("function _szRenderLegStatus()")
    render_end   = BLOCK.index("}", render_start + len("function _szRenderLegStatus()") + 10)
    # Find closing brace of function by scanning ahead
    depth = 0
    pos = render_start
    while pos < len(BLOCK):
        if BLOCK[pos] == "{":
            depth += 1
        elif BLOCK[pos] == "}":
            depth -= 1
            if depth == 0:
                render_end = pos
                break
        pos += 1
    render_body = BLOCK[render_start:render_end + 1]
    assert "_dvLadderOutcome(" in render_body


# ─────────────────────────────────────────────────────────────────────────────
# 6. Behavioral JS tests — _dvLadderOutcome via node subprocess
# ─────────────────────────────────────────────────────────────────────────────

def _node_available() -> bool:
    try:
        subprocess.run(["node", "--version"], capture_output=True, timeout=5)
        return True
    except Exception:
        return False


def _extract_fn(src: str, fn_name: str) -> str:
    """Brace-balanced extractor: returns the full function body for fn_name."""
    marker = "function " + fn_name + "("
    start = src.find(marker)
    if start < 0:
        raise RuntimeError(f"function {fn_name} not found in source")
    depth = 0
    started = False
    j = start
    while j < len(src):
        ch = src[j]
        if ch == "{":
            depth += 1
            started = True
        elif ch == "}":
            depth -= 1
            if started and depth == 0:
                return src[start:j + 1]
        j += 1
    raise RuntimeError(f"Unbalanced braces for function {fn_name}")


def _run_ladder_outcome_js(script: str) -> object:
    """Inject _dvLadderOutcome from HTML and run script; return parsed JSON."""
    src = Path("static/index-v2-prototype.html").read_text()
    fn_js = _extract_fn(src, "_dvLadderOutcome")
    full = fn_js + "\n" + script
    r = subprocess.run(
        ["node", "-e", full],
        capture_output=True, text=True, timeout=15,
        cwd=Path(__file__).parent.parent,
    )
    if r.returncode != 0:
        raise RuntimeError(f"node error:\n{r.stderr[:800]}")
    return json.loads(r.stdout.strip())


@pytest.mark.skipif(not _node_available(), reason="node not available")
class TestDvLadderOutcomeBehavioral:
    """Behavioral tests: run _dvLadderOutcome via node, assert exact values."""

    def test_one_of_four_failing(self):
        """1 of 4 legs failing → placed=3 failed=1 summaryText='3 of 4 orders placed'."""
        script = r"""
var results = [
  {ok: true,  symbol: 'XAUUSD', legIndex: 1, target: 'tp1'},
  {ok: true,  symbol: 'XAUUSD', legIndex: 2, target: 'tp2'},
  {ok: false, symbol: 'XAUUSD', legIndex: 3, target: 'tp3'},
  {ok: true,  symbol: 'XAUUSD', legIndex: 4, target: 'tp1'}
];
var r = _dvLadderOutcome(results);
process.stdout.write(JSON.stringify(r));
"""
        r = _run_ladder_outcome_js(script)
        assert r["placed"]      == 3,                      f"placed expected 3, got {r['placed']}"
        assert r["failed"]      == 1,                      f"failed expected 1, got {r['failed']}"
        assert r["total"]       == 4,                      f"total expected 4, got {r['total']}"
        assert r["summaryText"] == "3 of 4 orders placed", f"summaryText got {r['summaryText']}"
        assert len(r["failedLegs"]) == 1,                  f"failedLegs expected 1, got {len(r['failedLegs'])}"
        assert r["failedLegs"][0]["legIndex"] == 3,        f"wrong failed leg index"

    def test_all_ok(self):
        """All 4 legs ok → placed=4 failed=0 summaryText='All 4 orders placed'."""
        script = r"""
var results = [
  {ok: true, symbol: 'XAUUSD', legIndex: 1, target: 'tp1'},
  {ok: true, symbol: 'XAUUSD', legIndex: 2, target: 'tp2'},
  {ok: true, symbol: 'XAUUSD', legIndex: 3, target: 'tp3'},
  {ok: true, symbol: 'XAUUSD', legIndex: 4, target: 'tp1'}
];
var r = _dvLadderOutcome(results);
process.stdout.write(JSON.stringify(r));
"""
        r = _run_ladder_outcome_js(script)
        assert r["placed"]      == 4,                    f"placed expected 4, got {r['placed']}"
        assert r["failed"]      == 0,                    f"failed expected 0, got {r['failed']}"
        assert r["total"]       == 4,                    f"total expected 4, got {r['total']}"
        assert r["summaryText"] == "All 4 orders placed",f"summaryText got {r['summaryText']}"
        assert r["failedLegs"]  == [],                   f"failedLegs expected empty, got {r['failedLegs']}"

    def test_all_fail(self):
        """All 4 legs fail → placed=0 failed=4 summaryText='All 4 orders failed'."""
        script = r"""
var results = [
  {ok: false, symbol: 'XAUUSD', legIndex: 1, target: 'tp1', error: 'No connection'},
  {ok: false, symbol: 'XAUUSD', legIndex: 2, target: 'tp2', error: 'No connection'},
  {ok: false, symbol: 'XAUUSD', legIndex: 3, target: 'tp3', error: 'No connection'},
  {ok: false, symbol: 'XAUUSD', legIndex: 4, target: 'tp1', error: 'No connection'}
];
var r = _dvLadderOutcome(results);
process.stdout.write(JSON.stringify(r));
"""
        r = _run_ladder_outcome_js(script)
        assert r["placed"]      == 0,                    f"placed expected 0, got {r['placed']}"
        assert r["failed"]      == 4,                    f"failed expected 4, got {r['failed']}"
        assert r["total"]       == 4,                    f"total expected 4, got {r['total']}"
        assert r["summaryText"] == "All 4 orders failed",f"summaryText got {r['summaryText']}"
        assert len(r["failedLegs"]) == 4,                f"failedLegs expected 4, got {len(r['failedLegs'])}"

    def test_empty_results(self):
        """Empty array → placed=0 failed=0 total=0 failedLegs=[]."""
        script = r"""
var r = _dvLadderOutcome([]);
process.stdout.write(JSON.stringify(r));
"""
        r = _run_ladder_outcome_js(script)
        assert r["placed"]     == 0,  f"placed expected 0, got {r['placed']}"
        assert r["failed"]     == 0,  f"failed expected 0, got {r['failed']}"
        assert r["total"]      == 0,  f"total expected 0, got {r['total']}"
        assert r["failedLegs"] == [], f"failedLegs expected [], got {r['failedLegs']}"

    def test_null_results(self):
        """Null input → all zeros, no exception."""
        script = r"""
var r = _dvLadderOutcome(null);
process.stdout.write(JSON.stringify(r));
"""
        r = _run_ladder_outcome_js(script)
        assert r["placed"]     == 0
        assert r["failed"]     == 0
        assert r["total"]      == 0
        assert r["failedLegs"] == []

    def test_failedLegs_contains_full_objects(self):
        """failedLegs must contain the full result objects (for retry use)."""
        script = r"""
var results = [
  {ok: true,  symbol: 'GBPUSD', legIndex: 1, target: 'tp1', order_id: '12345'},
  {ok: false, symbol: 'GBPUSD', legIndex: 2, target: 'tp2', error: 'Market closed'}
];
var r = _dvLadderOutcome(results);
process.stdout.write(JSON.stringify(r));
"""
        r = _run_ladder_outcome_js(script)
        assert r["placed"]                         == 1
        assert r["failed"]                         == 1
        fl = r["failedLegs"][0]
        assert fl["symbol"]   == "GBPUSD",         f"symbol got {fl['symbol']}"
        assert fl["legIndex"] == 2,                f"legIndex got {fl['legIndex']}"
        assert fl["error"]    == "Market closed",  f"error got {fl['error']}"

    def test_single_leg_ok(self):
        """Single placed leg → placed=1 summaryText='All 1 order placed'."""
        script = r"""
var results = [{ok: true, symbol: 'BTCUSD', legIndex: 1, target: 'tp1', order_id: '99'}];
var r = _dvLadderOutcome(results);
process.stdout.write(JSON.stringify(r));
"""
        r = _run_ladder_outcome_js(script)
        assert r["placed"]      == 1
        assert r["failed"]      == 0
        assert r["total"]       == 1
        assert r["summaryText"] == "All 1 order placed", f"summaryText got {r['summaryText']}"

    def test_single_leg_fail(self):
        """Single failed leg → placed=0 summaryText='All 1 order failed'."""
        script = r"""
var results = [{ok: false, symbol: 'BTCUSD', legIndex: 1, target: 'tp1', error: 'timeout'}];
var r = _dvLadderOutcome(results);
process.stdout.write(JSON.stringify(r));
"""
        r = _run_ladder_outcome_js(script)
        assert r["placed"]      == 0
        assert r["failed"]      == 1
        assert r["total"]       == 1
        assert r["summaryText"] == "All 1 order failed", f"summaryText got {r['summaryText']}"
