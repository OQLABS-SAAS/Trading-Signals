"""Static contract tests for P2 (logon briefing) and P3 (goal-aware Today).

Pattern mirrors test_intent_frontend_contracts.py — read the HTML as text,
assert markers are present.

P2 checks:
  1. /api/briefing fetch called on login (in goDash post-login block).
  2. window._dvBriefing cache set after successful fetch.
  3. _dvShowBriefing function defined.
  4. Briefing panel DOM marker (dvBriefingPanel).
  5. Dismiss function _dvDismissBriefing defined.
  6. sessionStorage flag 'dv_briefing_seen' set on dismiss.
  7. sessionStorage flag cleared on login (so briefing always shows on new login).
  8. Stance banner rendered inside briefing panel.
  9. Goal pace progress bars rendered.
  10. P&L KPI block rendered (today/week/month).

P3 checks:
  11. _todayGoalPace function defined.
  12. _todaySelectPlan reads goal pace (_todayGoalPace called inside).
  13. AHEAD tightening constants defined (_DV_QFLOOR_AHEAD_BUMP, _DV_MAX_TRADES_AHEAD).
  14. Behind-never-loosens comment present (explicit safety documentation).
  15. Pace message stored in window._todayPaceMsg.
  16. Pace explanation line (todayPaceBanner) injected into Today top area.
  17. Back-compat: no-intent path returns no tightening (comment documents this).
"""
from pathlib import Path

HTML_PATH = Path("static/index-v2-prototype.html")
HTML = HTML_PATH.read_text()


# ─── P2: briefing fetch ───────────────────────────────────────────────────────

def test_briefing_fetch_called_on_login():
    """/api/briefing must be fetched in the post-login (goDash) block."""
    assert "/api/briefing" in HTML


def test_briefing_fetch_is_in_godash():
    """The /api/briefing fetch must appear after the doLogin / goDash flow."""
    # Locate goDash and verify /api/briefing appears after it
    godash_pos  = HTML.index("function goDash(")
    briefing_pos = HTML.index("/api/briefing")
    assert briefing_pos > godash_pos, "/api/briefing fetch must be wired inside goDash"


def test_dvBriefing_cache_set():
    """window._dvBriefing must be assigned from the briefing fetch response."""
    assert "window._dvBriefing" in HTML


def test_dvBriefing_cached_after_fetch():
    """_dvBriefing should be assigned the response 'd' inside the fetch then-block."""
    start = HTML.index("/api/briefing")
    block = HTML[start:start + 400]
    assert "window._dvBriefing" in block, \
        "window._dvBriefing must be assigned immediately after the briefing fetch"


# ─── P2: panel functions and DOM ─────────────────────────────────────────────

def test_dvShowBriefing_function_defined():
    assert "function _dvShowBriefing(" in HTML


def test_dvDismissBriefing_function_defined():
    assert "function _dvDismissBriefing(" in HTML


def test_briefing_panel_id_marker():
    """dvBriefingPanel must be the panel's DOM id."""
    assert "dvBriefingPanel" in HTML


def test_briefing_panel_created_in_show_function():
    start = HTML.index("function _dvShowBriefing(")
    block = HTML[start:start + 7000]  # function is large; scan enough chars
    assert "dvBriefingPanel" in block


# ─── P2: dismiss flag lifecycle ──────────────────────────────────────────────

def test_dismiss_sets_sessionStorage_flag():
    """Dismissing the briefing must set 'dv_briefing_seen' in sessionStorage."""
    start = HTML.index("function _dvDismissBriefing(")
    block = HTML[start:start + 300]
    assert "dv_briefing_seen" in block
    assert "sessionStorage" in block


def test_login_clears_seen_flag():
    """goDash must clear the sessionStorage briefing-seen flag on every login."""
    start = HTML.index("function goDash(")
    # Find the end of goDash by counting depth
    depth = 0
    i = start
    while i < len(HTML):
        if HTML[i] == '{': depth += 1
        elif HTML[i] == '}':
            depth -= 1
            if depth == 0: break
        i += 1
    block = HTML[start:i+1]
    assert "dv_briefing_seen" in block, \
        "goDash must call sessionStorage.removeItem('dv_briefing_seen') on login"
    assert "removeItem" in block


# ─── P2: briefing panel content markers ──────────────────────────────────────

def test_briefing_panel_has_stance_banner():
    """The briefing panel must render the stance text from /api/briefing."""
    start = HTML.index("function _dvShowBriefing(")
    block = HTML[start:start + 4000]
    # Stance is rendered using stance.text
    assert "stance.text" in block or "stance" in block.lower()


def test_briefing_panel_renders_pnl():
    """The briefing panel must show today/week/month P&L KPIs."""
    start = HTML.index("function _dvShowBriefing(")
    block = HTML[start:start + 6000]
    assert "pnl.today" in block or "pnl" in block
    assert "Today" in block or "today" in block.lower()
    assert "Week" in block or "week" in block.lower()
    assert "Month" in block or "month" in block.lower()


def test_briefing_panel_renders_goal_pace():
    """The briefing panel must show goal pace progress bars."""
    start = HTML.index("function _dvShowBriefing(")
    block = HTML[start:start + 6000]
    assert "Goal pace" in block or "goal" in block.lower()


def test_briefing_panel_renders_open_positions():
    """The briefing panel must list open positions."""
    start = HTML.index("function _dvShowBriefing(")
    block = HTML[start:start + 6000]
    assert "open_positions" in block or "Open positions" in block


def test_briefing_kpi_helper_defined():
    """_dvBriefingKPI helper must be defined (used to render P&L grid)."""
    assert "function _dvBriefingKPI(" in HTML


