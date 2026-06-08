"""CR-1 regression tests: commodity contract-size position sizing.

Backend tests verify that _calc_auto_lot divides by the correct contract size
so that a $100 risk on silver at a $0.50 stop-loss produces ~0.04 lots, NOT ~200.

Frontend tests (string-contract style matching the existing test suite) verify
that both _szContractSize and _todayContractSize return the correct sizes for
Yahoo Finance tickers (SI=F, GC=F, CL=F, NG=F, HG=F) as well as broker symbols
(XAGUSD, XAUUSD, WTI, NGAS, COPPER) in both map copies.
"""

import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Backend imports
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-prod")
os.environ.setdefault("REDIS_URL", "")

import app as dvapp  # noqa: E402  (after sys.path manipulation)

# ---------------------------------------------------------------------------
# Frontend HTML
# ---------------------------------------------------------------------------
HTML = Path("static/index-v2-prototype.html").read_text()


# ===========================================================================
# BACKEND: _calc_auto_lot contract-size correctness
# ===========================================================================

# Shared test parameters: $10,000 account, 1% risk = $100, $0.50 SL distance.
# Expected lots = risk_amt / (sl_dist * contract_size)
_BALANCE = 10_000.0
_RISK_PCT = 1.0          # 1 % => $100 risk
_SL_DIST  = 0.50         # e.g. 30 cents / $0.50 / $0.50 price move


def _expected_lots(contract_size: float) -> float:
    risk_amt = _BALANCE * (_RISK_PCT / 100.0)
    return round(risk_amt / (_SL_DIST * contract_size), 2)


class TestBackendContractSizeLots:
    """_calc_auto_lot must divide by contract size for all commodity assets."""

    def _lot(self, ticker: str) -> float:
        entry = 30.0
        sl = entry - _SL_DIST
        return dvapp._calc_auto_lot(
            _BALANCE, entry, sl, "commodity", risk_pct=_RISK_PCT, ticker=ticker
        )

    # --- Silver (5,000 oz / lot) ---
    def test_silver_yahoo_ticker(self):
        result = self._lot("SI=F")
        assert result == _expected_lots(5000), (
            f"SI=F: expected {_expected_lots(5000)} lots, got {result}"
        )

    def test_silver_broker_symbol(self):
        result = self._lot("XAGUSD")
        assert result == _expected_lots(5000), (
            f"XAGUSD: expected {_expected_lots(5000)} lots, got {result}"
        )

    # --- Gold (100 oz / lot) ---
    def test_gold_yahoo_ticker(self):
        result = self._lot("GC=F")
        assert result == _expected_lots(100), (
            f"GC=F: expected {_expected_lots(100)} lots, got {result}"
        )

    def test_gold_broker_symbol(self):
        result = self._lot("XAUUSD")
        assert result == _expected_lots(100), (
            f"XAUUSD: expected {_expected_lots(100)} lots, got {result}"
        )

    # --- Crude oil (1,000 bbl / lot) ---
    def test_crude_yahoo_ticker(self):
        result = self._lot("CL=F")
        assert result == _expected_lots(1000), (
            f"CL=F: expected {_expected_lots(1000)} lots, got {result}"
        )

    def test_crude_broker_symbol_wti(self):
        result = self._lot("WTI")
        assert result == _expected_lots(1000), (
            f"WTI: expected {_expected_lots(1000)} lots, got {result}"
        )

    def test_crude_broker_symbol_usoil(self):
        result = self._lot("USOIL")
        assert result == _expected_lots(1000), (
            f"USOIL: expected {_expected_lots(1000)} lots, got {result}"
        )

    # --- Natural gas (10,000 MMBtu / lot) ---
    def test_natgas_yahoo_ticker(self):
        result = self._lot("NG=F")
        assert result == _expected_lots(10000), (
            f"NG=F: expected {_expected_lots(10000)} lots, got {result}"
        )

    def test_natgas_broker_symbol(self):
        result = self._lot("NGAS")
        assert result == _expected_lots(10000), (
            f"NGAS: expected {_expected_lots(10000)} lots, got {result}"
        )

    # --- Copper (25,000 lbs / lot) ---
    def test_copper_yahoo_ticker(self):
        result = self._lot("HG=F")
        assert result == _expected_lots(25000), (
            f"HG=F: expected {_expected_lots(25000)} lots, got {result}"
        )

    def test_copper_broker_symbol(self):
        result = self._lot("COPPER")
        assert result == _expected_lots(25000), (
            f"COPPER: expected {_expected_lots(25000)} lots, got {result}"
        )

    # --- Platinum / Palladium (100 oz / lot) ---
    def test_platinum(self):
        result = self._lot("XPTUSD")
        assert result == _expected_lots(100), (
            f"XPTUSD: expected {_expected_lots(100)} lots, got {result}"
        )

    def test_palladium(self):
        result = self._lot("XPDUSD")
        assert result == _expected_lots(100), (
            f"XPDUSD: expected {_expected_lots(100)} lots, got {result}"
        )


