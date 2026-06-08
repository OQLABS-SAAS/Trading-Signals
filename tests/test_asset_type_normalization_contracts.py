"""
CR-2 contracts: asset_type normalization for all MT5 order-send paths.

Rules:
  - The shared helper _normalizeAssetType maps equity->stock, auto->stock,
    and passes crypto/forex/commodity/index through unchanged.
  - _todaySendOrders (Today tab: manual confirm + auto-place + retry) must
    call _normalizeAssetType(o.asset) — never send o.asset raw.
  - The Size/Act send paths (_szConfirmTrade sizing calc and ladder send) must
    also use _normalizeAssetType, not inline the map themselves.
  - No raw `asset_type:o.asset` or `asset_type: o.asset` pattern may appear
    in any /api/mt5/order POST body.
"""
import re
from pathlib import Path

HTML = Path("static/index-v2-prototype.html").read_text()


# ── Helper definition ────────────────────────────────────────────────────────

def test_normalize_asset_type_helper_exists():
    """_normalizeAssetType must be defined as a named function."""
    assert "function _normalizeAssetType(a)" in HTML


def test_normalize_asset_type_maps_equity_to_stock():
    """Helper body must map equity->stock."""
    assert "equity:'stock'" in HTML or "equity: 'stock'" in HTML


def test_normalize_asset_type_maps_auto_to_stock():
    """Helper body must map auto->stock."""
    assert "auto:'stock'" in HTML or "auto: 'stock'" in HTML


def test_normalize_asset_type_passes_through_fallback():
    """Helper body must use `|| a` to pass unknown types through."""
    # Confirm the canonical form: ({equity:'stock', auto:'stock'})[a] || a
    assert "|| a" in HTML


# ── _todaySendOrders: raw asset must not reach the POST ─────────────────────

def test_today_send_orders_uses_normalize_helper():
    """_todaySendOrders must call _normalizeAssetType, not send o.asset raw."""
    assert "_normalizeAssetType(o.asset)" in HTML


def test_today_send_orders_does_not_send_raw_o_asset():
    """No MT5 order POST in _todaySendOrders may use the raw asset_type:o.asset pattern."""
    # This checks the exact buggy pattern is gone from the file entirely.
    raw_patterns = [
        "asset_type:o.asset,",
        "asset_type: o.asset,",
        "asset_type:o.asset}",
        "asset_type: o.asset}",
    ]
    for pat in raw_patterns:
        assert pat not in HTML, f"Raw asset send pattern still present: {pat!r}"


# ── Size/Act paths use helper ────────────────────────────────────────────────

def test_sz_confirm_trade_sizing_calc_uses_helper():
    """_szConfirmTrade sizing calc (rawAsset line) must use _normalizeAssetType."""
    # The sizing calc sets: var assetType = _normalizeAssetType(rawAsset);
    assert "_normalizeAssetType(rawAsset)" in HTML


def test_sz_confirm_trade_order_send_uses_helper():
    """_szConfirmTrade order-send closure (const assetType) must use _normalizeAssetType."""
    # The closure sets: const assetType = _normalizeAssetType(_rawAssetType);
    assert "_normalizeAssetType(_rawAssetType)" in HTML


def test_sz_fallback_leg_uses_helper():
    """Size/Act fallback single-leg path must use _normalizeAssetType for assetType."""
    assert "_normalizeAssetType(sig.asset" in HTML


# ── No stale inline maps on order-send paths ────────────────────────────────

def test_no_inline_equity_stock_maps_in_order_sends():
    """
    All ({equity:'stock', auto:'stock'})[...] inline maps on order-send paths
    must have been replaced by _normalizeAssetType. The only remaining
    occurrence should be inside the helper definition itself.
    """
    # Find all occurrences of the inline map pattern
    pattern = r"\(\{equity:'stock',\s*auto:'stock'\}\)\["
    matches = [(m.start(), HTML[max(0,m.start()-120):m.start()+120])
               for m in re.finditer(pattern, HTML)]

    # Exactly one is allowed: inside the _normalizeAssetType body
    non_helper = [ctx for _, ctx in matches if "function _normalizeAssetType" not in ctx]
    assert len(non_helper) == 0, (
        f"Found {len(non_helper)} inline equity->stock map(s) outside the helper: "
        + str([c[:80] for c in non_helper])
    )


# ── Pass-through values must not be corrupted ───────────────────────────────

def test_normalize_helper_passthrough_types_not_remapped():
    """
    crypto, forex, commodity, index must NOT appear in the mapping table —
    they rely on the `|| a` fallthrough, so they should not be keys in the map.
    """
    # The map object literal inside _normalizeAssetType should only list equity/auto
    # Verify no remapping of pass-through types in the helper body
    helper_block_match = re.search(
        r"function _normalizeAssetType\(a\)\s*\{([^}]+)\}", HTML
    )
    assert helper_block_match, "_normalizeAssetType body not found"
    body = helper_block_match.group(1)
    for unwanted in ("crypto:", "forex:", "commodity:", "index:"):
        assert unwanted not in body, (
            f"Pass-through type {unwanted!r} should not be a key in _normalizeAssetType"
        )


# ── Retry path coverage (structural) ─────────────────────────────────────────

def test_retry_path_covered_by_today_send_orders():
    """
    The retry path passes legSubset to _todaySendOrders, which applies
    _normalizeAssetType in its shared loop. Confirm the retry call pattern exists.
    """
    assert "legSubset.forEach" in HTML
    assert "_todaySendOrders" in HTML
    # The retry wires into _todaySendOrders — confirm at least two call sites
    assert HTML.count("_todaySendOrders(") >= 2
