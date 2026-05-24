---
name: v4
description: "Skill for the V4 area of Trading-Signals. 13845 symbols across 495 files."
---

# V4

13845 symbols | 495 files | Cohesion: 77%

## When to Use

- Working with code in `research/`
- Understanding how Totp, Jwt, Rsa work
- Modifying v4-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `research/ccxt/go/v4/exchange_generated.go` | HandleDelta, CheckProxySettings, EnableDemoTrading, FetchAccounts, FetchTrades (+491) |
| `research/ccxt/go/v4/exchange_wrappers.go` | FetchCurrencies, FetchMarkets, FetchTrades, WatchLiquidationsForSymbols, WatchMyTradesForSymbols (+245) |
| `research/ccxt/go/v4/kucoin_wrapper.go` | FetchTime, FetchStatus, FetchMarkets, FetchContractMarkets, FetchCurrencies (+228) |
| `research/ccxt/go/v4/coinbase_wrapper.go` | FetchTime, FetchAccounts, FetchAccountsV2, FetchAccountsV3, FetchPortfolios (+221) |
| `research/ccxt/go/v4/htx_wrapper.go` | FetchStatus, FetchTime, FetchTradingFee, FetchTradingLimits, FetchTradingLimitsById (+217) |
| `research/ccxt/go/v4/binance_wrapper.go` | FetchTime, FetchCurrencies, FetchMarkets, FetchBalance, FetchOrderBook (+216) |
| `research/ccxt/go/v4/gate_wrapper.go` | FetchTime, FetchMarkets, FetchSpotMarkets, FetchSwapMarkets, FetchFutureMarkets (+215) |
| `research/ccxt/go/v4/okx_wrapper.go` | FetchStatus, FetchTime, FetchAccounts, FetchMarkets, FetchMarketsByType (+212) |
| `research/ccxt/go/v4/hitbtc_wrapper.go` | FetchMarkets, FetchCurrencies, CreateDepositAddress, FetchDepositAddress, FetchBalance (+206) |
| `research/ccxt/go/v4/bybit.go` | EnableDemoTrading, Nonce, AddPaginationCursorToResult, IsUnifiedEnabled, UpgradeUnifiedTradeAccount (+126) |

## Entry Points

Start here when exploring this area:

- **`Totp`** (Function) — `research/ccxt/go/v4/exchange.go:815`
- **`Jwt`** (Function) — `research/ccxt/go/v4/exchange_crypto.go:209`
- **`Rsa`** (Function) — `research/ccxt/go/v4/exchange_crypto.go:268`
- **`Eddsa`** (Function) — `research/ccxt/go/v4/exchange_crypto.go:350`
- **`ExchangeError`** (Function) — `research/ccxt/go/v4/exchange_errors.go:5`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `Totp` | Function | `research/ccxt/go/v4/exchange.go` | 815 |
| `Jwt` | Function | `research/ccxt/go/v4/exchange_crypto.go` | 209 |
| `Rsa` | Function | `research/ccxt/go/v4/exchange_crypto.go` | 268 |
| `Eddsa` | Function | `research/ccxt/go/v4/exchange_crypto.go` | 350 |
| `ExchangeError` | Function | `research/ccxt/go/v4/exchange_errors.go` | 5 |
| `ArgumentsRequired` | Function | `research/ccxt/go/v4/exchange_errors.go` | 20 |
| `BadRequest` | Function | `research/ccxt/go/v4/exchange_errors.go` | 23 |
| `BadSymbol` | Function | `research/ccxt/go/v4/exchange_errors.go` | 26 |
| `InvalidAddress` | Function | `research/ccxt/go/v4/exchange_errors.go` | 50 |
| `InvalidOrder` | Function | `research/ccxt/go/v4/exchange_errors.go` | 56 |
| `OrderNotFound` | Function | `research/ccxt/go/v4/exchange_errors.go` | 59 |
| `NotSupported` | Function | `research/ccxt/go/v4/exchange_errors.go` | 77 |
| `NetworkError` | Function | `research/ccxt/go/v4/exchange_errors.go` | 89 |
| `DDoSProtection` | Function | `research/ccxt/go/v4/exchange_errors.go` | 92 |
| `NullResponse` | Function | `research/ccxt/go/v4/exchange_errors.go` | 116 |
| `ToGetsLimit` | Function | `research/ccxt/go/v4/exchange_future.go` | 22 |
| `IsTrue` | Function | `research/ccxt/go/v4/exchange_helpers.go` | 94 |
| `EvalTruthy` | Function | `research/ccxt/go/v4/exchange_helpers.go` | 99 |
| `Multiply` | Function | `research/ccxt/go/v4/exchange_helpers.go` | 462 |
| `Divide` | Function | `research/ccxt/go/v4/exchange_helpers.go` | 498 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `HandleMessage → ParseInt` | cross_community | 8 |
| `HandleMessage → ParseInt` | cross_community | 6 |
| `HandleMessage → BaseCache` | intra_community | 6 |
| `HandleMessage → ToFloat64` | cross_community | 6 |
| `HandleMessage → ToFloat64` | cross_community | 6 |
| `HandleMessage → ToFloat64` | cross_community | 6 |
| `SafeOrder → GetValueFromList` | intra_community | 5 |
| `HandleOrder → BaseCache` | intra_community | 5 |
| `HandleOrder → BaseCache` | intra_community | 5 |
| `HandleOrderBook → ParseInt` | cross_community | 5 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Pro | 107 calls |
| Base | 39 calls |
| Omni_files | 1 calls |

## How to Explore

1. `gitnexus_context({name: "Totp"})` — see callers and callees
2. `gitnexus_query({query: "v4"})` — find related execution flows
3. Read key files listed above for implementation details
