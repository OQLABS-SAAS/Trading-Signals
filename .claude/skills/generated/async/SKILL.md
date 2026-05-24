---
name: async
description: "Skill for the Async area of Trading-Signals. 2581 symbols across 270 files."
---

# Async

2581 symbols | 270 files | Cohesion: 66%

## When to Use

- Working with code in `research/`
- Understanding how test_proxies, test_proxy_url, test_http_proxy work
- Modifying async-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `research/ccxt/php/async/Exchange.php` | edit_order_ws, create_trailing_amount_order_ws, create_trailing_percent_order_ws, create_market_order_with_cost_ws, create_trigger_order_ws (+178) |
| `research/ccxt/php/async/okx.php` | fetch_funding_rate_history, fetch_accounts, fetch_position_mode, fetch_deposit_addresses_by_network, fetch_deposit_address (+73) |
| `research/ccxt/php/async/hyperliquid.php` | market, amount_to_precision, price_to_precision, sign_l1_action, set_ref (+71) |
| `research/ccxt/php/async/gate.php` | transfer, fetch_my_liquidations, prepare_request, fetch_funding_rate, parse_funding_rate (+70) |
| `research/ccxt/php/async/coinex.php` | fetch_funding_history, fetch_funding_rate_history, fetch_margin_adjustment_history, create_market_buy_order_with_cost, create_order_request (+46) |
| `research/ccxt/php/async/mexc.php` | fetch_trades, modify_margin_helper, fetch_funding_rate_history, create_deposit_address, fetch_deposits (+45) |
| `research/ccxt/php/async/pacifica.php` | fetch_ohlcv, set_margin_mode, set_leverage, withdraw, transfer (+43) |
| `research/ccxt/php/async/phemex.php` | cancel_all_orders, fetch_open_orders, fetch_deposit_address, fetch_transfers, custom_parse_bid_ask (+42) |
| `research/ccxt/php/async/bitmart.php` | fetch_my_trades, cancel_orders, cancel_all_orders, fetch_orders_by_status, fetch_borrow_interest (+41) |
| `research/ccxt/php/async/coinbase.php` | fetch_positions, fetch_position, sign, create_deposit_address, create_market_buy_order_with_cost (+40) |

## Entry Points

Start here when exploring this area:

- **`test_proxies`** (Function) — `research/ccxt/php/test/exchange/async/test_proxies.php:12`
- **`test_proxy_url`** (Function) — `research/ccxt/php/test/exchange/async/test_proxies.php:22`
- **`test_http_proxy`** (Function) — `research/ccxt/php/test/exchange/async/test_proxies.php:40`
- **`test_proxy_for_exceptions`** (Function) — `research/ccxt/php/test/exchange/async/test_proxies.php:56`
- **`remove_proxy_options`** (Function) — `research/ccxt/php/test/exchange/base/test_shared_methods.php:578`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `ArgumentsRequired` | Class | `research/ccxt/php/ArgumentsRequired.php` | 6 |
| `ExchangeError` | Class | `research/ccxt/php/ExchangeError.php` | 6 |
| `AuthenticationError` | Class | `research/ccxt/php/AuthenticationError.php` | 6 |
| `InvalidAddress` | Class | `research/ccxt/php/InvalidAddress.php` | 6 |
| `Throttler` | Class | `research/ccxt/php/async/Throttler.php` | 9 |
| `ProxyConnector` | Class | `research/ccxt/php/static_dependencies/proxies/reactphp-http-proxy/src/ProxyConnector.php` | 45 |
| `test_proxies` | Function | `research/ccxt/php/test/exchange/async/test_proxies.php` | 12 |
| `test_proxy_url` | Function | `research/ccxt/php/test/exchange/async/test_proxies.php` | 22 |
| `test_http_proxy` | Function | `research/ccxt/php/test/exchange/async/test_proxies.php` | 40 |
| `test_proxy_for_exceptions` | Function | `research/ccxt/php/test/exchange/async/test_proxies.php` | 56 |
| `remove_proxy_options` | Function | `research/ccxt/php/test/exchange/base/test_shared_methods.php` | 578 |
| `set_proxy_options` | Function | `research/ccxt/php/test/exchange/base/test_shared_methods.php` | 594 |
| `test_proxies` | Function | `research/ccxt/php/test/exchange/sync/test_proxies.php` | 11 |
| `test_proxy_url` | Function | `research/ccxt/php/test/exchange/sync/test_proxies.php` | 19 |
| `test_http_proxy` | Function | `research/ccxt/php/test/exchange/sync/test_proxies.php` | 35 |
| `test_proxy_for_exceptions` | Function | `research/ccxt/php/test/exchange/sync/test_proxies.php` | 49 |
| `tco_debug` | Function | `research/ccxt/php/test/exchange/async/test_create_order.php` | 15 |
| `test_create_order` | Function | `research/ccxt/php/test/exchange/async/test_create_order.php` | 27 |
| `tco_create_unfillable_order` | Function | `research/ccxt/php/test/exchange/async/test_create_order.php` | 67 |
| `tco_create_fillable_order` | Function | `research/ccxt/php/test/exchange/async/test_create_order.php` | 112 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Safe_order → Filter_by_limit` | cross_community | 6 |
| `Safe_order → NotSupported` | cross_community | 5 |
| `Safe_ticker → Gmp_pow` | cross_community | 4 |
| `Safe_ticker → Precise` | cross_community | 4 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Php | 839 calls |
| Sync | 20 calls |
| Abstract | 14 calls |
| Base | 14 calls |
| Pro | 12 calls |
| Cluster_6935 | 2 calls |
| Async_support | 1 calls |
| Cluster_6954 | 1 calls |

## How to Explore

1. `gitnexus_context({name: "test_proxies"})` — see callers and callees
2. `gitnexus_query({query: "async"})` — find related execution flows
3. Read key files listed above for implementation details
