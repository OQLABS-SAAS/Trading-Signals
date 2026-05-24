---
name: base
description: "Skill for the Base area of Trading-Signals. 2734 symbols across 706 files."
---

# Base

2734 symbols | 706 files | Cohesion: 65%

## When to Use

- Working with code in `research/`
- Understanding how Assert, UnWrapType, TestAccount work
- Modifying base-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `research/ccxt/ts/src/base/Exchange.ts` | loadMarkets, starknetEncodeStructuredData, encodeDydxTxForSimulation, encodeDydxTxForSigning, encodeDydxTxRaw (+313) |
| `research/ccxt/cs/ccxt/base/Exchange.BaseMethods.cs` | handleDelta, fetchAccounts, watchLiquidations, watchLiquidationsForSymbols, watchMyLiquidations (+192) |
| `research/ccxt/js/src/base/Exchange.js` | checkRequiredVersion, filterBySinceLimit, parseToInt, handleOptionAndParams, handleMaxEntriesPerRequestAndParams (+145) |
| `research/ccxt/go/tests/base/tests.go` | ParseCliArgsAndProps, Init, InitInner, CheckIfSpecificTestIsChosen, ImportFiles (+69) |
| `research/ccxt/python/ccxt/base/exchange.py` | filterBy, groupBy, lighter_sign_create_grouped_orders, lighter_sign_create_order, lighter_sign_cancel_order (+62) |
| `research/ccxt/go/tests/base/test.helpers.go` | SafeValue, Add, IsTrue, GetValue, Multiply (+41) |
| `research/ccxt/go/tests/base/test.sharedMethods.go` | LogTemplate, IsTemporaryFailure, StringValue, AssertType, AssertStructure (+27) |
| `research/ccxt/ts/src/base/Precise.ts` | Precise, mul, div, or, reduce (+26) |
| `research/ccxt/js/src/test/Exchange/base/test.sharedMethods.js` | logTemplate, isTemporaryFailure, stringValue, assertType, assertStructure (+21) |
| `research/ccxt/php/Exchange.php` | Exchange, keysort, seconds, milliseconds, parse_date (+20) |

## Entry Points

Start here when exploring this area:

- **`Assert`** (Function) — `research/ccxt/go/tests/base/helpers.go:34`
- **`UnWrapType`** (Function) — `research/ccxt/go/tests/base/helpers.go:73`
- **`TestAccount`** (Function) — `research/ccxt/go/tests/base/test.account.go:7`
- **`HelperTestSandboxState`** (Function) — `research/ccxt/go/tests/base/test.afterConstructor.go:27`
- **`TestBalance`** (Function) — `research/ccxt/go/tests/base/test.balance.go:7`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `NotSupported` | Class | `research/ccxt/cs/ccxt/base/Exchange.Errors.cs` | 155 |
| `NullResponse` | Class | `research/ccxt/cs/ccxt/base/Exchange.Errors.cs` | 233 |
| `Exchange` | Class | `research/ccxt/php/Exchange.php` | 63 |
| `ECDomainParameters` | Class | `research/ccxt/cs/ccxt/static/Portable.BouncyCastle/crypto/parameters/ECDomainParameters.cs` | 9 |
| `ECPublicKeyParameters` | Class | `research/ccxt/cs/ccxt/static/Portable.BouncyCastle/crypto/parameters/ECPublicKeyParameters.cs` | 8 |
| `PemReader` | Class | `research/ccxt/cs/ccxt/static/Portable.BouncyCastle/openssl/PEMReader.cs` | 29 |
| `InvalidParameterException` | Class | `research/ccxt/cs/ccxt/static/Portable.BouncyCastle/security/InvalidParameterException.cs` | 5 |
| `ExchangeError` | Class | `research/ccxt/python/ccxt/base/errors.py` | 69 |
| `AuthenticationError` | Class | `research/ccxt/python/ccxt/base/errors.py` | 73 |
| `PermissionDenied` | Class | `research/ccxt/python/ccxt/base/errors.py` | 77 |
| `BadRequest` | Class | `research/ccxt/python/ccxt/base/errors.py` | 93 |
| `OperationRejected` | Class | `research/ccxt/python/ccxt/base/errors.py` | 101 |
| `NoChange` | Class | `research/ccxt/python/ccxt/base/errors.py` | 105 |
| `InvalidAddress` | Class | `research/ccxt/python/ccxt/base/errors.py` | 129 |
| `InvalidOrder` | Class | `research/ccxt/python/ccxt/base/errors.py` | 137 |
| `NetworkError` | Class | `research/ccxt/cs/ccxt/base/Exchange.Errors.cs` | 179 |
| `RateLimitExceeded` | Class | `research/ccxt/cs/ccxt/base/Exchange.Errors.cs` | 191 |
| `ExchangeNotAvailable` | Class | `research/ccxt/cs/ccxt/base/Exchange.Errors.cs` | 197 |
| `BaseAccessor` | Class | `research/vectorbt/vectorbt/base/accessors.py` | 82 |
| `BaseSRAccessor` | Class | `research/vectorbt/vectorbt/base/accessors.py` | 706 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Main → Init` | cross_community | 4 |
| `Main → Exchange` | cross_community | 4 |
| `FetchPaginatedCallCursor → Capitalize` | cross_community | 4 |
| `FetchPaginatedCallDeterministic → Capitalize` | cross_community | 4 |
| `FetchPaginatedCallDynamic → Capitalize` | cross_community | 3 |

## Connected Areas

| Area | Connections |
|------|-------------|
| V4 | 1600 calls |
| Pro | 1061 calls |
| Php | 153 calls |
| Ccxt | 71 calls |
| Exchanges | 68 calls |
| Generic | 23 calls |
| Sync | 18 calls |
| Bip32 | 12 calls |

## How to Explore

1. `gitnexus_context({name: "Assert"})` — see callers and callees
2. `gitnexus_query({query: "base"})` — find related execution flows
3. Read key files listed above for implementation details
