"""Behavioral tests for the three money-math safety holes closed in the
ship-prep branch.

These tests compute ACTUAL LOT NUMBERS and loss-at-stop figures — they do NOT
grep source strings.  Every assertion drives a real arithmetic path through the
production code (backend) or the extracted sizing functions (frontend/JS).

Holes covered
─────────────
HOLE 1  (HIGH)  _szNativeLotsFromUnits null||1 → up to 5000× oversize on
                unknown commodity.  Now returns 0 (non-tradeable).

HOLE 2  (MED)   _todayLotUnits / _todaySizeTrade with null contract size →
                Infinity lots, tradeable=True.  Now returns tradeable=False
                with a sizeReason.

HOLE 3  (MED)   _forexUsdRate / backend _forex_usd_per_pip_per_lot default
                to rate=1 for exotic quote currencies (ZAR, TRY, NOK …) →
                10–32× sizing error.  Now returns None/null → _calc_auto_lot
                returns 0 (non-tradeable).

Regression suite
────────────────
Known instruments (silver, gold, crude, copper, EURUSD, GBPJPY, BTC, AAPL)
must produce loss-at-stop ≈ risk budget (within 40% tolerance to allow for
the cost model rounding).
"""

from __future__ import annotations

import os
import sys
import subprocess
import json
from pathlib import Path

# ---------------------------------------------------------------------------
# Backend imports
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-prod")
os.environ.setdefault("REDIS_URL", "")

import app as dvapp  # noqa: E402

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------
_BALANCE   = 10_000.0
_RISK_PCT  = 1.0           # 1 % ⇒ $100
_RISK_USD  = _BALANCE * (_RISK_PCT / 100.0)   # = 100.0


def _lot(ticker: str, asset_type: str, entry: float, sl: float) -> float:
    return dvapp._calc_auto_lot(
        _BALANCE, entry, sl, asset_type, risk_pct=_RISK_PCT, ticker=ticker
    )


def _loss_at_stop_forex(lots: float, ticker: str, entry: float, sl: float) -> float:
    """Reconstruct the USD loss at stop for a forex position."""
    sym      = str(ticker).upper().replace("=X","").replace("/","").replace("-","")
    pip_size = 0.01 if "JPY" in sym else 0.0001
    pips     = abs(entry - sl) / pip_size
    pvl      = dvapp._forex_usd_per_pip_per_lot(ticker, pip_size, entry)
    if pvl is None:
        return float("nan")
    return lots * pips * pvl


def _loss_at_stop_nonforex(lots: float, entry: float, sl: float,
                            contract_size: float) -> float:
    """loss = lots × contract_size × |entry − sl|"""
    return lots * contract_size * abs(entry - sl)


# ===========================================================================
# HOLE 1 — backend: unknown commodity _calc_auto_lot must return 0
# ===========================================================================

