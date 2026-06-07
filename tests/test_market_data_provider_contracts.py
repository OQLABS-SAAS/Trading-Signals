from pathlib import Path


APP = Path("app.py").read_text()


def _block(start_marker: str, end_marker: str) -> str:
    start = APP.index(start_marker)
    end = APP.index(end_marker, start)
    return APP[start:end]


def test_live_price_uses_provider_first_not_yfinance_ticker():
    block = _block('def live_price():', '@app.route("/api/analyze"')
    assert "provider_first_download(" in block
    assert "yf.Ticker" not in block
    assert '"provider_order": "eodhd-first"' in block


def test_prices_route_uses_provider_first_not_yfinance_batch():
    block = _block('def get_prices():', "# ─── MACRO DATA")
    assert "provider_first_download(" in block
    assert "yf.download" not in block
    assert '"provider_order": "eodhd-first"' in block


def test_scan_list_uses_provider_first_for_signal_voting():
    block = _block('def scan_list():', "# /api/chat endpoint removed")
    assert "provider_first_download(raw" in block
    assert "yf.download" not in block


def test_analyze_and_backtest_have_provider_first_ohlc_paths():
    assert "df = provider_first_download(ticker, period=cfg[\"period\"], interval=cfg[\"interval\"], asset_type=asset_type)" in APP
    assert "df_daily = provider_first_download(ticker, period=\"1y\", interval=\"1d\", asset_type=asset_type)" in APP
    assert "df_bt = provider_first_download(ticker_n, period=period_map.get(timeframe,\"1y\")," in APP


def test_analyze_uses_single_defined_request_body_for_markov_toggles():
    block = _block('def analyze():', '# ── STEP 1: TradingView')

    assert "body = request.get_json(silent=True) or {}" in block
    assert "normalize_analyze_payload(\n                body," in block
    assert '_use_markov    = body.get("use_markov", False)' in APP


def test_market_sector_and_new_listing_routes_use_provider_first():
    sectors = _block('def sector_performance():', '@app.route("/api/new-listings"')
    listings = _block('def new_listings():', '@app.route("/api/daily-brief"')

    assert 'provider_first_download(etf, period="5d", interval="1d", asset_type="stock")' in sectors
    assert "yf.Ticker(etf)" not in sectors
    assert 'provider_first_download(ticker, period="3mo", interval="1d", asset_type=atype)' in listings
    assert 'safe_download(ticker, period="3mo", interval="1d")' not in listings


def test_sync_backtest_tries_provider_first_before_direct_stooq_fallbacks():
    block = _block('def backtest_route():', '# ─── RQ Backtest')
    provider_idx = block.index("provider-first OHLC")
    stooq_idx = block.index("Stooq direct fallback")
    fmp_idx = block.index("FMP direct fallback")

    assert provider_idx < stooq_idx < fmp_idx
