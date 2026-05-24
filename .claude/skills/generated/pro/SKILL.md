---
name: pro
description: "Skill for the Pro area of Trading-Signals. 11822 symbols across 911 files."
---

# Pro

11822 symbols | 911 files | Cohesion: 73%

## When to Use

- Working with code in `research/`
- Understanding how NewTestMainClass, SetDefaults, NewAftermathCore work
- Modifying pro-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `research/ccxt/js/src/base/Exchange.js` | loadMarkets, checkAddress, fetchAccounts, watchLiquidations, watchLiquidationsForSymbols (+121) |
| `research/ccxt/js/src/bybit.js` | addPaginationCursorToResult, isUnifiedEnabled, safeMarket, getBybitType, getAmount (+115) |
| `research/ccxt/cs/ccxt/base/Exchange.BaseMethods.cs` | safeBool, safeList, filterByValueSinceLimit, parseTransfer, parseToInt (+107) |
| `research/ccxt/js/src/okx.js` | handleMarketTypeAndParams, convertToInstrumentType, fetchMarkets, fetchMarketsByType, fetchOrderBook (+105) |
| `research/ccxt/js/src/gate.js` | describe, loadUnifiedStatus, prepareRequest, spotOrderPrepareRequest, multiOrderSpotPrepareRequest (+89) |
| `research/ccxt/js/src/htx.js` | describe, fetchTradingFee, fetchTradingLimits, fetchTradingLimitsById, fetchMarkets (+83) |
| `research/ccxt/js/src/pro/binance.js` | describeData, requestId, stream, getWsUrl, getFutureWsCategory (+76) |
| `research/ccxt/python/ccxt/pro/binance.py` | stream, get_ws_url, get_future_ws_category, watch_liquidations_for_symbols, watch_order_book_for_symbols (+73) |
| `research/ccxt/php/pro/binance.php` | handle_liquidation, parse_ws_liquidation, handle_my_liquidation, parse_ws_trade, handle_trade (+69) |
| `research/ccxt/ts/src/pro/binance.ts` | handleLiquidation, parseWsLiquidation, handleMyLiquidation, parseWsTrade, handleTrade (+69) |

## Entry Points

Start here when exploring this area:

- **`NewTestMainClass`** (Function) — `research/ccxt/go/tests/base/tests.go:32`
- **`SetDefaults`** (Function) — `research/ccxt/go/v4/exchange_helpers.go:2618`
- **`NewAftermathCore`** (Function) — `research/ccxt/go/v4/pro/aftermath.go:11`
- **`NewAlpacaCore`** (Function) — `research/ccxt/go/v4/pro/alpaca.go:11`
- **`NewApexCore`** (Function) — `research/ccxt/go/v4/pro/apex.go:11`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `ArrayCache` | Class | `research/ccxt/php/pro/ArrayCache.php` | 4 |
| `ArrayCacheBySymbolById` | Class | `research/ccxt/cs/ccxt/ws/ArrayCache.cs` | 208 |
| `ArrayCacheBySymbolById` | Class | `research/ccxt/php/pro/ArrayCacheBySymbolById.php` | 4 |
| `ArrayCacheByTimestamp` | Class | `research/ccxt/php/pro/ArrayCacheByTimestamp.php` | 4 |
| `ArrayCache` | Class | `research/ccxt/cs/ccxt/ws/ArrayCache.cs` | 29 |
| `ArrayCacheBySymbolBySide` | Class | `research/ccxt/php/pro/ArrayCacheBySymbolBySide.php` | 4 |
| `ArrayCacheBySymbolBySide` | Class | `research/ccxt/cs/ccxt/ws/ArrayCache.cs` | 296 |
| `ArrayCacheByTimestamp` | Class | `research/ccxt/cs/ccxt/ws/ArrayCache.cs` | 135 |
| `InvalidNonce` | Class | `research/ccxt/cs/ccxt/base/Exchange.Errors.cs` | 209 |
| `ChecksumError` | Class | `research/ccxt/cs/ccxt/base/Exchange.Errors.cs` | 215 |
| `OrderBookSide` | Class | `research/ccxt/php/pro/OrderBookSide.php` | 17 |
| `Asks` | Class | `research/ccxt/php/pro/OrderBookSide.php` | 228 |
| `Bids` | Class | `research/ccxt/php/pro/OrderBookSide.php` | 229 |
| `UnsubscribeError` | Class | `research/ccxt/cs/ccxt/base/Exchange.Errors.cs` | 245 |
| `ChecksumError` | Class | `research/ccxt/php/ChecksumError.php` | 6 |
| `UnsubscribeError` | Class | `research/ccxt/php/UnsubscribeError.php` | 6 |
| `OrderBook` | Class | `research/ccxt/php/pro/OrderBook.php` | 4 |
| `CountedOrderBook` | Class | `research/ccxt/php/pro/OrderBook.php` | 74 |
| `IndexedOrderBook` | Class | `research/ccxt/php/pro/OrderBook.php` | 85 |
| `InvalidNonce` | Class | `research/ccxt/php/InvalidNonce.php` | 6 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Main → Describe` | cross_community | 4 |
| `Main → Describe` | cross_community | 4 |
| `Main → Describe` | cross_community | 4 |
| `Main → Describe` | cross_community | 4 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Base | 1005 calls |
| Exchanges | 218 calls |
| Php | 174 calls |
| V4 | 119 calls |
| Async | 108 calls |
| Abstract | 75 calls |
| Async_support | 45 calls |
| Ws | 15 calls |

## How to Explore

1. `gitnexus_context({name: "NewTestMainClass"})` — see callers and callees
2. `gitnexus_query({query: "pro"})` — find related execution flows
3. Read key files listed above for implementation details