class TestBackendForexAndNonCommodityUnchanged:
    """Forex, crypto, stock and index sizing must not be affected."""

    def _lot(self, ticker: str, asset_type: str, entry: float, sl: float) -> float:
        return dvapp._calc_auto_lot(
            _BALANCE, entry, sl, asset_type, risk_pct=_RISK_PCT, ticker=ticker
        )

    def test_eurusd_forex(self):
        # 20 pip SL on EURUSD: pip_size=0.0001, pips=20, pip_val=$10/lot => lots=0.5
        result = self._lot("EURUSD", "forex", 1.1000, 1.0980)
        # $100 risk / (20 pips * $10/pip) = 0.5 lots
        assert result == 0.5

    def test_usdjpy_forex(self):
        # 10 pip SL on USDJPY @ 145.00: pip_size=0.01, pips=10
        # pip_val_usd = (0.01/145.00)*100_000 ≈ 6.897/lot
        # lots = $100 / (10 * 6.897) ≈ 1.45
        # Updated from 1.0 (old $10/pip flat) to correct rate-based value (CR-3 fix).
        result = self._lot("USDJPY", "forex", 145.00, 144.90)
        expected = round(100.0 / (10 * (0.01 / 145.00) * 100_000), 2)
        assert result == expected, f"USDJPY: expected {expected} lots, got {result}"

    def test_btc_crypto(self):
        # Crypto: contract_size=1 so lots = risk / sl_dist
        result = self._lot("BTC-USD", "crypto", 50000.0, 49500.0)
        # $100 / ($500 * 1) = 0.2 lots
        assert result == 0.2

    def test_stock(self):
        # Stocks: contract_size=1
        result = self._lot("AAPL", "stock", 180.0, 175.0)
        # $100 / ($5 * 1) = 20.0 lots (shares)
        assert result == 20.0

    def test_index(self):
        # Indices: contract_size=1
        result = self._lot("^GSPC", "index", 5000.0, 4950.0)
        # $100 / ($50 * 1) = 2.0
        assert result == 2.0


# ===========================================================================
# EXPLICIT REGRESSION: silver and copper must NOT return the generic fallback
# ===========================================================================

class TestBackendRegressionNotGenericFallback:
    """These are the exact pre-fix wrong values.  They must never come back."""

    def _lot(self, ticker: str) -> float:
        entry = 30.0
        sl = entry - _SL_DIST
        return dvapp._calc_auto_lot(
            _BALANCE, entry, sl, "commodity", risk_pct=_RISK_PCT, ticker=ticker
        )

    def test_silver_not_200_lots(self):
        """Before fix: SI=F / XAGUSD fell through to lots = risk/sl_dist = 200."""
        result_si = self._lot("SI=F")
        result_xag = self._lot("XAGUSD")
        assert result_si != 200.0,  f"SI=F still produces 200 lots — bug not fixed!"
        assert result_xag != 200.0, f"XAGUSD still produces 200 lots — bug not fixed!"

    def test_copper_not_200_lots(self):
        """Before fix: HG=F / COPPER fell through to lots = risk/sl_dist = 200."""
        result_hg = self._lot("HG=F")
        result_cu = self._lot("COPPER")
        assert result_hg != 200.0,  f"HG=F still produces 200 lots — bug not fixed!"
        assert result_cu != 200.0,  f"COPPER still produces 200 lots — bug not fixed!"

    def test_silver_not_100_contract_fallback(self):
        """After partial-fix attempt: silver must not use the gold/generic 100 size."""
        result = self._lot("SI=F")
        wrong = round(_BALANCE * (_RISK_PCT / 100.0) / (_SL_DIST * 100), 2)
        assert result != wrong, (
            f"SI=F is using contract_size=100 (gold fallback) = {wrong} lots, not 5000-based"
        )

    def test_copper_not_100_contract_fallback(self):
        """Copper must not use the generic 100 contract-size fallback."""
        result = self._lot("COPPER")
        wrong = round(_BALANCE * (_RISK_PCT / 100.0) / (_SL_DIST * 100), 2)
        assert result != wrong, (
            f"COPPER is using contract_size=100 fallback = {wrong} lots, not 25000-based"
        )