class TestBackendUnknownCommodityReturnsZero:
    """_calc_auto_lot must refuse (return 0) for any commodity whose contract
    size is not in the verified map.  Before the fix it silently divided by
    sl_dist only, producing lot counts up to 5,000× too large."""

    def test_unknown_commodity_zz_f(self):
        result = _lot("ZZ=F", "commodity", 30.0, 29.5)
        assert result == 0.0, (
            f"ZZ=F (unknown commodity): expected 0 lots, got {result}. "
            "Pre-fix value would have been ~200."
        )

    def test_unknown_commodity_newmetal(self):
        result = _lot("NEWMETAL", "commodity", 30.0, 29.5)
        assert result == 0.0, (
            f"NEWMETAL (unknown commodity): expected 0 lots, got {result}"
        )

    def test_unknown_commodity_not_200(self):
        """Prove the old wrong value is no longer returned.

        Before fix: lots = risk_amt / sl_dist = 100 / 0.5 = 200 — no contract
        size division at all.  That is the 5,000× oversize for silver
        (contract_size=5,000): 200 lots × 5,000 oz = 1,000,000 oz position.
        """
        result = _lot("ZZ=F", "commodity", 30.0, 29.5)
        wrong_pre_fix = round(_RISK_USD / 0.5, 2)   # = 200.0
        assert result != wrong_pre_fix, (
            f"ZZ=F still produces {wrong_pre_fix} lots — pre-fix oversize NOT fixed!"
        )

    def test_contract_size_for_unknown_returns_none(self):
        assert dvapp._contract_size_for_ticker("ZZ=F", "commodity") is None
        assert dvapp._contract_size_for_ticker("NEWMETAL", "commodity") is None

    # --- known instruments must be completely unaffected ---

    def test_silver_unaffected(self):
        result = _lot("SI=F", "commodity", 30.0, 29.5)
        expected = round(_RISK_USD / (0.5 * 5000), 2)
        assert result == expected, f"SI=F: expected {expected} lots, got {result}"

    def test_gold_unaffected(self):
        result = _lot("GC=F", "commodity", 2000.0, 1990.0)
        expected = round(_RISK_USD / (10.0 * 100), 2)
        assert result == expected, f"GC=F: expected {expected} lots, got {result}"

    def test_crude_unaffected(self):
        result = _lot("CL=F", "commodity", 80.0, 79.0)
        expected = round(_RISK_USD / (1.0 * 1000), 2)
        assert result == expected, f"CL=F: expected {expected} lots, got {result}"

    def test_copper_unaffected(self):
        result = _lot("HG=F", "commodity", 4.0, 3.9)
        expected = round(_RISK_USD / (0.1 * 25000), 2)
        assert result == expected, f"HG=F: expected {expected} lots, got {result}"

    def test_xagusd_broker_symbol_unaffected(self):
        result = _lot("XAGUSD", "commodity", 30.0, 29.5)
        expected = round(_RISK_USD / (0.5 * 5000), 2)
        assert result == expected, f"XAGUSD: expected {expected} lots, got {result}"


# ===========================================================================
# HOLE 3 — backend: exotic forex quote currency must refuse, not use rate=1
# ===========================================================================

