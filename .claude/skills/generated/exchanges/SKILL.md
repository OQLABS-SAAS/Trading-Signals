---
name: exchanges
description: "Skill for the Exchanges area of Trading-Signals. 2233 symbols across 142 files."
---

# Exchanges

2233 symbols | 142 files | Cohesion: 65%

## When to Use

- Working with code in `research/`
- Understanding how Precise, ArgumentsRequired, ExchangeError work
- Modifying exchanges-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `research/ccxt/cs/ccxt/exchanges/bybit.cs` | parseLedgerEntry, parsePosition, fetchOrderBook, fetchMarkets, fetchDerivativesOpenInterestHistory (+82) |
| `research/ccxt/cs/ccxt/exchanges/gate.cs` | safeMarket, parseContractMarket, fetchOptionMarkets, parseTrade, withdraw (+76) |
| `research/ccxt/cs/ccxt/exchanges/okx.cs` | parseMarket, createOrderRequest, parseLedgerEntry, fetchPositions, parsePosition (+71) |
| `research/ccxt/cs/ccxt/exchanges/hyperliquid.cs` | calculatePricePrecision, amountToPrecision, priceToPrecision, createOrderRequest, editOrdersRequest (+67) |
| `research/ccxt/cs/ccxt/exchanges/phemex.cs` | fetchPositions, parsePosition, setMarginMode, cancelAllOrders, fetchOrders (+51) |
| `research/ccxt/cs/ccxt/exchanges/htx.cs` | parseTrade, fetchTrades, fetchMyTrades, setLeverage, fetchSettlementHistory (+50) |
| `research/ccxt/cs/ccxt/exchanges/coinex.cs` | modifyMarginHelper, parseMarginModification, fetchFundingHistory, fetchFundingRateHistory, fetchIsolatedBorrowRate (+45) |
| `research/ccxt/cs/ccxt/exchanges/bitmart.cs` | fetchSpotMarkets, fetchMarkets, parseLedgerEntry, cancelAllOrders, fetchClosedOrders (+40) |
| `research/ccxt/cs/ccxt/exchanges/mexc.cs` | fetchTicker, parseTicker, parseMarketLeverageTiers, fetchMyTrades, fetchOrderTrades (+39) |
| `research/ccxt/cs/ccxt/exchanges/pacifica.cs` | fetchOrder, parseOrder, fetchOHLCV, fetchMyTrades, fetchFundingRateHistory (+39) |

## Entry Points

Start here when exploring this area:

- **`Precise`** (Class) — `research/ccxt/cs/ccxt/base/Exchange.Precise.cs:6`
- **`ArgumentsRequired`** (Class) — `research/ccxt/cs/ccxt/base/Exchange.Errors.cs:41`
- **`ExchangeError`** (Class) — `research/ccxt/cs/ccxt/base/Exchange.Errors.cs:11`
- **`BadRequest`** (Class) — `research/ccxt/cs/ccxt/base/Exchange.Errors.cs:47`
- **`BadSymbol`** (Class) — `research/ccxt/cs/ccxt/base/Exchange.Errors.cs:53`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `Precise` | Class | `research/ccxt/cs/ccxt/base/Exchange.Precise.cs` | 6 |
| `ArgumentsRequired` | Class | `research/ccxt/cs/ccxt/base/Exchange.Errors.cs` | 41 |
| `ExchangeError` | Class | `research/ccxt/cs/ccxt/base/Exchange.Errors.cs` | 11 |
| `BadRequest` | Class | `research/ccxt/cs/ccxt/base/Exchange.Errors.cs` | 47 |
| `BadSymbol` | Class | `research/ccxt/cs/ccxt/base/Exchange.Errors.cs` | 53 |
| `InvalidOrder` | Class | `research/ccxt/cs/ccxt/base/Exchange.Errors.cs` | 113 |
| `InvalidAddress` | Class | `research/ccxt/cs/ccxt/base/Exchange.Errors.cs` | 101 |
| `OrderNotFound` | Class | `research/ccxt/cs/ccxt/base/Exchange.Errors.cs` | 119 |
| `AuthenticationError` | Class | `research/ccxt/cs/ccxt/base/Exchange.Errors.cs` | 17 |
| `PermissionDenied` | Class | `research/ccxt/cs/ccxt/base/Exchange.Errors.cs` | 23 |
| `InsufficientFunds` | Class | `research/ccxt/cs/ccxt/base/Exchange.Errors.cs` | 95 |
| `DDoSProtection` | Class | `research/ccxt/cs/ccxt/base/Exchange.Errors.cs` | 185 |
| `AddressPending` | Class | `research/ccxt/cs/ccxt/base/Exchange.Errors.cs` | 107 |
| `integerPrecisionToAmount` | Method | `research/ccxt/cs/ccxt/base/Exchange.BaseMethods.cs` | 6477 |
| `div` | Method | `research/ccxt/cs/ccxt/base/Exchange.Precise.cs` | 49 |
| `add` | Method | `research/ccxt/cs/ccxt/base/Exchange.Precise.cs` | 73 |
| `mod` | Method | `research/ccxt/cs/ccxt/base/Exchange.Precise.cs` | 101 |
| `sub` | Method | `research/ccxt/cs/ccxt/base/Exchange.Precise.cs` | 111 |
| `neg` | Method | `research/ccxt/cs/ccxt/base/Exchange.Precise.cs` | 124 |
| `ge` | Method | `research/ccxt/cs/ccxt/base/Exchange.Precise.cs` | 145 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Base | 176 calls |
| Pro | 24 calls |
| Math | 1 calls |

## How to Explore

1. `gitnexus_context({name: "Precise"})` — see callers and callees
2. `gitnexus_query({query: "exchanges"})` — find related execution flows
3. Read key files listed above for implementation details