# ===========================================================================
# FRONTEND: _szContractSize map (fallback; used when _todayContractSize absent)
# ===========================================================================

class TestFrontendSzContractSizeMap:
    """_szContractSize must return correct sizes for Yahoo tickers and broker symbols."""

    # Silver
    def test_sz_silver_yahoo_si_f(self):
        assert "s === 'SI=F'" in HTML or "s==='SI=F'" in HTML or "'SI=F'" in HTML

    def test_sz_silver_xagusd_already_present(self):
        # XAG regex was already present but SI=F was missing — both must be covered
        assert "/XAG/.test(s)" in HTML

    def test_sz_silver_returns_5000_not_100(self):
        # The SI=F path must return 5000, and the fallback 100 must appear AFTER it
        si_pos = HTML.index("s === 'SI=F'")
        fallback_pos = HTML.index("return 100", si_pos)
        assert fallback_pos > si_pos  # fallback comes after the SI=F check

    # Gold
    def test_sz_gold_yahoo_gc_f(self):
        assert "s === 'GC=F'" in HTML or "s==='GC=F'" in HTML

    # Crude — CL=F was partially covered by /CL/ but now explicitly handled
    def test_sz_crude_cl_f(self):
        assert "s === 'CL=F'" in HTML or "s==='CL=F'" in HTML

    # Copper
    def test_sz_copper_hg_f(self):
        assert "s === 'HG=F'" in HTML or "s==='HG=F'" in HTML

    def test_sz_copper_broker_symbol(self):
        assert "s === 'COPPER'" in HTML or "s==='COPPER'" in HTML

    def test_sz_copper_returns_25000(self):
        assert "return 25000" in HTML

    # Natural gas
    def test_sz_natgas_ng_f(self):
        assert "s === 'NG=F'" in HTML or "s==='NG=F'" in HTML

    def test_sz_natgas_returns_10000(self):
        assert "return 10000" in HTML

    # Platinum / Palladium
    def test_sz_platinum_xpt(self):
        assert "/XPT/.test(s)" in HTML

    def test_sz_palladium_xpd(self):
        assert "/XPD/.test(s)" in HTML


# ===========================================================================
# FRONTEND: _todayContractSize map (primary runtime map)
# ===========================================================================

def _today_map_block() -> str:
    """Extract the _todayContractSize function body."""
    start = HTML.index("function _todayContractSize(o){")
    end = HTML.index("\n}", start) + 2
    return HTML[start:end]


class TestFrontendTodayContractSizeMap:
    """_todayContractSize must return correct sizes for Yahoo tickers and broker symbols."""

    def test_today_silver_si_f(self):
        block = _today_map_block()
        assert "SI=F" in block, "_todayContractSize missing SI=F"

    def test_today_silver_5000(self):
        block = _today_map_block()
        assert "5000" in block, "_todayContractSize missing 5000 for silver"

    def test_today_silver_xagusd(self):
        block = _today_map_block()
        assert "XAG" in block, "_todayContractSize missing XAG pattern"

    def test_today_gold_gc_f(self):
        block = _today_map_block()
        assert "GC=F" in block, "_todayContractSize missing GC=F"

    def test_today_gold_100(self):
        block = _today_map_block()
        assert "100" in block, "_todayContractSize missing 100 for gold"

    def test_today_crude_cl_f(self):
        block = _today_map_block()
        assert "CL=F" in block, "_todayContractSize missing CL=F"

    def test_today_crude_1000(self):
        block = _today_map_block()
        assert "1000" in block

    def test_today_natgas_ng_f(self):
        block = _today_map_block()
        assert "NG=F" in block, "_todayContractSize missing NG=F"

    def test_today_natgas_10000(self):
        block = _today_map_block()
        assert "10000" in block

    def test_today_copper_hg_f(self):
        block = _today_map_block()
        assert "HG=F" in block, "_todayContractSize missing HG=F"

    def test_today_copper_25000(self):
        block = _today_map_block()
        assert "25000" in block, "_todayContractSize missing 25000 for copper"

    def test_today_platinum_xpt(self):
        block = _today_map_block()
        assert "XPT" in block, "_todayContractSize missing XPT for platinum"

    def test_today_palladium_xpd(self):
        block = _today_map_block()
        assert "XPD" in block, "_todayContractSize missing XPD for palladium"