class TestBackendExoticForexQuoteRefuses:
    """_forex_usd_per_pip_per_lot must return None for quote currencies outside
    the 11-currency fallback table (ZAR, TRY, NOK, SEK, DKK, HKD, SGD, PLN …)
    so that _calc_auto_lot returns 0 instead of placing a wildly wrong order.

    Before the fix: _FOREX_QUOTE_TO_USD.get(quote, 1.0) → rate=1.0 for ZAR
    (~18×) or TRY (~32×), silently producing a lot count 18–32× off.
    """

    def test_eurzar_pip_val_is_none(self):
        """EURZAR quote=ZAR not in table → pip_val must be None, not 1000."""
        pvl = dvapp._forex_usd_per_pip_per_lot("EURZAR", 0.0001, 18.0)
        assert pvl is None, (
            f"EURZAR pip_val should be None (unknown ZAR rate), got {pvl}. "
            "Pre-fix value was 10.0 (rate=1) → ~18× off."
        )

    def test_eurtry_pip_val_is_none(self):
        pvl = dvapp._forex_usd_per_pip_per_lot("EURTRY", 0.0001, 32.0)
        assert pvl is None, (
            f"EURTRY pip_val should be None (unknown TRY rate), got {pvl}"
        )

    def test_eurnok_pip_val_is_none(self):
        pvl = dvapp._forex_usd_per_pip_per_lot("EURNOK", 0.0001, 11.5)
        assert pvl is None, (
            f"EURNOK pip_val should be None (unknown NOK rate), got {pvl}"
        )

    def test_eursek_pip_val_is_none(self):
        pvl = dvapp._forex_usd_per_pip_per_lot("EURSEK", 0.0001, 11.5)
        assert pvl is None, f"EURSEK pip_val should be None, got {pvl}"

    def test_calc_auto_lot_eurzar_returns_zero(self):
        """_calc_auto_lot must return 0.0 for an exotic-quote pair, not size it wrong."""
        result = _lot("EURZAR", "forex", 18.0, 17.95)
        assert result == 0.0, (
            f"EURZAR lot should be 0 (unknown ZAR rate → refuse), got {result}. "
            "Pre-fix: would have returned a wrong lot using rate=1."
        )

    def test_calc_auto_lot_eurtry_returns_zero(self):
        result = _lot("EURTRY", "forex", 32.0, 31.90)
        assert result == 0.0, (
            f"EURTRY lot should be 0 (unknown TRY rate → refuse), got {result}"
        )

    def test_eurzar_not_returns_wrong_size(self):
        """Demonstrate the pre-fix value would have been ~200 lots (rate=1).

        With pip_val = 0.0001 × 100_000 × 1.0 = 10 (wrong — ZAR is ~18×),
        and 5-pip SL: lots = 100 / (5 × 10) = 2.0 — but with correct ZAR rate
        (~18 ZAR/USD) pip_val ≈ 0.56 and lots ≈ 35.7.  The fix refuses both.
        """
        result = _lot("EURZAR", "forex", 18.0, 17.95)
        pre_fix_wrong = round(_RISK_USD / (5 * 10.0), 2)   # = 2.0 (rate=1)
        assert result != pre_fix_wrong, (
            f"EURZAR still producing the pre-fix wrong value {pre_fix_wrong}"
        )

    # --- known pairs must be completely unaffected ---

    def test_eurusd_still_works(self):
        result = _lot("EURUSD", "forex", 1.1000, 1.0980)
        expected = 0.5  # $100 / (20 × $10)
        assert result == expected, f"EURUSD must still be 0.5 lots, got {result}"

    def test_eurusd_loss_at_stop(self):
        lots  = _lot("EURUSD", "forex", 1.1000, 1.0980)
        loss  = _loss_at_stop_forex(lots, "EURUSD", 1.1000, 1.0980)
        assert abs(loss - _RISK_USD) / _RISK_USD <= 0.05, (
            f"EURUSD loss_at_stop={loss:.2f}, expected ~{_RISK_USD:.2f}"
        )

    def test_gbpjpy_still_works(self):
        """GBPJPY is a cross pair with a KNOWN counter (JPY) — must still size."""
        lots = _lot("GBPJPY=X", "forex", 190.0, 189.70)
        assert lots > 0, f"GBPJPY must still produce lots > 0, got {lots}"

    def test_gbpjpy_loss_at_stop(self):
        lots = _lot("GBPJPY=X", "forex", 190.0, 189.70)
        loss = _loss_at_stop_forex(lots, "GBPJPY=X", 190.0, 189.70)
        assert abs(loss - _RISK_USD) / _RISK_USD <= 0.05, (
            f"GBPJPY loss_at_stop={loss:.2f}, expected ~{_RISK_USD:.2f}"
        )

    def test_usdjpy_usd_base_still_works(self):
        """USD-base pairs use live price, not the table — must be unaffected."""
        lots = _lot("USDJPY=X", "forex", 145.0, 144.90)
        assert lots > 0, f"USDJPY USD-base pair must still produce lots, got {lots}"

    def test_usdjpy_loss_at_stop(self):
        entry, sl = 145.0, 144.90
        lots  = _lot("USDJPY=X", "forex", entry, sl)
        loss  = _loss_at_stop_forex(lots, "USDJPY=X", entry, sl)
        assert abs(loss - _RISK_USD) / _RISK_USD <= 0.05, (
            f"USDJPY loss_at_stop={loss:.2f}, expected ~{_RISK_USD:.2f}"
        )


# ===========================================================================
# REGRESSION — backend: silver, gold, crude, copper loss-at-stop ~ risk
# ===========================================================================