# ─── P3: _todayGoalPace function ─────────────────────────────────────────────

def test_todayGoalPace_function_defined():
    assert "function _todayGoalPace(" in HTML


def test_todayGoalPace_reads_intent():
    """_todayGoalPace must call _dvIntentGet to source goals."""
    start = HTML.index("function _todayGoalPace(")
    block = HTML[start:start + 800]
    assert "_dvIntentGet" in block


def test_todayGoalPace_reads_briefing_cache():
    """_todayGoalPace must reference window._dvBriefing for P&L data."""
    start = HTML.index("function _todayGoalPace(")
    block = HTML[start:start + 800]
    assert "window._dvBriefing" in block or "_dvBriefing" in block


def test_todayGoalPace_returns_ahead_false_when_no_intent():
    """The no-intent fallback must return ahead=false (back-compat)."""
    start = HTML.index("function _todayGoalPace(")
    block = HTML[start:start + 800]
    # The function must explicitly handle the no-horizon case
    assert "ahead: false" in block or "ahead:false" in block


# ─── P3: _todaySelectPlan tightening ─────────────────────────────────────────

def test_todaySelectPlan_calls_todayGoalPace():
    """_todaySelectPlan must call _todayGoalPace to read current pace."""
    # Find the LAST definition of _todaySelectPlan (the P3-updated one)
    pos = HTML.rindex("function _todaySelectPlan(")
    block = HTML[pos:pos + 2500]
    assert "_todayGoalPace" in block, "_todaySelectPlan must call _todayGoalPace()"


def test_ahead_tightening_constants_defined():
    """P3 AHEAD bump constants must be defined."""
    assert "_DV_QFLOOR_AHEAD_BUMP" in HTML
    assert "_DV_MAX_TRADES_AHEAD"  in HTML


def test_qfloor_bump_is_ten():
    """The quality floor bump must be 10 (one notch on the 0-100 QFLOOR scale)."""
    assert "_DV_QFLOOR_AHEAD_BUMP   = 10" in HTML or "_DV_QFLOOR_AHEAD_BUMP=10" in HTML or \
           "_DV_QFLOOR_AHEAD_BUMP = 10" in HTML


def test_max_trades_ahead_is_three():
    """When ahead, basket is capped at 3 trades (conservative)."""
    assert "_DV_MAX_TRADES_AHEAD     = 3" in HTML or "_DV_MAX_TRADES_AHEAD=3" in HTML or \
           "_DV_MAX_TRADES_AHEAD = 3" in HTML or "_DV_MAX_TRADES_AHEAD    = 3" in HTML


def test_behind_never_loosens_comment_present():
    """The 'BEHIND never loosens' safety rule must be explicitly documented in a comment."""
    pos = HTML.rindex("function _todaySelectPlan(")
    block = HTML[pos:pos + 3000]
    # Must have an explicit comment that behind never loosens
    assert "BEHIND never loosens" in block or "behind never loosens" in block.lower() or \
           "never force junk" in block.lower() or "never loosen" in block.lower(), \
        "Behind-never-loosens safety rule must be in a comment inside _todaySelectPlan"


def test_behind_never_loosens_no_else_branch_for_behind():
    """There must be no code path that adjusts gates downward for 'behind' pace."""
    pos = HTML.rindex("function _todaySelectPlan(")
    block = HTML[pos:pos + 3000]
    # Ensure the tightening only happens on pace.ahead, not on !pace.ahead
    # i.e. there's no 'else' branch that reduces effectiveQfloor or increases max
    # This is verified by confirming QFLOOR is only ever incremented, never decremented
    assert "effectiveQfloor - " not in block, \
        "Quality floor must never be lowered — behind does not trigger looser gates"
    assert "max + " not in block or "max +" not in block, \
        "maxTrades must never be increased — behind does not trigger more trades"


# ─── P3: pace message surfaced in UI ─────────────────────────────────────────

def test_todayPaceMsg_stored_on_window():
    """_todaySelectPlan must store the pace message in window._todayPaceMsg."""
    pos = HTML.rindex("function _todaySelectPlan(")
    block = HTML[pos:pos + 3000]
    assert "window._todayPaceMsg" in block


def test_todayPaceBanner_injected_in_renderTop():
    """_todayRenderTop must inject the todayPaceBanner element when paceMsg is set."""
    start = HTML.index("function _todayRenderTop(")
    block = HTML[start:start + 3000]
    assert "todayPaceBanner" in block
    assert "_todayPaceMsg" in block or "paceMsg" in block


def test_pace_explanation_text_is_human_readable():
    """The pace tightening explanation must be a user-facing sentence."""
    pos = HTML.rindex("function _todaySelectPlan(")
    block = HTML[pos:pos + 3000]
    # Must contain the explanation string mentioning goal and being selective
    assert "ahead of your" in block or "ahead of" in block


def test_pace_banner_uses_green_styling():
    """The AHEAD banner should use a green colour to indicate positive status."""
    start = HTML.index("function _todayRenderTop(")
    block = HTML[start:start + 3000]
    assert "93,232,160" in block  # DotVerse green colour in the pace banner


# ─── P3: back-compat when no intent set ──────────────────────────────────────

def test_no_intent_path_uses_original_max():
    """When no intent is set, _todaySelectPlan uses cfg.maxTrades (no tightening)."""
    pos = HTML.rindex("function _todaySelectPlan(")
    block = HTML[pos:pos + 3000]
    # The pace.ahead guard only tightens; it never runs if pace.ahead is false
    # Confirm the tightening is inside if(pace.ahead){...}
    assert "if(pace.ahead)" in block or "if (pace.ahead)" in block
