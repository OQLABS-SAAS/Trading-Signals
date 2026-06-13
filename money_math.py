"""DotVerse money-math: position sizing, contract sizes, and FX pip values.

First extracted module of the app.py monolith split. These functions are the
recurring contract-size / currency-conversion / pip-value bug family — keeping
them in ONE tested place (driven by tests/, imported by app.py and any future
module) is what stops that family of bugs from reappearing.

Pure functions only: no Flask, no DB, no global app state. Safe to import
anywhere. Behaviour is identical to the previous in-app.py definitions.
"""

# USD value of 1 unit of each forex quote currency (fallback table).
# Intentionally does NOT cover exotic currencies (ZAR, TRY, NOK, SEK, DKK,
# HKD, SGD …) — callers must refuse to size those rather than guess a rate.
_FOREX_QUOTE_TO_USD: dict = {
    "USD": 1.0,
    "JPY": 1 / 150.0,
    "GBP": 1.27,
    "EUR": 1.08,
    "AUD": 0.67,
    "NZD": 0.61,
    "CAD": 1 / 1.35,
    "CHF": 1 / 0.90,
    "INR": 1 / 83.0,
    "CNH": 1 / 7.2,
    "MXN": 1 / 17.0,
}


def _forex_usd_per_pip_per_lot(ticker: str, pip_size: float, entry: float) -> float:
    """Return the USD value of 1 pip for 1 standard lot (100,000 units).

    Formula: pip_value_usd = pip_size * 100_000 * usd_per_quote_ccy

    For USD-base pairs (USDJPY, USDCAD, USDCHF) the pip value depends on the
    current price (pip_size / entry * 100_000), which is equivalent to using
    usd_per_quote = 1/entry and multiplying by pip_size * 100_000 — both
    expressions are identical.  The price-based form is preferred here because
    it uses the live entry rather than a stale fallback rate.

    For USD-quote pairs (EURUSD, GBPUSD, AUDUSD, NZDUSD) pip_value = 10 USD
    exactly (pip_size=0.0001, 0.0001*100000=10, usd_per_USD=1).

    For crosses (EURJPY, GBPJPY, EURGBP …) pip_value is in the counter
    currency, converted via the fallback table _FOREX_QUOTE_TO_USD.
    """
    sym = str(ticker).upper().replace("=X", "").replace("/", "").replace("-", "")
    contract_size = 100_000
    if len(sym) < 6:
        # Malformed ticker — fall back to the old $10/pip assumption so we
        # never return 0 and block a trade for a minor symbol quirk.
        return pip_size * contract_size  # ≈ $10 for 4dp pairs

    quote_ccy = sym[3:6]  # e.g. 'GBPJPY' → 'JPY', 'EURUSD' → 'USD'
    base_ccy  = sym[0:3]  # e.g. 'GBPJPY' → 'GBP', 'USDJPY' → 'USD'

    if base_ccy == "USD" and entry and entry > 0:
        # USD-base pair: pip value in USD = pip_size / price * 100_000
        # This is exact — uses live entry, not a stale table value.
        return (pip_size / entry) * contract_size

    # USD-quote or cross pair: look up usd_per_quote from the fallback table.
    # Do NOT default to 1.0 for unknown quote currencies — that silently produces
    # sizing errors of 10–32× for exotic pairs (ZAR, TRY, NOK, SEK, DKK, HKD …).
    # Return None so _calc_auto_lot can refuse to size rather than place a wrong order.
    if quote_ccy not in _FOREX_QUOTE_TO_USD:
        return None  # caller must treat as non-tradeable
    usd_per_quote = _FOREX_QUOTE_TO_USD[quote_ccy]
    return pip_size * contract_size * usd_per_quote


# Contract sizes (instrument units per 1.0 lot) for non-forex assets.
# Indices, stocks, crypto: 1 (units == shares / coins / index points).
# Keys are matched case-insensitively; both Yahoo Finance ticker forms
# (GC=F, SI=F …) and broker symbol forms (XAUUSD, XAGUSD, WTI …) are listed.
_COMMODITY_CONTRACT_SIZES = {
    # Gold
    "GC=F":   100,   "XAUUSD": 100,   "GOLD": 100,
    # Silver — the critical one: 5,000 oz/lot on CME standard contract
    "SI=F":   5000,  "XAGUSD": 5000,  "SILVER": 5000,
    # Crude oil
    "CL=F":   1000,  "WTI":    1000,  "USOIL": 1000,  "UKOIL": 1000,
    "BRENT":  1000,
    # Natural gas
    "NG=F":   10000, "NGAS":   10000, "NATGAS": 10000,
    # Copper
    "HG=F":   25000, "COPPER": 25000,
    # Platinum / palladium (standard MT5 broker contract = 100 oz/lot;
    # NOTE: CME full contract is 50 oz but MT5 spot CFDs typically use 100 oz —
    # verify with your specific broker before trading these.)
    "XPTUSD": 100,   "PLATINUM": 100,
    "XPDUSD": 100,   "PALLADIUM": 100,
}