class TestBackendRegressionKnownInstrumentsLossAtStop:
    """For every known instrument, loss-at-stop from the returned lot count must
    approximate the risk budget within ±40% (the cost model adds spread/fees/
    slip on top of the raw SL distance, so perfect equality is not expected)."""

    _TOL = 0.40   # 40% tolerance

    def _check(self, ticker, asset_type, entry, sl, cs):
        lots = _lot(ticker, asset_type, entry, sl)
        assert lots > 0, f"{ticker}: got 0 lots"
        loss = _loss_at_stop_nonforex(lots, entry, sl, cs)
        dev  = abs(loss - _RISK_USD) / _RISK_USD
        assert dev <= self._TOL, (
            f"{ticker}: loss_at_stop={loss:.2f} deviates {dev*100:.1f}% "
            f"from risk budget ${_RISK_USD:.2f} (tolerance {self._TOL*100:.0f}%)"
        )

    def test_silver_si_f(self):
        self._check("SI=F",   "commodity", 30.0,   29.5,   5000)

    def test_silver_xagusd(self):
        self._check("XAGUSD", "commodity", 30.0,   29.5,   5000)

    def test_gold_gc_f(self):
        self._check("GC=F",   "commodity", 2000.0, 1990.0, 100)

    def test_gold_xauusd(self):
        self._check("XAUUSD", "commodity", 2000.0, 1990.0, 100)

    def test_crude_cl_f(self):
        self._check("CL=F",   "commodity", 80.0,   79.0,   1000)

    def test_crude_wti(self):
        self._check("WTI",    "commodity", 80.0,   79.0,   1000)

    def test_copper_hg_f(self):
        self._check("HG=F",   "commodity", 4.0,    3.9,    25000)

    def test_copper_symbol(self):
        self._check("COPPER", "commodity", 4.0,    3.9,    25000)

    def test_btc_crypto(self):
        # crypto: contract_size = 1
        self._check("BTC-USD","crypto",    50000.0, 49500.0, 1)

    def test_aapl_stock(self):
        # stock: contract_size = 1
        self._check("AAPL",   "stock",    180.0,  175.0,   1)

    def test_eurusd_forex(self):
        lots = _lot("EURUSD", "forex", 1.1000, 1.0980)
        loss = _loss_at_stop_forex(lots, "EURUSD", 1.1000, 1.0980)
        assert abs(loss - _RISK_USD) / _RISK_USD <= 0.05, (
            f"EURUSD: loss_at_stop={loss:.2f}, risk={_RISK_USD:.2f}"
        )

    def test_gbpjpy_forex(self):
        lots = _lot("GBPJPY=X", "forex", 190.0, 189.70)
        loss = _loss_at_stop_forex(lots, "GBPJPY=X", 190.0, 189.70)
        assert abs(loss - _RISK_USD) / _RISK_USD <= 0.05, (
            f"GBPJPY: loss_at_stop={loss:.2f}, risk={_RISK_USD:.2f}"
        )


# ===========================================================================
# HOLE 1+2 — frontend JS: drive extracted functions via node subprocess
# ===========================================================================

# Path to the pre-built harness (built during the test session by the CI script,
# or by running:  python3 tests/_build_sizing_harness.py)
_HARNESS = Path(__file__).parent / "_sizing_harness.js"
_RUNNER  = Path(__file__).parent / "_sizing_runner.js"


def _build_harness() -> bool:
    """Rebuild /tmp/_sizing_harness.js from the live HTML source.  Returns True
    on success.  Skipped if node is not available."""
    html = Path("static/index-v2-prototype.html")
    if not html.exists():
        return False
    lines = html.read_text().splitlines(keepends=True)
    prefix = (
        "var window = {\n"
        "  _forexUsdRates: {\n"
        "    USDCAD:1.35, USDCHF:0.90, USDJPY:150, USDINR:83,\n"
        "    USDCNH:7.2,  USDMXN:17,   EURUSD:1.08, GBPUSD:1.27,\n"
        "    AUDUSD:0.67, NZDUSD:0.61\n"
        "  },\n"
        "  _todayLeverage: 100\n"
        "};\n"
        "var _todayLeverageReal = false;\n"
        "function _szBrokerLeverageValue(){ return 100; }\n"
    )
    # Extract by function NAME (brace-balanced), not hardcoded line numbers, so an
    # unrelated edit elsewhere in the HTML can't shift the slice and break the harness.
    src = "".join(lines)
    def _through_fn(start_marker, end_fn):
        si = src.find(start_marker)
        fi = src.find("function " + end_fn, si if si >= 0 else 0)
        if si < 0 or fi < 0:
            raise RuntimeError("harness: marker not found for " + end_fn)
        depth = 0; started = False; j = fi
        while j < len(src):
            ch = src[j]
            if ch == "{":
                depth += 1; started = True
            elif ch == "}":
                depth -= 1
                if started and depth == 0:
                    return src[si:j + 1]
            j += 1
        raise RuntimeError("harness: unbalanced braces for " + end_fn)
    # chunk1: _szNormalizeAssetType … through the close of _todaySizeTrade
    chunk1 = _through_fn("function _szNormalizeAssetType(", "_todaySizeTrade")
    # chunk2: the _forexUsdRate function (rate cache already defined in prefix)
    chunk2 = _through_fn("function _forexUsdRate(", "_forexUsdRate")
    harness = prefix + chunk1 + "\n" + chunk2
    _HARNESS.write_text(harness)
    return True


