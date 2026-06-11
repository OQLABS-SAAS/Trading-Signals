"""Static contract tests for A5 quick-wins and #21 allocation guidance.

Pattern: read the HTML as text, assert markers are present / absent.
Mirrors existing contract-test conventions (test_today_frontend_contracts.py, etc.).

A5 checks:
  1. Header date — _dvFmtHeaderDate function present; no literal '· —' placeholder.
  2. Reset All Data — confirm() wording present; lives in the danger zone (settDangerZone);
     NOT present next to the Journal button in the Portfolio header.
  3. MT5 UNKNOWN — no bare 'MT5 UNKNOWN' string in any render path; human syncing
     phrase present instead.

#21 checks:
  4. _dvAllocationHint pure function defined with the ≥2× threshold logic.
  5. Function wired into the allocation row renderer.
  6. Node-harness behavioural tests for _dvAllocationHint (run via subprocess).
"""
import json
import re
import subprocess
from pathlib import Path

HTML_PATH = Path("static/index-v2-prototype.html")
HTML = HTML_PATH.read_text()


# ─────────────────────────────────────────────────────────────────────────────
# A5 — Fix 1: Header date
# ─────────────────────────────────────────────────────────────────────────────

def test_a5_header_date_function_present():
    """_dvFmtHeaderDate must exist to compute the live date string."""
    assert "function _dvFmtHeaderDate(" in HTML


def test_a5_header_no_emdash_placeholder():
    """The tab-restore path must not hard-code an &mdash; placeholder."""
    # The old tab-restore code injected a literal &mdash; span — must be gone
    assert "'&mdash;'" not in HTML
    assert '"&mdash;"' not in HTML
    # Old static form: innerHTML = '... <span id="dashDate">&mdash;</span>'
    assert "<span id=\"dashDate\">&mdash;</span>" not in HTML
    assert "<span id='dashDate'>&mdash;</span>" not in HTML


def test_a5_header_date_formats_uppercase_short():
    """Format output must contain uppercase day/month tokens."""
    assert "'SUN','MON','TUE','WED','THU','FRI','SAT'" in HTML
    assert "'JAN','FEB','MAR','APR','MAY','JUN'" in HTML


def test_a5_header_date_called_on_tab_restore():
    """Tab-restore path must call _dvFmtHeaderDate, not re-insert &mdash;."""
    assert "_dvFmtHeaderDate(new Date())" in HTML


# ─────────────────────────────────────────────────────────────────────────────
# A5 — Fix 2: Reset All Data demoted to Danger Zone
# ─────────────────────────────────────────────────────────────────────────────

def test_a5_reset_button_not_in_portfolio_header():
    """pfResetBtn must NOT appear inside the Portfolio page-header (pg-hd) div."""
    # The pg-hd block now ends before any reset button reference
    pg_hd_idx = HTML.index('<div class="pg-hd"><div class="pg-hd-left"><div class="pg-hd-title">Portfolio</div>')
    # Find the end of the header block (next pg-hd or the VaR div that follows)
    pg_hd_end = HTML.index('data-guide="portfolio-var"', pg_hd_idx)
    header_block = HTML[pg_hd_idx:pg_hd_end]
    assert "pfResetBtn" not in header_block, \
        "pfResetBtn should have been removed from the Portfolio page header"


def test_a5_reset_button_in_danger_zone():
    """pfResetBtn must live inside settDangerZone."""
    dz_idx = HTML.index('id="settDangerZone"')
    # The danger zone section ends at the closing </div> pair — find pfResetBtn nearby
    dz_block = HTML[dz_idx: dz_idx + 2000]
    assert "pfResetBtn" in dz_block, \
        "pfResetBtn must appear inside the settDangerZone section"


def test_a5_reset_danger_zone_title():
    """Danger Zone section must have the correct heading."""
    assert "Danger Zone" in HTML
    assert "settDangerZone" in HTML


def test_a5_reset_confirm_dialog_names_data_types():
    """First confirm() must explicitly name journal, trades, positions, settings."""
    # Extract the pfMasterReset function block
    start = HTML.index("async function pfMasterReset()")
    end   = HTML.index("\nasync function ", start + 1)
    block = HTML[start:end]
    assert "confirm(" in block
    assert "journal" in block.lower()
    assert "trade" in block.lower()
    assert "position" in block.lower()
    assert "cannot be undone" in block.lower()


def test_a5_reset_double_confirm():
    """pfMasterReset must have two confirm() calls (belt-and-braces)."""
    start = HTML.index("async function pfMasterReset()")
    end   = HTML.index("\nasync function ", start + 1)
    block = HTML[start:end]
    assert block.count("confirm(") >= 2


# ─────────────────────────────────────────────────────────────────────────────
# A5 — Fix 3: MT5 UNKNOWN phrasing removed
# ─────────────────────────────────────────────────────────────────────────────

def test_a5_no_mt5_unknown_literal():
    """The string 'MT5 UNKNOWN' must not appear anywhere in the rendered HTML."""
    assert "MT5 UNKNOWN" not in HTML


def test_a5_no_mt5_mode_unknown_badge():
    """'MT5 MODE UNKNOWN' badge text must be gone."""
    assert "MT5 MODE UNKNOWN" not in HTML