def _contract_size_for_ticker(ticker: str, asset_type: str):
    """Return the number of instrument units per 1.0 lot for the given ticker.

    Returns 1 for indices, stocks and crypto (lot == 1 unit).
    Returns the appropriate commodity contract size for known commodity tickers.
    Returns None for unknown commodity/futures tickers so callers can refuse to size
    rather than silently using a guessed contract size on a real-money order.
    """
    t = str(ticker).upper().strip()
    if asset_type == "commodity" or t.endswith("=F"):
        size = _COMMODITY_CONTRACT_SIZES.get(t)
        if size is not None:
            return float(size)
        # Fuzzy fallback for broker aliases not in the map
        if "XAG" in t or t.startswith("SI"):
            return 5000.0
        if "XAU" in t or t.startswith("GC"):
            return 100.0
        if any(x in t for x in ("WTI", "USOIL", "BRENT", "UKOIL")) or t.startswith("CL"):
            return 1000.0
        if "NGAS" in t or "NATGAS" in t or t.startswith("NG"):
            return 10000.0
        if "COPPER" in t or t.startswith("HG"):
            return 25000.0
        if "XPT" in t or "PLATINUM" in t:
            return 100.0
        if "XPD" in t or "PALLADIUM" in t:
            return 100.0
        # Unknown commodity/futures ticker — refuse to guess a contract size.
        # Returning None causes _calc_auto_lot to return 0 (non-tradeable).
        print(f"[sizing] unknown commodity contract size for {ticker!r}; refusing to size")
        return None
    # indices, stocks, crypto: 1 unit per lot
    return 1.0


def _calc_auto_lot(account_balance, entry, sl, asset_type, risk_pct=1.0, ticker=""):
    """Calculate appropriate lot size for an auto-scan signal."""
    if not entry or not sl or entry == sl or account_balance <= 0:
        return 0.0
    risk_amt = account_balance * (risk_pct / 100.0)
    sl_dist  = abs(entry - sl)
    if sl_dist == 0:
        return 0.0
    if asset_type == "forex":
        # pip_size: JPY pairs use 2-decimal pricing (0.01), all others 0.0001.
        # pip_val_usd: USD value of 1 pip per standard lot — depends on the
        # quote currency of the pair, NOT a flat $10/pip assumption.
        #   • USD-quote (EURUSD, GBPUSD…): $10/pip — same as before.
        #   • USD-base  (USDJPY, USDCAD…): pip_size/entry * 100k — exact.
        #   • Cross     (EURJPY, EURGBP…): pip_size * 100k * usd_per_quote.
        pip_size     = 0.01 if "JPY" in str(ticker).upper() else 0.0001
        pips         = sl_dist / pip_size
        pip_val_usd  = _forex_usd_per_pip_per_lot(ticker, pip_size, entry)
        if pip_val_usd is None:
            # Unknown quote currency — refuse to size rather than use a wrong rate.
            # _forex_usd_per_pip_per_lot returns None for exotic pairs outside the
            # 11-currency fallback table (ZAR, TRY, NOK, SEK, DKK, HKD, SGD …).
            return 0.0
        lots = risk_amt / max(pips * pip_val_usd, 1e-8)
    else:
        # Commodities, indices, stocks, crypto.
        # For commodities the SL distance is in price-per-unit (e.g. $/oz for silver),
        # so P&L per lot = sl_dist × contract_size.  Dividing only by sl_dist produces
        # a number in "units", not lots, and inflates size by up to ~5,000×.
        contract_size = _contract_size_for_ticker(ticker, asset_type)
        if contract_size is None:
            # Unknown commodity/futures — contract size is unverified.
            # Return 0 so the caller treats this as non-tradeable rather than
            # silently placing an order at a dangerously wrong size.
            return 0.0
        lots = risk_amt / (sl_dist * contract_size)
    return round(max(lots, 0.0), 2)