# ===========================================================================
# FRONTEND: Both map copies must cover SI=F and COPPER
# ===========================================================================

class TestFrontendBothMapsCoverNewTickers:
    """Both _szContractSize and _todayContractSize must handle SI=F and COPPER.

    Before this fix, _todayContractSize handled XAG (XAGUSD) but not SI=F,
    causing 50× oversize when the Yahoo Finance ticker form was passed.
    """

    def test_si_f_appears_in_sz_contract_size(self):
        sz_block_start = HTML.index("function _szContractSize(assetType, sym, forexContractSize){")
        sz_block_end = HTML.index("\n}", sz_block_start) + 2
        sz_block = HTML[sz_block_start:sz_block_end]
        assert "SI=F" in sz_block, "_szContractSize still missing SI=F"

    def test_si_f_appears_in_today_contract_size(self):
        today_block = _today_map_block()
        assert "SI=F" in today_block, "_todayContractSize still missing SI=F"

    def test_copper_appears_in_sz_contract_size(self):
        sz_block_start = HTML.index("function _szContractSize(assetType, sym, forexContractSize){")
        sz_block_end = HTML.index("\n}", sz_block_start) + 2
        sz_block = HTML[sz_block_start:sz_block_end]
        assert "COPPER" in sz_block, "_szContractSize still missing COPPER"

    def test_copper_appears_in_today_contract_size(self):
        today_block = _today_map_block()
        assert "COPPER" in today_block, "_todayContractSize still missing COPPER"

    def test_silver_not_100_in_sz_contract_size(self):
        """SI=F must not fall through to the generic 100 return in _szContractSize."""
        sz_block_start = HTML.index("function _szContractSize(assetType, sym, forexContractSize){")
        sz_block_end = HTML.index("\n}", sz_block_start) + 2
        sz_block = HTML[sz_block_start:sz_block_end]
        # The SI=F check (returning 5000) must appear before the fallback 100
        si_pos = sz_block.index("SI=F")
        fallback_pos = sz_block.rindex("return 100")
        assert si_pos < fallback_pos, "SI=F check must come before the fallback return 100"

    def test_copper_not_100_in_today_contract_size(self):
        """COPPER must not fall through to the generic 100 return in _todayContractSize."""
        today_block = _today_map_block()
        copper_pos = today_block.index("COPPER")
        fallback_pos = today_block.rindex("return 100")
        assert copper_pos < fallback_pos, "COPPER check must come before the fallback return 100"


# ===========================================================================
# FAIL-SAFE: unknown commodity tickers must NOT produce a tradeable lot size
# ===========================================================================

