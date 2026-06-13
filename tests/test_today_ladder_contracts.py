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
