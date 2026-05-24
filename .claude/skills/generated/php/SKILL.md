---
name: php
description: "Skill for the Php area of Trading-Signals. 2504 symbols across 280 files."
---

# Php

2504 symbols | 280 files | Cohesion: 58%

## When to Use

- Working with code in `research/`
- Understanding how test_number, test_precise, helper_test_handle_market_type_and_params work
- Modifying php-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `research/ccxt/php/Exchange.php` | extend, load_markets, handle_delta, watch_liquidations, watch_liquidations_for_symbols (+402) |
| `research/ccxt/php/async/Exchange.php` | load_markets, safe_dict, handle_delta, fetch_accounts, watch_liquidations (+70) |
| `research/ccxt/php/bybit.php` | fetch_derivatives_open_interest_history, fetch_open_interest_history, parse_liquidation, parse_ledger_entry, is_unified_enabled (+70) |
| `research/ccxt/php/gate.php` | sign, fetch_leverage, edit_order_request, edit_order, parse_order (+66) |
| `research/ccxt/php/hyperliquid.php` | market, fetch_balance, fetch_trades, amount_to_precision, price_to_precision (+66) |
| `research/ccxt/php/okx.php` | fetch_leverage, set_leverage, set_margin_mode, fetch_margin_adjustment_history, parse_ledger_entry (+52) |
| `research/ccxt/php/htx.php` | fetch_order_trades, transfer, fetch_open_interest, set_position_mode, parse_trade (+47) |
| `research/ccxt/php/phemex.php` | fetch_funding_history, parse_funding_fee_to_precision, set_leverage, fetch_funding_rate_history, fetch_open_interest (+45) |
| `research/ccxt/php/pacifica.php` | parse_order, fetch_my_trades, fetch_funding_rate_history, fetch_orders, add_pagination_cursor_to_result (+35) |
| `research/ccxt/php/bitmart.php` | fetch_trading_fee, fetch_open_interest, parse_liquidation, set_leverage, fetch_funding_rate (+32) |

## Entry Points

Start here when exploring this area:

- **`test_number`** (Function) — `research/ccxt/php/test/base/test_number.php:11`
- **`test_precise`** (Function) — `research/ccxt/php/test/base/test_precise.php:11`
- **`helper_test_handle_market_type_and_params`** (Function) — `research/ccxt/php/test/base/test_handle_methods.php:11`
- **`test_safe_methods`** (Function) — `research/ccxt/php/test/base/test_safe_methods.php:14`
- **`test_to_array`** (Function) — `research/ccxt/php/test/base/test_to_array.php:11`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `NotSupported` | Class | `research/ccxt/php/NotSupported.php` | 6 |
| `NullResponse` | Class | `research/ccxt/php/NullResponse.php` | 6 |
| `BadRequest` | Class | `research/ccxt/php/BadRequest.php` | 6 |
| `Precise` | Class | `research/ccxt/php/Precise.php` | 4 |
| `BadSymbol` | Class | `research/ccxt/php/BadSymbol.php` | 6 |
| `InvalidOrder` | Class | `research/ccxt/php/InvalidOrder.php` | 6 |
| `OrderNotFound` | Class | `research/ccxt/php/OrderNotFound.php` | 6 |
| `DDoSProtection` | Class | `research/ccxt/php/DDoSProtection.php` | 6 |
| `BaseError` | Class | `research/ccxt/php/BaseError.php` | 6 |
| `htx` | Class | `research/ccxt/php/htx.php` | 10 |
| `okx` | Class | `research/ccxt/php/okx.php` | 10 |
| `kraken` | Class | `research/ccxt/php/kraken.php` | 10 |
| `InvalidProxySettings` | Class | `research/ccxt/php/InvalidProxySettings.php` | 6 |
| `EC` | Class | `research/ccxt/php/static_dependencies/elliptic-php/lib/EC.php` | 9 |
| `InsufficientFunds` | Class | `research/ccxt/php/InsufficientFunds.php` | 6 |
| `bingx` | Class | `research/ccxt/php/bingx.php` | 10 |
| `AddressPending` | Class | `research/ccxt/php/AddressPending.php` | 6 |
| `BadResponse` | Class | `research/ccxt/php/BadResponse.php` | 6 |
| `EdDSA` | Class | `research/ccxt/php/static_dependencies/elliptic-php/lib/EdDSA.php` | 7 |
| `phemex` | Class | `research/ccxt/php/phemex.php` | 10 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Safe_order → Filter_by_limit` | cross_community | 6 |
| `Safe_order → NotSupported` | cross_community | 5 |
| `Safe_ticker → Gmp_pow` | cross_community | 4 |
| `Safe_ticker → Precise` | cross_community | 4 |
| `Safe_order → Gmp_pow` | cross_community | 4 |
| `Safe_order → Precise` | cross_community | 4 |
| `Safe_order → Valid_object_value` | cross_community | 3 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Async | 454 calls |
| Base | 67 calls |
| Pro | 23 calls |
| Crypto | 4 calls |
| Contracts | 3 calls |
| BN | 3 calls |
| EdDSA | 2 calls |
| Cairo | 2 calls |

## How to Explore

1. `gitnexus_context({name: "test_number"})` — see callers and callees
2. `gitnexus_query({query: "php"})` — find related execution flows
3. Read key files listed above for implementation details