def _node_available() -> bool:
    try:
        subprocess.run(["node", "--version"], capture_output=True, timeout=5)
        return True
    except Exception:
        return False


def _run_js(script: str) -> dict:
    """Run a node.js snippet that returns JSON on stdout.  Raises on failure."""
    src = f"var fs=require('fs'); eval(fs.readFileSync({json.dumps(str(_HARNESS))},'utf8'));\n{script}"
    r = subprocess.run(
        ["node", "-e", src],
        capture_output=True, text=True, timeout=15,
        cwd=Path(__file__).parent.parent,
    )
    if r.returncode != 0:
        raise RuntimeError(f"node error:\n{r.stderr[:800]}")
    return json.loads(r.stdout.strip())


import pytest


@pytest.fixture(scope="module", autouse=True)
def build_js_harness():
    """Build the JS harness once per test module session."""
    if _node_available():
        _build_harness()


@pytest.mark.skipif(not _node_available(), reason="node not available")
class TestFrontendJSSizingFunctions:
    """Drive the real JS sizing functions from the HTML via node subprocess.

    Each test calls _run_js() which evals the extracted production JS and
    returns computed numbers as JSON.  No string-matching; every assertion
    is on actual computed lot counts, tradeable flags, and loss figures.
    """

    # ── _forexUsdRate ──────────────────────────────────────────────────────

    def test_forex_rate_known_usd(self):
        r = _run_js("process.stdout.write(JSON.stringify(_forexUsdRate('USD')));")
        assert r == 1

    def test_forex_rate_known_jpy(self):
        r = _run_js("process.stdout.write(JSON.stringify(_forexUsdRate('JPY')));")
        assert isinstance(r, float) and 0.006 < r < 0.008

    def test_forex_rate_known_gbp(self):
        r = _run_js("process.stdout.write(JSON.stringify(_forexUsdRate('GBP')));")
        assert isinstance(r, float) and 1.20 < r < 1.35

    def test_forex_rate_exotic_zar_is_null(self):
        r = _run_js("process.stdout.write(JSON.stringify(_forexUsdRate('ZAR')));")
        assert r is None, f"ZAR should be null, got {r}"

    def test_forex_rate_exotic_try_is_null(self):
        r = _run_js("process.stdout.write(JSON.stringify(_forexUsdRate('TRY')));")
        assert r is None, f"TRY should be null, got {r}"

    def test_forex_rate_exotic_nok_is_null(self):
        r = _run_js("process.stdout.write(JSON.stringify(_forexUsdRate('NOK')));")
        assert r is None, f"NOK should be null, got {r}"

    def test_forex_rate_exotic_sek_is_null(self):
        r = _run_js("process.stdout.write(JSON.stringify(_forexUsdRate('SEK')));")
        assert r is None, f"SEK should be null, got {r}"

    # ── _szNativeLotsFromUnits ─────────────────────────────────────────────

    def test_unknown_commodity_returns_zero_lots(self):
        """BEFORE fix: 200 / (null||1) = 200 lots.  AFTER: 0 lots (blocked)."""
        script = """
var posSize = 200;   // moneyAtRisk(100) / slDist(0.5) = 200 units
var lots = _szNativeLotsFromUnits(posSize, 'commodity', 'UNKNOWNMETAL');
process.stdout.write(JSON.stringify({lots: lots}));
"""
        r = _run_js(script)
        assert r["lots"] == 0, (
            f"Unknown commodity lots should be 0, got {r['lots']}. "
            "Pre-fix was 200 (5000x oversize vs silver contract_size=5000)."
        )

    def test_unknown_commodity_before_was_200(self):
        """Demonstrate the exact pre-fix arithmetic (null||1 = 1) produces 200."""
        script = """
var broken = 200 / (null || 1);   // old code
process.stdout.write(JSON.stringify({broken: broken}));
"""
        r = _run_js(script)
        assert r["broken"] == 200, "Pre-fix simulation should give 200"

    def test_silver_xagusd_correct_lots(self):
        script = """
var lots = _szNativeLotsFromUnits(5000, 'commodity', 'XAGUSD');
process.stdout.write(JSON.stringify({lots: lots}));
"""
        r = _run_js(script)
        assert r["lots"] == 1.0, f"XAGUSD 5000u should be 1 lot, got {r['lots']}"

    def test_gold_xauusd_correct_lots(self):
        script = """
var lots = _szNativeLotsFromUnits(100, 'commodity', 'XAUUSD');
process.stdout.write(JSON.stringify({lots: lots}));
"""
        r = _run_js(script)
        assert r["lots"] == 1.0, f"XAUUSD 100u should be 1 lot, got {r['lots']}"

    def test_crude_wti_correct_lots(self):
        script = """
var lots = _szNativeLotsFromUnits(1000, 'commodity', 'WTI');
process.stdout.write(JSON.stringify({lots: lots}));
"""
        r = _run_js(script)
        assert r["lots"] == 1.0

    def test_copper_correct_lots(self):
        script = """
var lots = _szNativeLotsFromUnits(25000, 'commodity', 'COPPER');
process.stdout.write(JSON.stringify({lots: lots}));
"""
        r = _run_js(script)
        assert r["lots"] == 1.0

    def test_crypto_passthrough(self):
        script = """
var lots = _szNativeLotsFromUnits(0.5, 'crypto', 'BTCUSD');
process.stdout.write(JSON.stringify({lots: lots}));
"""
        r = _run_js(script)
        assert r["lots"] == 0.5

    def test_forex_100k_units_one_lot(self):
        script = """
var lots = _szNativeLotsFromUnits(100000, 'forex', 'EURUSD');
process.stdout.write(JSON.stringify({lots: lots}));
"""
        r = _run_js(script)
        assert r["lots"] == 1.0

    # ── _todayLotUnits ─────────────────────────────────────────────────────

    def test_today_lot_units_unknown_commodity_nullcs(self):
        script = """
var lu = _todayLotUnits({asset:'commodity', sym:'UNKNOWNMETAL'});
process.stdout.write(JSON.stringify({nullCs: lu.nullCs, cs: lu.cs,
                                     stepUnits: lu.stepUnits, minUnits: lu.minUnits}));
"""
        r = _run_js(script)
        assert r["nullCs"] is True,  f"nullCs should be True, got {r['nullCs']}"
        assert r["cs"] is None,      f"cs should be null, got {r['cs']}"
        assert r["stepUnits"] == 0,  f"stepUnits should be 0, got {r['stepUnits']}"
        assert r["minUnits"] == 0,   f"minUnits should be 0, got {r['minUnits']}"

    def test_today_lot_units_silver_has_correct_cs(self):
        script = """
var lu = _todayLotUnits({asset:'commodity', sym:'XAGUSD'});
process.stdout.write(JSON.stringify({cs: lu.cs, nullCs: lu.nullCs || false,
                                     stepUnits: lu.stepUnits}));
"""
        r = _run_js(script)
        assert r["cs"] == 5000, f"silver cs should be 5000, got {r['cs']}"
        assert r["nullCs"] is False
        assert abs(r["stepUnits"] - 50.0) < 0.01   # 0.01 lot × 5000 = 50 units

    # ── _todaySizeTrade ────────────────────────────────────────────────────

    def test_today_size_trade_unknown_commodity_not_tradeable(self):
        """Hole 2: unknown commodity must produce lots=0, tradeable=false."""
        script = """
var s = _todaySizeTrade(
    {asset:'commodity', sym:'UNKNOWNMETAL', entry:30, sl:29.5, tp:31},
    10000, 1);
process.stdout.write(JSON.stringify({
    lots: s.lots, units: s.units, tradeable: s.tradeable,
    netLoss: s.netLoss, sizeReason: s.sizeReason || null
}));
"""
        r = _run_js(script)
        assert r["lots"] == 0,        f"unknown commodity lots must be 0, got {r['lots']}"
        assert r["units"] == 0,       f"unknown commodity units must be 0, got {r['units']}"
        assert r["tradeable"] is False, f"unknown commodity must not be tradeable, got {r['tradeable']}"
        assert r["netLoss"] == 0,     f"unknown commodity netLoss must be 0, got {r['netLoss']}"
        assert r["sizeReason"],       "unknown commodity must have a sizeReason message"

    def test_today_size_trade_silver_tradeable_loss_at_stop(self):
        """Known silver: tradeable=true, loss-at-stop within 40% of $100."""
        script = """
var s = _todaySizeTrade(
    {asset:'commodity', sym:'XAGUSD', entry:30, sl:29.5, tp:31},
    10000, 1);
process.stdout.write(JSON.stringify({
    lots: s.lots, tradeable: s.tradeable, netLoss: s.netLoss
}));
"""
        r = _run_js(script)
        assert r["tradeable"] is True, f"XAGUSD should be tradeable, got {r['tradeable']}"
        assert 0.01 <= r["lots"] <= 0.10, f"silver lots out of range: {r['lots']}"
        assert 60 <= r["netLoss"] <= 120, (
            f"silver netLoss={r['netLoss']:.2f} not in [$60,$120]"
        )

    def test_today_size_trade_gold_tradeable(self):
        script = """
var s = _todaySizeTrade(
    {asset:'commodity', sym:'XAUUSD', entry:2000, sl:1990, tp:2020},
    10000, 1);
process.stdout.write(JSON.stringify({tradeable: s.tradeable, netLoss: s.netLoss}));
"""
        r = _run_js(script)
        assert r["tradeable"] is True
        assert 60 <= r["netLoss"] <= 140, f"gold netLoss={r['netLoss']:.2f}"

    def test_today_size_trade_crude_tradeable(self):
        script = """
var s = _todaySizeTrade(
    {asset:'commodity', sym:'WTI', entry:80, sl:79, tp:82},
    10000, 1);
process.stdout.write(JSON.stringify({tradeable: s.tradeable, netLoss: s.netLoss}));
"""
        r = _run_js(script)
        assert r["tradeable"] is True
        assert 60 <= r["netLoss"] <= 140

    def test_today_size_trade_copper_tradeable(self):
        script = """
var s = _todaySizeTrade(
    {asset:'commodity', sym:'COPPER', entry:4, sl:3.9, tp:4.2},
    10000, 1);
process.stdout.write(JSON.stringify({tradeable: s.tradeable, netLoss: s.netLoss}));
"""
        r = _run_js(script)
        assert r["tradeable"] is True
        assert 60 <= r["netLoss"] <= 140

    def test_today_size_trade_eurusd_tradeable(self):
        script = """
var s = _todaySizeTrade(
    {asset:'forex', sym:'EURUSD', entry:1.1000, sl:1.0980, tp:1.1040},
    10000, 1);
process.stdout.write(JSON.stringify({tradeable: s.tradeable, netLoss: s.netLoss}));
"""
        r = _run_js(script)
        assert r["tradeable"] is True
        assert 70 <= r["netLoss"] <= 130, f"EURUSD netLoss={r['netLoss']}"

    def test_today_size_trade_gbpjpy_tradeable(self):
        script = """
var s = _todaySizeTrade(
    {asset:'forex', sym:'GBPJPY', entry:190, sl:189.70, tp:190.9},
    10000, 1);
process.stdout.write(JSON.stringify({tradeable: s.tradeable, netLoss: s.netLoss}));
"""
        r = _run_js(script)
        assert r["tradeable"] is True
        assert 40 <= r["netLoss"] <= 160, f"GBPJPY netLoss={r['netLoss']}"

    def test_today_size_trade_btc_tradeable(self):
        script = """
var s = _todaySizeTrade(
    {asset:'crypto', sym:'BTC-USD', entry:50000, sl:49500, tp:51000},
    10000, 1);
process.stdout.write(JSON.stringify({tradeable: s.tradeable, netLoss: s.netLoss}));
"""
        r = _run_js(script)
        assert r["tradeable"] is True
        assert 70 <= r["netLoss"] <= 130

    def test_today_size_trade_aapl_tradeable(self):
        script = """
var s = _todaySizeTrade(
    {asset:'stock', sym:'AAPL', entry:180, sl:175, tp:190},
    10000, 1);
process.stdout.write(JSON.stringify({tradeable: s.tradeable, netLoss: s.netLoss}));
"""
        r = _run_js(script)
        assert r["tradeable"] is True
        assert 70 <= r["netLoss"] <= 130
