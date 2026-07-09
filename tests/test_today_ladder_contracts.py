from pathlib import Path


HTML = Path("static/index-v2-prototype.html").read_text()


def test_today_ladder_uses_stacked_beginner_order_cards():
    assert ".today-v2-leg{display:grid;grid-template-columns:minmax(0,1fr)" in HTML
    assert ".today-v2-legGrid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr))" in HTML
    assert ".today-v2-legBadge" in HTML
    assert "Each row below is one MT5 order" in HTML
    assert "MT5 volume is lots, units, contracts, or shares; cash in is margin; controls is position value." in HTML


def test_today_ladder_removes_forced_horizontal_scroll_rows():
    assert ".today-v2-ladder{overflow-x:auto}" not in HTML
    assert ".today-v2-leg{min-width:650px}" not in HTML
    assert "grid-template-columns:78px minmax(86px,1fr) 92px 86px 86px 72px" not in HTML


def test_today_ladder_explains_cash_controls_lots_and_risk():
    assert "MT5 volume for this order." in HTML
    assert "Cash in: margin you put up." in HTML
    assert "Position value controlled." in HTML
    assert "function legSizeText(l)" in HTML
    assert "esc(legSizeText(l))" in HTML
    assert "Controls: position value. Lots:" not in HTML
    assert "Risk if stop-loss hits:" in HTML
    assert "Can make if this order reaches its target." in HTML
    assert "Share of this setup assigned to this order." in HTML


def test_today_bottom_summary_reflows_without_nine_column_grid():
    assert ".today-v2-bottom{position:static" in HTML
    assert "grid-template-columns:repeat(auto-fit,minmax(132px,1fr))" in HTML
    assert "grid-template-columns:repeat(8,minmax(104px,1fr)) 178px" not in HTML


def test_today_v2_has_phone_and_tablet_friendly_breakpoints():
    assert "@media(max-width:1180px)" in HTML
    assert "@media(max-width:900px)" in HTML
    assert "@media(max-width:520px)" in HTML
    assert ".today-page.v2{padding-bottom:16px;max-width:100%;overflow-x:hidden}" in HTML
    assert ".today-v2-setup{grid-template-columns:repeat(2,minmax(0,1fr))}" in HTML
    assert ".today-v2-summary{grid-template-columns:repeat(2,minmax(0,1fr))}" in HTML
    assert ".today-v2-tableWrap{overflow-x:auto;-webkit-overflow-scrolling:touch}" in HTML
    assert ".today-v2-tableWrap{overflow:visible}" in HTML
    assert ".today-v2-table,.today-v2-table thead,.today-v2-table tbody,.today-v2-table tr,.today-v2-table td{display:block;width:100%;box-sizing:border-box}" in HTML
    assert ".today-v2-table thead{display:none}" in HTML
    assert ".today-v2-table td{display:grid;grid-template-columns:92px minmax(0,1fr)" in HTML
    for label in ["Trade", "Readiness", "Duration", "Volume", "Risk", "R:R", "Profit", "Mode", "Why"]:
        assert f'content:"{label}"' in HTML
    assert ".today-v2-review{width:100%;min-height:44px}" in HTML
    assert ".today-v2-selectedTop,.today-v2-switch,.today-v2-scout{align-items:stretch;flex-direction:column}" in HTML