def test_a5_mt5_syncing_phrase_present():
    """When account details are unknown, human-readable syncing phrase must appear."""
    assert "account details syncing" in HTML


def test_a5_mt5_syncing_badge_present():
    """Badge fallback must use SYNCING wording, not UNKNOWN."""
    assert "MT5 CONNECTED — SYNCING" in HTML


# ─────────────────────────────────────────────────────────────────────────────
# #21 — Allocation divergence guidance
# ─────────────────────────────────────────────────────────────────────────────

def test_alloc_hint_function_defined():
    """_dvAllocationHint pure function must be defined."""
    assert "function _dvAllocationHint(" in HTML


def test_alloc_hint_2x_threshold_present():
    """The ≥2× over-threshold check must appear in the function body."""
    start = HTML.index("function _dvAllocationHint(")
    end   = HTML.index("\n}", start) + 2
    block = HTML[start:end]
    assert "2 * t" in block or "2*t" in block


def test_alloc_hint_half_threshold_present():
    """The ≤ half-target under-threshold check must appear."""
    start = HTML.index("function _dvAllocationHint(")
    end   = HTML.index("\n}", start) + 2
    block = HTML[start:end]
    assert "t / 2" in block or "t/2" in block


def test_alloc_hint_wired_into_rows():
    """_dvAllocationHint must be called inside the allocation row renderer."""
    assert "_dvAllocationHint(actualPct, target, a.label)" in HTML


def test_alloc_hint_renders_html():
    """The hint HTML output variable must be injected into the row HTML."""
    assert "hintHtml" in HTML


def test_alloc_hint_no_hint_when_target_zero():
    """Guard for target=0 must exist (avoids divide-by-zero / spurious hints)."""
    start = HTML.index("function _dvAllocationHint(")
    end   = HTML.index("\n}", start) + 2
    block = HTML[start:end]
    # The guard: if !(t > 0) return ''
    assert "!(t > 0)" in block or "t <= 0" in block or "t === 0" in block


# ─────────────────────────────────────────────────────────────────────────────
# #21 — Node-harness behavioural tests for _dvAllocationHint
# ─────────────────────────────────────────────────────────────────────────────

def _extract_alloc_hint_fn(html_text):
    """Extract the _dvAllocationHint function source for the node harness."""
    start = html_text.index("function _dvAllocationHint(")
    # Find the closing brace of this function (first top-level '}' after the opening)
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
    raise ValueError("Could not extract _dvAllocationHint function body")


_ALLOC_HINT_FN = _extract_alloc_hint_fn(HTML)

_NODE_HARNESS_TEMPLATE = """\
{fn_source}

var results = [];

function check(label, actual, target, assetLabel, expectContains, expectEmpty) {{
  var hint = _dvAllocationHint(actual, target, assetLabel);
  var pass;
  if (expectEmpty) {{
    pass = (hint === '');
  }} else {{
    pass = hint.indexOf(expectContains) !== -1;
  }}
  results.push({{ label: label, pass: pass, hint: hint }});
}}

// 1. ≥2× over: actual=40, target=15 → over hint with "Forex"
check('2x_over_forex', 40, 15, 'Forex', 'over your Forex target', false);

// 2. Exactly 2× over: actual=30, target=15 → triggers (boundary)
check('exactly_2x_over', 30, 15, 'Crypto', 'over your Crypto target', false);

// 3. ≤ half under: actual=5, target=15 → under hint
check('half_under', 5, 15, 'Stocks', 'under your Stocks target', false);

// 4. Exactly half: actual=7.5, target=15 → triggers (boundary)
check('exactly_half', 7.5, 15, 'Commodities', 'under your Commodities target', false);

// 5. Within bounds (1.5×): actual=20, target=15 → no hint
check('within_bounds_1_5x', 20, 15, 'Forex', '', true);

// 6. On target: actual=15, target=15 → no hint
check('on_target', 15, 15, 'Forex', '', true);

// 7. target=0 → no hint (guard)
check('target_zero', 50, 0, 'Cash', '', true);

// 8. actualPct=null → no hint
check('actual_null', null, 20, 'Forex', '', true);

// 9. Over hint must include computed percentage
check('over_pct_in_message', 40, 10, 'Equity', '%', false);

// 10. Just under 2× (1.99×): actual=29.9, target=15.05 → no hint
check('just_under_2x', 29.9, 15.05, 'Crypto', '', true);

console.log(JSON.stringify(results));
"""


def test_alloc_hint_node_behavioural():
    """Run _dvAllocationHint through node and assert all cases pass."""
    script = _NODE_HARNESS_TEMPLATE.format(fn_source=_ALLOC_HINT_FN)
    result = subprocess.run(
        ["node", "-e", script],
        capture_output=True, text=True, timeout=10
    )
    assert result.returncode == 0, f"node error: {result.stderr}"
    cases = json.loads(result.stdout.strip())
    failures = [c for c in cases if not c["pass"]]
    assert not failures, (
        "Failing _dvAllocationHint cases:\n" +
        "\n".join(f"  {c['label']}: hint={c['hint']!r}" for c in failures)
    )
