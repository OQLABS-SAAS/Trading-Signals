"""
Contract tests for Act-tab stale/stuck order warnings.

These tests verify that the frontend JS in static/index-v2-prototype.html:
  1. Declares a 120-second stale threshold (_MT5_STALE_SECS = 120).
  2. Has helper functions _mt5OrderAgeSecs and _mt5FmtAge.
  3. Emits a warning for stale pending/executing rows.
  4. Emits a subtle "Placed X ago" note for non-stale pending/executing rows.
  5. Gracefully omits age display when created_at is absent or unparseable.
  6. Does NOT emit any auto-cancel, auto-retry, or order-mutation logic near the warning.
"""

import re
import json
import subprocess
from pathlib import Path
import pytest

HTML_PATH = "static/index-v2-prototype.html"

@pytest.fixture(scope="module")
def html():
    with open(HTML_PATH, "r", encoding="utf-8") as f:
        return f.read()


def _node_available() -> bool:
    try:
        subprocess.run(["node", "--version"], capture_output=True, timeout=5)
        return True
    except Exception:
        return False


def _extract_fn(src: str, fn_name: str) -> str:
    marker = "function " + fn_name + "("
    start = src.find(marker)
    if start < 0:
        raise RuntimeError(f"function {fn_name} not found")
    depth = 0
    started = False
    for idx in range(start, len(src)):
        ch = src[idx]
        if ch == "{":
            depth += 1
            started = True
        elif ch == "}":
            depth -= 1
            if started and depth == 0:
                return src[start:idx + 1]
    raise RuntimeError(f"unbalanced braces for {fn_name}")


def _run_node(script: str) -> dict:
    result = subprocess.run(
        ["node", "-e", script],
        capture_output=True,
        text=True,
        timeout=15,
        cwd=Path(__file__).parent.parent,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr[:1000])
    return json.loads(result.stdout.strip())


# ── 1. Stale threshold constant ────────────────────────────────────────────────

def test_stale_threshold_constant_declared(html):
    """_MT5_STALE_SECS must be declared and set to 120."""
    assert "_MT5_STALE_SECS" in html, "_MT5_STALE_SECS constant not found in HTML"
    # Must be assigned 120 (allow spaces around =)
    assert re.search(r"_MT5_STALE_SECS\s*=\s*120\b", html), \
        "_MT5_STALE_SECS is not set to 120"


# ── 2. Helper functions present ────────────────────────────────────────────────

def test_age_helper_function_declared(html):
    """_mt5OrderAgeSecs must be declared as a function."""
    assert "function _mt5OrderAgeSecs" in html, \
        "_mt5OrderAgeSecs function not found in HTML"


def test_fmt_age_helper_function_declared(html):
    """_mt5FmtAge must be declared as a function."""
    assert "function _mt5FmtAge" in html, \
        "_mt5FmtAge function not found in HTML"


# ── 3. Stale warning markup ────────────────────────────────────────────────────

def test_stale_warning_text_present(html):
    """The stale warning message must reference 'may not have reached your broker'."""
    assert "may not have reached your broker" in html, \
        "Stale-order warning text not found in HTML"


def test_stale_warning_check_mt5_text_present(html):
    """The stale warning must advise the user to 'Check MT5'."""
    assert "Check MT5" in html, \
        "'Check MT5' advisory text not found in stale warning"


def test_stale_warning_uses_stale_threshold(html):
    """The render path must compare ageSecs against _MT5_STALE_SECS."""
    assert re.search(r"ageSecs\s*>=\s*_MT5_STALE_SECS", html), \
        "Stale threshold comparison (ageSecs >= _MT5_STALE_SECS) not found"


def test_stale_warning_shows_elapsed_time(html):
    """The stale warning must embed the formatted age string."""
    # The warning block uses ageStr in its text
    assert re.search(r"has been.*for.*ageStr", html, re.DOTALL), \
        "Stale warning does not include the elapsed ageStr in output"


def test_stale_warning_only_for_pending_executing(html):
    """The stale/age block must be gated on pending or executing status."""
    # The if-block must check o.status
    assert re.search(
        r"o\.status\s*===\s*['\"]pending['\"]\s*\|\|\s*o\.status\s*===\s*['\"]executing['\"]",
        html
    ), "Stale check is not gated on pending/executing status"