class TestBackendUnknownCommodityRefusesToSize:
    """An unmapped commodity ticker must produce 0 lots (non-tradeable), never a guessed size.

    Rationale: if contract_size is silently guessed, a real-money order could be
    placed at wildly wrong position size. Backend returns None for unknown commodities
    and _calc_auto_lot converts that to 0.0 (order refused).
    """

    def _lot(self, ticker: str, asset_type: str = "commodity") -> float:
        entry = 30.0
        sl = entry - _SL_DIST
        return dvapp._calc_auto_lot(
            _BALANCE, entry, sl, asset_type, risk_pct=_RISK_PCT, ticker=ticker
        )

    def test_unknown_commodity_zz_f_returns_zero(self):
        """ZZ=F is not in the contract map — must return 0 (non-tradeable)."""
        result = self._lot("ZZ=F", "commodity")
        assert result == 0.0, (
            f"ZZ=F (unknown commodity) should return 0 lots, got {result}"
        )

    def test_unknown_commodity_asset_type_returns_zero(self):
        """A completely novel ticker with asset_type=commodity must return 0."""
        result = self._lot("NEWMETAL", "commodity")
        assert result == 0.0, (
            f"NEWMETAL (unknown commodity) should return 0 lots, got {result}"
        )

    def test_unknown_futures_ticker_returns_zero(self):
        """A futures-style =F ticker not in the map must return 0."""
        result = self._lot("ZZ=F", "commodity")
        assert result == 0.0, (
            f"Unknown =F ticker should return 0 lots, got {result}"
        )

    def test_contract_size_for_unknown_commodity_returns_none(self):
        """_contract_size_for_ticker must return None for unknown commodity."""
        result = dvapp._contract_size_for_ticker("ZZ=F", "commodity")
        assert result is None, (
            f"_contract_size_for_ticker('ZZ=F', 'commodity') should return None, got {result}"
        )

    def test_contract_size_for_unknown_newmetal_returns_none(self):
        """_contract_size_for_ticker must return None for an unknown broker-symbol commodity."""
        result = dvapp._contract_size_for_ticker("NEWMETAL", "commodity")
        assert result is None, (
            f"_contract_size_for_ticker('NEWMETAL', 'commodity') should return None, got {result}"
        )

    # --- Known instruments must be completely unaffected ---

    def test_known_silver_unaffected(self):
        result = self._lot("SI=F", "commodity")
        assert result == _expected_lots(5000), f"SI=F must still work: got {result}"

    def test_known_gold_unaffected(self):
        result = self._lot("GC=F", "commodity")
        assert result == _expected_lots(100), f"GC=F must still work: got {result}"

    def test_known_crude_unaffected(self):
        result = self._lot("CL=F", "commodity")
        assert result == _expected_lots(1000), f"CL=F must still work: got {result}"

    def test_known_copper_unaffected(self):
        result = self._lot("HG=F", "commodity")
        assert result == _expected_lots(25000), f"HG=F must still work: got {result}"

    def test_known_xagusd_unaffected(self):
        result = self._lot("XAGUSD", "commodity")
        assert result == _expected_lots(5000), f"XAGUSD must still work: got {result}"

    def test_forex_unaffected_by_commodity_guard(self):
        """The commodity guard must not affect forex sizing at all."""
        result = dvapp._calc_auto_lot(
            _BALANCE, 1.1000, 1.0980, "forex", risk_pct=_RISK_PCT, ticker="EURUSD"
        )
        assert result == 0.5, f"EURUSD forex lots should be 0.5, got {result}"

    def test_crypto_unaffected_by_commodity_guard(self):
        """The commodity guard must not affect crypto sizing."""
        result = dvapp._calc_auto_lot(
            _BALANCE, 50000.0, 49500.0, "crypto", risk_pct=_RISK_PCT, ticker="BTC-USD"
        )
        assert result == 0.2, f"BTC-USD crypto lots should be 0.2, got {result}"


class TestFrontendUnknownCommodityDoesNotReturn100:
    """Frontend map functions must NOT silently return 100 for an unknown commodity/=F ticker.

    Both _szContractSize and _todayContractSize must return null (not 100) for
    unknown commodity tickers so UI callers know the size cannot be verified.
    """

    def _sz_block(self) -> str:
        start = HTML.index("function _szContractSize(assetType, sym, forexContractSize){")
        end = HTML.index("\n}", start) + 2
        return HTML[start:end]

    def test_sz_contract_size_fallback_is_null_not_100(self):
        """_szContractSize commodity fallback must be 'return null', not 'return 100'."""
        block = self._sz_block()
        # Last return statement in the commodity block must be null
        # (after platinum/palladium which still legitimately return 100)
        assert "return null" in block, "_szContractSize must have a 'return null' fallback for unknown commodities"

    def test_today_contract_size_fallback_is_null_not_100(self):
        """_todayContractSize commodity fallback must be 'return null', not 'return 100'."""
        block = _today_map_block()
        assert "return null" in block, "_todayContractSize must have a 'return null' fallback for unknown commodities"

    def test_sz_unknown_commodity_fallback_after_all_known(self):
        """'return null' in _szContractSize must come after all known-instrument return statements."""
        block = self._sz_block()
        # Last known instrument in the block is palladium (XPD), which returns 100
        xpd_pos = block.rindex("XPD")
        null_pos = block.rindex("return null")
        assert null_pos > xpd_pos, "return null must come after the last known-instrument check (XPD)"

    def test_today_unknown_commodity_fallback_after_all_known(self):
        """'return null' in _todayContractSize must come after all known-instrument return statements."""
        block = _today_map_block()
        xpd_pos = block.rindex("XPD")
        null_pos = block.rindex("return null")
        assert null_pos > xpd_pos, "return null must come after the last known-instrument check (XPD)"

    def test_sz_block_still_has_return_100_for_platinum(self):
        """Platinum/palladium must still return 100 in _szContractSize."""
        block = self._sz_block()
        assert "return 100" in block, "Platinum/palladium 100 oz return must still be present in _szContractSize"

    def test_today_block_still_has_return_100_for_platinum(self):
        """Platinum/palladium must still return 100 in _todayContractSize."""
        block = _today_map_block()
        assert "return 100" in block, "Platinum/palladium 100 oz return must still be present in _todayContractSize"
