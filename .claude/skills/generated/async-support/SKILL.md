---
name: async-support
description: "Skill for the Async_support area of Trading-Signals. 3291 symbols across 142 files."
---

# Async_support

3291 symbols | 142 files | Cohesion: 60%

## When to Use

- Working with code in `research/`
- Understanding how test_number, test_precise, tco_assert_filled_order work
- Modifying async_support-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `research/ccxt/python/ccxt/async_support/kucoin.py` | fetch_transaction_fee, fetch_deposit_withdraw_fee, fetch_order_book, fetch_trades, fetch_deposits (+113) |
| `research/ccxt/python/ccxt/async_support/bybit.py` | fetch_funding_rates, fetch_order_book, fetch_order_classic, fetch_order, fetch_orders (+98) |
| `research/ccxt/python/ccxt/async_support/okx.py` | fetch_order_book, cancel_orders_for_symbols, fetch_deposit_addresses_by_network, fetch_deposit_address, fetch_leverage (+90) |
| `research/ccxt/python/ccxt/async_support/gate.py` | fetch_network_deposit_address, fetch_deposit_addresses_by_network, fetch_deposit_address, fetch_order_trades, fetch_my_trades (+88) |
| `research/ccxt/python/ccxt/async_support/hyperliquid.py` | fetch_open_interests, fetch_open_interest, calculate_price_precision, amount_to_precision, price_to_precision (+73) |
| `research/ccxt/python/ccxt/async_support/htx.py` | fetch_trading_fee, fetch_trading_limits, fetch_trading_limits_by_id, parse_ticker, fetch_ticker (+70) |
| `research/ccxt/python/ccxt/async_support/phemex.py` | fetch_ohlcv, fetch_tickers, fetch_trades, cancel_all_orders, fetch_orders (+61) |
| `research/ccxt/python/ccxt/async_support/coinbase.py` | cancel_order, cancel_orders, fetch_trades, fetch_order_book, fetch_positions (+57) |
| `research/ccxt/python/ccxt/async_support/bitmart.py` | fetch_order_book, fetch_trades, fetch_my_trades, fetch_trading_fee, cancel_order (+56) |
| `research/ccxt/python/ccxt/async_support/coinex.py` | fetch_ticker, fetch_tickers, fetch_order_book, fetch_trades, fetch_ohlcv (+56) |

## Entry Points

Start here when exploring this area:

- **`test_number`** (Function) — `research/ccxt/python/ccxt/test/base/test_number.py:26`
- **`test_precise`** (Function) — `research/ccxt/python/ccxt/test/base/test_precise.py:16`
- **`tco_assert_filled_order`** (Function) — `research/ccxt/python/ccxt/test/exchange/async/test_create_order.py:141`
- **`test_balance`** (Function) — `research/ccxt/python/ccxt/test/exchange/base/test_balance.py:17`
- **`test_liquidation`** (Function) — `research/ccxt/python/ccxt/test/exchange/base/test_liquidation.py:17`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `ImplicitAPI` | Class | `research/ccxt/python/ccxt/abstract/gateio.py` | 3 |
| `gate` | Class | `research/ccxt/python/ccxt/async_support/gate.py` | 30 |
| `gateio` | Class | `research/ccxt/python/ccxt/async_support/gateio.py` | 10 |
| `ImplicitAPI` | Class | `research/ccxt/python/ccxt/abstract/kucoinfutures.py` | 3 |
| `kucoin` | Class | `research/ccxt/python/ccxt/async_support/kucoin.py` | 34 |
| `kucoinfutures` | Class | `research/ccxt/python/ccxt/async_support/kucoinfutures.py` | 11 |
| `test_number` | Function | `research/ccxt/python/ccxt/test/base/test_number.py` | 26 |
| `test_precise` | Function | `research/ccxt/python/ccxt/test/base/test_precise.py` | 16 |
| `tco_assert_filled_order` | Function | `research/ccxt/python/ccxt/test/exchange/async/test_create_order.py` | 141 |
| `test_balance` | Function | `research/ccxt/python/ccxt/test/exchange/base/test_balance.py` | 17 |
| `test_liquidation` | Function | `research/ccxt/python/ccxt/test/exchange/base/test_liquidation.py` | 17 |
| `test_market` | Function | `research/ccxt/python/ccxt/test/exchange/base/test_market.py` | 17 |
| `test_order_book` | Function | `research/ccxt/python/ccxt/test/exchange/base/test_order_book.py` | 17 |
| `assert_order_state` | Function | `research/ccxt/python/ccxt/test/exchange/base/test_shared_methods.py` | 423 |
| `test_ticker` | Function | `research/ccxt/python/ccxt/test/exchange/base/test_ticker.py` | 17 |
| `tco_assert_filled_order` | Function | `research/ccxt/python/ccxt/test/exchange/sync/test_create_order.py` | 141 |
| `fetch_order_book` | Method | `research/ccxt/python/ccxt/async_support/ascendex.py` | 1057 |
| `fetch_ticker` | Method | `research/ccxt/python/ccxt/async_support/ascendex.py` | 1147 |
| `fetch_tickers` | Method | `research/ccxt/python/ccxt/async_support/ascendex.py` | 1179 |
| `fetch_ohlcv` | Method | `research/ccxt/python/ccxt/async_support/ascendex.py` | 1252 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Ccxt | 174 calls |
| Pro | 37 calls |
| Base | 6 calls |

## How to Explore

1. `gitnexus_context({name: "test_number"})` — see callers and callees
2. `gitnexus_query({query: "async_support"})` — find related execution flows
3. Read key files listed above for implementation details