# ── 4. Subtle "Placed ago" for non-stale rows ─────────────────────────────────

def test_placed_ago_text_present(html):
    """Non-stale pending/executing rows must show 'Placed' + age + 'ago'."""
    assert re.search(r"Placed.*ago", html), \
        "'Placed X ago' text not found in HTML"


def test_placed_ago_uses_age_str(html):
    """The placed-ago note must embed the formatted ageStr."""
    assert re.search(r"Placed.*\+.*ageStr.*\+.*ago", html, re.DOTALL), \
        "'Placed' + ageStr + 'ago' pattern not found"


# ── 5. Graceful handling of missing/unparseable timestamp ─────────────────────

def test_age_helper_returns_null_on_falsy_input(html):
    """_mt5OrderAgeSecs must return null when createdAt is falsy."""
    assert re.search(r"if\s*\(\s*!createdAt", html), \
        "Guard for missing createdAt not found in _mt5OrderAgeSecs"


def test_age_helper_returns_null_on_nan(html):
    """_mt5OrderAgeSecs must check isNaN(t) and return null."""
    assert "isNaN(t)" in html, \
        "isNaN guard not found in _mt5OrderAgeSecs"


def test_age_helper_rejects_negative_age(html):
    """_mt5OrderAgeSecs must return null for negative ages (future timestamps)."""
    assert re.search(r"ageSecs\s*>=\s*0\s*\?", html), \
        "Negative-age guard not found in _mt5OrderAgeSecs"


def test_stale_block_only_rendered_when_age_not_null(html):
    """The stale/placed-ago block must only render when ageSecs !== null."""
    assert re.search(r"ageSecs\s*!==\s*null", html), \
        "Null-check on ageSecs not found before rendering warning"


def test_try_catch_in_age_helper(html):
    """_mt5OrderAgeSecs must be wrapped in try/catch for parse safety."""
    # Locate the function body and confirm try/catch is present within it
    m = re.search(r"function _mt5OrderAgeSecs\(.*?\}\s*\n", html, re.DOTALL)
    if m:
        snippet = m.group(0)
    else:
        snippet = html  # fallback: check whole file
    assert "try {" in snippet or "try{" in snippet, \
        "try/catch not found in _mt5OrderAgeSecs"


# ── 6. No auto-cancel / order-mutation in warning path ─────────────────────────

def test_no_auto_cancel_in_stale_warning(html):
    """The stale warning block must not issue a cancel call automatically."""
    # The warning block (staleWarningHtml) must not call mt5CancelOrder
    # Find the stale warning HTML string in the source and confirm it contains no cancel call
    m = re.search(r"staleWarningHtml\s*=\s*'(.*?)'", html, re.DOTALL)
    if m:
        warning_html = m.group(1)
        assert "mt5CancelOrder" not in warning_html, \
            "staleWarningHtml must not auto-invoke mt5CancelOrder"


def test_no_fetch_in_stale_warning(html):
    """The stale warning rendering must not trigger any dvFetch / fetch call."""
    m = re.search(r"staleWarningHtml\s*=\s*'(.*?)'", html, re.DOTALL)
    if m:
        warning_html = m.group(1)
        assert "dvFetch" not in warning_html and "fetch(" not in warning_html, \
            "staleWarningHtml must not issue any network request"


def test_mt5_poll_refreshes_order_history(html):
    """Act order history must refresh while the trader stays on the Act tab."""
    assert "function mt5RefreshOrderHistory()" in html
    start = html.index("function mt5Poll()")
    end = html.index("function mt5LoadTab()", start)
    block = html[start:end]
    assert "mt5RefreshOrderHistory();" in block
    assert "actRefreshOrderFeed();" not in block

    helper_start = html.index("function mt5RefreshOrderHistory()")
    helper_end = html.index("function mt5Poll()", helper_start)
    helper_block = html[helper_start:helper_end]
    assert "dvFetch('/api/mt5/orders')" in helper_block
    assert "_mt5RenderOrders(d.orders || [])" in helper_block


