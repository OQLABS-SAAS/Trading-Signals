---
name: abstract
description: "Skill for the Abstract area of Trading-Signals. 1139 symbols across 561 files."
---

# Abstract

1139 symbols | 561 files | Cohesion: 71%

## When to Use

- Working with code in `research/`
- Understanding how isogenyMap, mod, pow work
- Modifying abstract-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `research/ccxt/ts/src/static_dependencies/noble-curves/abstract/weierstrass.ts` | normPrivateKeyToScalar, fromPrivateKey, prepSig, SWUFpSqrtRatio, sqrtRatio (+55) |
| `research/ccxt/js/src/static_dependencies/noble-curves/abstract/weierstrass.js` | weierstrassEquation, fromAffine, is0, normalizeZ, assertValidity (+52) |
| `research/ccxt/js/src/hyperliquid.js` | market, updateSpotCurrencyCode, fetchBalance, fetchOrderBook, fetchTrades (+36) |
| `research/ccxt/js/src/static_dependencies/noble-curves/abstract/edwards.js` | assertInRange, assertGE0, normalizeZ, equals, is0 (+29) |
| `research/ccxt/ts/src/static_dependencies/noble-curves/abstract/edwards.ts` | assertInRange, assertGE0, fromHex, modN, modN_LE (+26) |
| `research/ccxt/js/src/static_dependencies/noble-curves/abstract/modular.js` | mod, pow, FpPow, FpInvertBatch, lastMultiplied (+22) |
| `research/ccxt/ts/src/static_dependencies/noble-curves/abstract/modular.ts` | pow, tonelliShanks, FpSqrt, neg, sqr (+21) |
| `research/ccxt/ts/src/static_dependencies/noble-curves/abstract/utils.ts` | u8a, bytesToHex, bytesToNumberLE, ensureBytes, concatBytes (+13) |
| `research/ccxt/js/src/static_dependencies/noble-curves/abstract/utils.js` | u8a, bytesToHex, bytesToNumberLE, ensureBytes, concatBytes (+11) |
| `research/ccxt/js/src/dydx.js` | hashMessage, signDydxTx, retrieveCredentials, fetchDydxAccount, fetchLatestBlockHeight (+7) |

## Entry Points

Start here when exploring this area:

- **`isogenyMap`** (Function) — `research/ccxt/js/src/static_dependencies/noble-curves/abstract/hash-to-curve.js:138`
- **`mod`** (Function) — `research/ccxt/js/src/static_dependencies/noble-curves/abstract/modular.js:16`
- **`pow`** (Function) — `research/ccxt/js/src/static_dependencies/noble-curves/abstract/modular.js:27`
- **`FpPow`** (Function) — `research/ccxt/js/src/static_dependencies/noble-curves/abstract/modular.js:214`
- **`FpInvertBatch`** (Function) — `research/ccxt/js/src/static_dependencies/noble-curves/abstract/modular.js:233`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `Exchange` | Class | `research/ccxt/js/src/base/Exchange.js` | 54 |
| `coinbase` | Class | `research/ccxt/js/src/coinbase.js` | 18 |
| `gate` | Class | `research/ccxt/js/src/gate.js` | 16 |
| `hitbtc` | Class | `research/ccxt/js/src/hitbtc.js` | 15 |
| `htx` | Class | `research/ccxt/js/src/htx.js` | 17 |
| `okx` | Class | `research/ccxt/js/src/okx.js` | 17 |
| `Point` | Class | `research/ccxt/js/src/static_dependencies/noble-curves/abstract/weierstrass.js` | 154 |
| `Point` | Class | `research/ccxt/ts/src/static_dependencies/noble-curves/abstract/weierstrass.ts` | 237 |
| `Signature` | Class | `research/ccxt/ts/src/static_dependencies/noble-curves/abstract/weierstrass.ts` | 729 |
| `Signature` | Class | `research/ccxt/js/src/static_dependencies/noble-curves/abstract/weierstrass.js` | 581 |
| `Point` | Class | `research/ccxt/js/src/static_dependencies/noble-curves/abstract/edwards.js` | 76 |
| `ImplicitAPI` | Class | `research/ccxt/python/ccxt/abstract/coinbase.py` | 3 |
| `ImplicitAPI` | Class | `research/ccxt/python/ccxt/abstract/coinbaseadvanced.py` | 3 |
| `coinbase` | Class | `research/ccxt/python/ccxt/async_support/coinbase.py` | 26 |
| `coinbaseadvanced` | Class | `research/ccxt/python/ccxt/async_support/coinbaseadvanced.py` | 10 |
| `coinbase` | Class | `research/ccxt/python/ccxt/coinbase.py` | 25 |
| `coinbaseadvanced` | Class | `research/ccxt/python/ccxt/coinbaseadvanced.py` | 10 |
| `ImplicitAPI` | Class | `research/ccxt/python/ccxt/abstract/htx.py` | 3 |
| `ImplicitAPI` | Class | `research/ccxt/python/ccxt/abstract/huobi.py` | 3 |
| `htx` | Class | `research/ccxt/python/ccxt/async_support/htx.py` | 32 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Pro | 252 calls |
| Base | 38 calls |
| Php | 33 calls |
| Async | 29 calls |
| Noble-curves | 14 calls |
| List | 4 calls |
| Scure-starknet | 3 calls |
| Calldata | 3 calls |

## How to Explore

1. `gitnexus_context({name: "isogenyMap"})` — see callers and callees
2. `gitnexus_query({query: "abstract"})` — find related execution flows
3. Read key files listed above for implementation details
