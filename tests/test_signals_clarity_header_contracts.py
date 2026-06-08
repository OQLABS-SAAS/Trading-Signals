"""
Contract tests for the Signals feed clarity header (_sfBuildClarityHeader).

These tests assert on the *source text* of index-v2-prototype.html — they verify
the implementation shape (function present, correct field references, graceful
missing-data handling, clear-filters control) without executing the browser JS.
"""
from pathlib import Path

HTML = Path("static/index-v2-prototype.html").read_text()


# ── helpers ──────────────────────────────────────────────────────────────────

def _extract_block(start_marker, end_marker):
    """Return the text between the first occurrence of two markers."""
    start = HTML.index(start_marker)
    end   = HTML.index(end_marker, start)
    return HTML[start:end]


# ── 1. Function existence ─────────────────────────────────────────────────────

def test_clarity_header_function_exists():
    assert "function _sfBuildClarityHeader()" in HTML


def test_clear_all_filters_function_exists():
    assert "function _sfClearAllFilters()" in HTML


# ── 2. Called from _sfRender ──────────────────────────────────────────────────

def test_clarity_header_invoked_in_sfRender():
    """_sfRender must call _sfBuildClarityHeader so it appears in the feed."""
    render_start = HTML.index("function _sfRender()")
    render_end   = HTML.index("\nfunction ", render_start + 1)
    render_block = HTML[render_start:render_end]
    assert "_sfBuildClarityHeader()" in render_block


# ── 3. Scan-time section uses the right field ─────────────────────────────────

def test_clarity_header_uses_as_of_utc():
    block = _extract_block("function _sfBuildClarityHeader()", "function _sfClearAllFilters()")
    assert "run.as_of_utc" in block


def test_clarity_header_relative_time_labels():
    """Relative time labels must cover the sub-minute and minute-range cases."""
    block = _extract_block("function _sfBuildClarityHeader()", "function _sfClearAllFilters()")
    assert "just now" in block
    assert "m ago" in block
    assert "h ago" in block


def test_clarity_header_rejects_negative_or_future_timestamps():
    """Only non-negative diffMs should produce a label (never show wrong time)."""
    block = _extract_block("function _sfBuildClarityHeader()", "function _sfClearAllFilters()")
    # The guard must be present
    assert "diffMs >= 0" in block


# ── 4. Scope section uses correct fields ─────────────────────────────────────

def test_clarity_header_uses_scan_scope():
    block = _extract_block("function _sfBuildClarityHeader()", "function _sfClearAllFilters()")
    assert "run.scan_scope" in block


def test_clarity_header_reads_tickers_and_asset_type():
    block = _extract_block("function _sfBuildClarityHeader()", "function _sfClearAllFilters()")
    assert "s.tickers" in block
    assert "s.asset_type" in block


# ── 5. Provider-health section uses correct fields ────────────────────────────

def test_clarity_header_uses_provider_health():
    block = _extract_block("function _sfBuildClarityHeader()", "function _sfClearAllFilters()")
    assert "run.provider_health" in block


def test_clarity_header_uses_ready_count_and_failed_count():
    block = _extract_block("function _sfBuildClarityHeader()", "function _sfClearAllFilters()")
    assert "ph.ready_count" in block
    assert "ph.failed_count" in block


def test_clarity_header_error_line_only_when_failed_gt_zero():
    """Error text must be conditional on failed > 0, not always shown."""
    block = _extract_block("function _sfBuildClarityHeader()", "function _sfClearAllFilters()")
    assert "failed > 0" in block


# ── 6. Filter chips ───────────────────────────────────────────────────────────

def test_clarity_header_reads_sfFilter_fields():
    block = _extract_block("function _sfBuildClarityHeader()", "function _sfClearAllFilters()")
    for key in ("f.asset", "f.dir", "f.status", "f.conf"):
        assert key in block, f"Expected '{key}' in clarity header block"


def test_clarity_header_reads_condFilter_badge():
    block = _extract_block("function _sfBuildClarityHeader()", "function _sfClearAllFilters()")
    assert "window._condFilter" in block
    assert "_condFilter.badge" in block


def test_clarity_header_reads_sfVerifiedOnly():
    block = _extract_block("function _sfBuildClarityHeader()", "function _sfClearAllFilters()")
    assert "window._sfVerifiedOnly" in block


def test_clarity_header_always_visible_clear_button():
    """Clear filters button must always render (not inside a conditional chip block)."""
    block = _extract_block("function _sfBuildClarityHeader()", "function _sfClearAllFilters()")
    assert "_sfClearAllFilters()" in block
    assert "Clear filters" in block


# ── 7. _sfClearAllFilters resets all filter state ────────────────────────────

def test_clear_all_filters_resets_sfFilter():
    block = _extract_block("function _sfClearAllFilters()", "function _sfRender()")
    assert "_sfFilter" in block
    assert "asset:'all'" in block


def test_clear_all_filters_clears_condFilter():
    block = _extract_block("function _sfClearAllFilters()", "function _sfRender()")
    assert "window._condFilter = null" in block


def test_clear_all_filters_clears_verified_only():
    block = _extract_block("function _sfClearAllFilters()", "function _sfRender()")
    assert "window._sfVerifiedOnly = false" in block


def test_clear_all_filters_invalidates_cache():
    """Cache must be cleared so the next render fetches fresh results."""
    block = _extract_block("function _sfClearAllFilters()", "function _sfRender()")
    assert "window._sfResultCache = null" in block


def test_clear_all_filters_triggers_rerender():
    block = _extract_block("function _sfClearAllFilters()", "function _sfRender()")
    assert "_sfRender()" in block


# ── 8. Graceful no-scan state ─────────────────────────────────────────────────

def test_clarity_header_handles_missing_run_gracefully():
    """When window._dvSignalUniverseRun is absent, return a hint — never crash."""
    block = _extract_block("function _sfBuildClarityHeader()", "function _sfClearAllFilters()")
    # The guard at the top of the function
    assert "var run = window._dvSignalUniverseRun" in block
    assert "if (!run)" in block
    # The returned string should mention running a scan
    assert "Run a scan" in block


def test_clarity_header_try_catch_around_time_parse():
    """Each data section must be wrapped so a bad field never crashes the render."""
    block = _extract_block("function _sfBuildClarityHeader()", "function _sfClearAllFilters()")
    # Must see multiple try/catch blocks (at least 3 for time, scope, health)
    count = block.count("try {")
    assert count >= 3, f"Expected at least 3 try blocks in clarity header, got {count}"


# ── 9. DOM anchor id for the header ──────────────────────────────────────────

def test_clarity_header_has_stable_dom_id():
    """sfClarityHeader id lets tests (and future JS) address the element."""
    block = _extract_block("function _sfBuildClarityHeader()", "function _sfClearAllFilters()")
    assert 'id="sfClarityHeader"' in block