def test_cancel_uses_order_fetch_and_does_not_claim_unconfirmed_cancel(html):
    """Cancel must inspect server response instead of always saying cancelled."""
    start = html.index("function mt5CancelOrder(orderId)")
    end = html.index("function actSetTrailingReal", start)
    block = html[start:end]
    assert "dvOrderFetch('/api/mt5/cancel/'" in block
    assert "d._ok && d.status === 'cancelled'" in block
    assert "Order cancelled before MT5 picked it up" in block
    assert "Cancel not confirmed" in block
    assert "mt5RefreshOrderHistory()" in block
    assert "actRefreshOrderFeed()" not in block


def test_move_stop_to_entry_button_uses_real_breakeven_action(html):
    """Visible live-trade button must call the real MT5 breakeven endpoint helper."""
    assert "function actMoveToBreakevenReal(ticket, bePrice)" in html
    assert "Move stop to entry</button>" in html
    assert "actMoveToBreakevenReal(\\''+ticket+'\\',\\''+openPrice+'\\')" in html
    start = html.index("function actMoveToBreakevenReal(ticket, bePrice)")
    end = html.index("// Visual state restored", start)
    block = html[start:end]
    assert "dvOrderFetch('/api/mt5/breakeven'" in block
    assert "'/api/mt5/close'" not in block
    assert "Break-even move not confirmed" in block


def test_failed_order_rows_hide_internal_queue_comments(html):
    """Failed rows must not show acct/internal queue comments directly to the trader."""
    assert "function _mt5FailedOrderText(o)" in html
    start = html.index("function _mt5FailedOrderText(o)")
    end = html.index("function _mt5RenderOrders(orders)", start)
    block = html[start:end]
    assert "/DotVerse|acct=|LIVE|DEMO/.test(c)" in block
    assert "Check MT5 journal for the exact broker message" in block
    assert "_esc(_dvHumanizeError(c))" in block
    render_start = html.index("function _mt5RenderOrders(orders)")
    render_end = html.index("function mt5Poll()", render_start)
    render_block = html[render_start:render_end]
    assert "_mt5FailedOrderText(o)" in render_block


@pytest.mark.skipif(not _node_available(), reason="node not available")
def test_runtime_current_mt5_account_id_prefers_state_account_id(html):
    fn = _extract_fn(html, "_dvCurrentMt5AccountId")
    result = _run_node(
        fn
        + """
global.window = {_mt5LastState:{account_id:7, account:{id:99, account_id:88}}, _todayLastMt5State:{account_id:3}};
console.log(JSON.stringify({accountId:_dvCurrentMt5AccountId()}));
"""
    )
    assert result == {"accountId": 7}


@pytest.mark.skipif(not _node_available(), reason="node not available")
def test_runtime_mt5_refresh_order_history_fetches_and_renders_orders(html):
    fn = _extract_fn(html, "mt5RefreshOrderHistory")
    result = _run_node(
        fn
        + """
var calls = [];
function dvFetch(path){ calls.push(['fetch', path]); return Promise.resolve({orders:[{id:1},{id:2}]}); }
function _mt5RenderOrders(orders){ calls.push(['render', orders.length]); }
(async function(){
  await mt5RefreshOrderHistory();
  console.log(JSON.stringify({calls:calls}));
})();
"""
    )
    assert result == {"calls": [["fetch", "/api/mt5/orders"], ["render", 2]]}


@pytest.mark.skipif(not _node_available(), reason="node not available")
def test_runtime_move_stop_to_entry_posts_breakeven_not_close(html):
    fn = _extract_fn(html, "actMoveToBreakevenReal")
    result = _run_node(
        fn
        + """
var calls = [];
function _dvCurrentMt5AccountId(){ return 7; }
function dvOrderFetch(path, opts){
  calls.push(['orderFetch', path, JSON.parse(opts.body)]);
  return Promise.resolve({_ok:true, status:'ok'});
}
function _dvToast(msg){ calls.push(['toast', msg]); }
function mt5RefreshOrderHistory(){ calls.push(['history']); return Promise.resolve(); }
function mt5Poll(){ calls.push(['poll']); }
function _mt5OrderErrorText(){ return 'error'; }
function _mt5ConfirmMoneyAction(action, detail){ calls.push(['confirm', action, detail]); return true; }
(async function(){
  await actMoveToBreakevenReal('555', '1.081');
  console.log(JSON.stringify({calls:calls}));
})();
"""
    )
    assert result["calls"][0] == [
        "confirm",
        "Move stop loss to entry for ticket 555",
        "New stop-loss price: 1.081",
    ]
    assert result["calls"][1] == [
        "orderFetch",
        "/api/mt5/breakeven",
        {"ticket": "555", "be_price": "1.081", "account_id": 7},
    ]
    assert all(call[1] != "/api/mt5/close" for call in result["calls"] if call[0] == "orderFetch")
    assert ["history"] in result["calls"]
    assert ["poll"] in result["calls"]
    assert any(call[0] == "confirm" for call in result["calls"])


