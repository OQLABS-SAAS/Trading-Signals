"""Static contract tests: no mock/fake data in P&L chart or Stress Test.

Tests mirror the pattern in test_a5_quickwins_contracts.py (read HTML as text,
assert markers present / absent).

Covers:
  ITEM A — drawPnlChart must use real /api/performance/pnl data
    (a) No Math.random or seeded-looking data generation in drawPnlChart
    (b) Empty-state text marker present (no-closed-trades honest state)

  ITEM B — Stress Test must use real open positions from /api/mt5/state
    (c) Hardcoded notionals array [26804,10816... is GONE from the file
    (d) Stress Test references /api/mt5/state AND has the no-positions empty-state text
"""
from pathlib import Path

HTML_PATH = Path("static/index-v2-prototype.html")
HTML = HTML_PATH.read_text(encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# ITEM A — drawPnlChart: real data only
# ─────────────────────────────────────────────────────────────────────────────

def _extract_draw_pnl_chart(html_text):
    """Extract the drawPnlChart function body."""
    start = html_text.index("function drawPnlChart(")
    depth = 0
    i = start
    while i < len(html_text):
        c = html_text[i]
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return html_text[start:i + 1]
        i += 1
    raise ValueError("Could not extract drawPnlChart body")


_DRAW_PNL_FN = _extract_draw_pnl_chart(HTML)


def test_pnl_chart_no_math_random():
    """drawPnlChart must NOT contain Math.random — no synthetic data generation."""
    assert "Math.random" not in _DRAW_PNL_FN, (
        "drawPnlChart still references Math.random. "
        "All random-walk / seeded-fake-data code must be removed."
    )


def test_pnl_chart_no_seeded_looking():
    """The 'seeded-looking' comment (and the fake-data generation pattern) must be gone."""
    assert "seeded-looking" not in _DRAW_PNL_FN, (
        "drawPnlChart still contains the 'seeded-looking' fake-data comment."
    )


def test_pnl_chart_fetches_real_endpoint():
    """drawPnlChart must fetch /api/performance/pnl for real cumulative P&L data."""
    assert "/api/performance/pnl" in _DRAW_PNL_FN, (
        "drawPnlChart must call dvFetch('/api/performance/pnl') to plot real closed-trade data."
    )


def test_pnl_chart_empty_state_marker():
    """The empty-state marker comment must exist inside drawPnlChart (honest no-data state)."""
    assert "EMPTY-STATE-PNL-MARKER" in _DRAW_PNL_FN, (
        "drawPnlChart must contain the EMPTY-STATE-PNL-MARKER comment "
        "to confirm the no-closed-trades honest state is implemented."
    )


def test_pnl_chart_no_closed_trades_text():
    """The exact empty-state message for zero closed trades must appear in drawPnlChart."""
    assert "No closed trades yet" in _DRAW_PNL_FN, (
        "drawPnlChart must render 'No closed trades yet — your real P&L will plot here as you close trades.' "
        "when there are no closed trades, instead of drawing synthetic data."
    )


# ─────────────────────────────────────────────────────────────────────────────
# ITEM B — Stress Test: real open positions from /api/mt5/state
# ─────────────────────────────────────────────────────────────────────────────

def test_stress_hardcoded_notionals_gone():
    """The hardcoded example notionals array [26804,10816... must be GONE from the file."""
    assert "[26804,10816" not in HTML, (
        "The hardcoded illustrative notionals array [26804,10816,...] still exists. "
        "Remove it entirely — the stress test must use real /api/mt5/state positions."
    )


def test_stress_uses_mt5_state():
    """rmRunStress must fetch /api/mt5/state to get the user's real open positions."""
    # Locate rmRunStress function body
    start = HTML.index("async function rmRunStress(")
    depth = 0
    i = start
    while i < len(HTML):
        c = HTML[i]
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                fn_body = HTML[start:i + 1]
                break
        i += 1
    else:
        raise ValueError("Could not extract rmRunStress body")

    assert "/api/mt5/state" in fn_body, (
        "rmRunStress must call dvFetch('/api/mt5/state') to load the user's real open positions."
    )


def test_stress_real_positions_module_variable():
    """window._rmStressPositions must be the module-level store for real positions."""
    assert "window._rmStressPositions" in HTML, (
        "window._rmStressPositions must exist as the real-positions store for the stress test."
    )


def test_stress_no_positions_empty_state():
    """Stress test must show an honest empty state when there are no open positions."""
    assert "No open positions to stress-test. Open a position (or connect MT5) and it will appear here." in HTML, (
        "Stress test must render the honest no-positions message when /api/mt5/state returns empty positions."
    )


def test_stress_illustrative_disclaimer_gone():
    """The 'Illustrative example portfolio' disclaimer must be gone (no longer needed)."""
    assert "Illustrative example portfolio" not in HTML, (
        "The 'Illustrative example portfolio — not your live positions' disclaimer still exists. "
        "Remove it — the stress test now uses real data."
    )