@pytest.mark.skipif(not _node_available(), reason="node not available")
def test_runtime_set_trailing_uses_order_fetch_and_requires_confirmed_status(html):
    fn = _extract_fn(html, "actSetTrailingReal")
    result = _run_node(
        fn
        + """
var calls = [];
global.document = { getElementById:function(id){ return id === 'pftrail-555' ? {value:'35'} : null; } };
function _dvCurrentMt5AccountId(){ return 7; }
function dvOrderFetch(path, opts){
  calls.push(['orderFetch', path, JSON.parse(opts.body)]);
  return Promise.resolve({_ok:true, status:'ok'});
}
function _dvToast(msg){ calls.push(['toast', msg]); }
function mt5RefreshOrderHistory(){ calls.push(['history']); return Promise.resolve(); }
function mt5Poll(){ calls.push(['poll']); }
function _mt5OrderErrorText(){ return 'error'; }
function _mt5ConfirmMoneyAction(action, detail){ calls.push(['confirm', action, detail]); return true; }
(async function(){
  await actSetTrailingReal('555');
  console.log(JSON.stringify({calls:calls}));
})();
"""
    )
    assert result["calls"][0] == [
        "confirm",
        "Queue trailing stop for ticket 555",
        "Trailing distance: 35 pips",
    ]
    assert result["calls"][1] == [
        "orderFetch",
        "/api/mt5/trailing",
        {"ticket": "555", "pips": 35, "account_id": 7},
    ]
    assert ["history"] in result["calls"]
    assert ["poll"] in result["calls"]


@pytest.mark.skipif(not _node_available(), reason="node not available")
def test_runtime_close_position_uses_order_fetch_and_surfaces_response_errors(html):
    fn = _extract_fn(html, "mt5ClosePosition")
    result = _run_node(
        fn
        + """
var calls = [];
function parseInt(v){ return Number(v); }
global.document = { getElementById:function(){ return null; } };
function _dvCurrentMt5AccountId(){ return 7; }
function dvOrderFetch(path, opts){
  calls.push(['orderFetch', path, JSON.parse(opts.body)]);
  return Promise.resolve({_ok:false,_httpStatus:403,error:'Position 555 not found or not yours'});
}
function _mt5OrderErrorText(res){ calls.push(['errorText', res.error]); return res.error; }
function _dvToast(msg){ calls.push(['toast', msg]); }
function mt5RefreshOrderHistory(){ calls.push(['history']); return Promise.resolve(); }
function _closePaperTrade(){ calls.push(['paper']); }
function _mt5ConfirmMoneyAction(action, detail){ calls.push(['confirm', action, detail]); return true; }
(async function(){
  await mt5ClosePosition('555', 'EURUSD', 'SL');
  console.log(JSON.stringify({calls:calls}));
})();
"""
    )
    assert result["calls"][0] == ["confirm", "Queue close order for EURUSD", "Ticket 555"]
    assert result["calls"][1] == [
        "orderFetch",
        "/api/mt5/close",
        {"ticket": "555", "symbol": "EURUSD", "level": "SL", "account_id": 7},
    ]
    assert ["errorText", "Position 555 not found or not yours"] in result["calls"]
    assert ["toast", "Position 555 not found or not yours"] in result["calls"]
    assert ["history"] in result["calls"]


def test_order_history_renders_account_badge(html):
    """Act order history must show which MT5 account each row belongs to."""
    start = html.index("function _mt5RenderOrders(orders)")
    end = html.index("function mt5RefreshOrderHistory()", start)
    block = html[start:end]
    assert ">ACCOUNT<" in block
    assert "acctLabel" in block
    assert "o.account_number" in block
    assert "o.account_id" in block
