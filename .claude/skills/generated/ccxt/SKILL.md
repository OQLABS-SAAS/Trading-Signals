---
name: ccxt
description: "Skill for the Ccxt area of Trading-Signals. 5135 symbols across 110 files."
---

# Ccxt

5135 symbols | 110 files | Cohesion: 74%

## When to Use

- Working with code in `research/`
- Understanding how ImplicitAPI, gate, gateio work
- Modifying ccxt-related functionality

## Key Files

| File | Symbols |
|------|---------|
| `research/ccxt/python/ccxt/base/exchange.py` | log, safe_string, safe_string_upper, safe_value, safe_string_upper_2 (+326) |
| `research/ccxt/python/ccxt/kucoin.py` | nonce, fetch_status, fetch_markets, fetch_uta_markets, load_migration_status (+153) |
| `research/ccxt/python/ccxt/bybit.py` | add_pagination_cursor_to_result, is_unified_enabled, get_bybit_type, get_amount, get_price (+131) |
| `research/ccxt/python/ccxt/okx.py` | handle_market_type_and_params, convert_to_instrument_type, fetch_status, fetch_time, fetch_accounts (+121) |
| `research/ccxt/python/ccxt/gate.py` | load_unified_status, fetch_markets, fetch_swap_markets, fetch_future_markets, prepare_request (+111) |
| `research/ccxt/python/ccxt/htx.py` | fetch_status, fetch_time, fetch_trading_fee, fetch_trading_limits, fetch_trading_limits_by_id (+102) |
| `research/ccxt/python/ccxt/hyperliquid.py` | market, fetch_status, fetch_currencies, fetch_markets, fetch_hip3_markets (+96) |
| `research/ccxt/python/ccxt/bingx.py` | fetch_currencies, fetch_spot_markets, fetch_swap_markets, fetch_inverse_swap_markets, fetch_markets (+85) |
| `research/ccxt/python/ccxt/bitmart.py` | fetch_status, fetch_currencies, get_currency_id_from_code_and_network, fetch_transaction_fee, fetch_deposit_withdraw_fee (+83) |
| `research/ccxt/python/ccxt/coinbase.py` | fetch_time, fetch_accounts, fetch_accounts_v2, fetch_accounts_v3, fetch_portfolios (+80) |

## Entry Points

Start here when exploring this area:

- **`ImplicitAPI`** (Class) — `research/ccxt/python/ccxt/abstract/gate.py:3`
- **`gate`** (Class) — `research/ccxt/python/ccxt/gate.py:29`
- **`gateio`** (Class) — `research/ccxt/python/ccxt/gateio.py:10`
- **`ImplicitAPI`** (Class) — `research/ccxt/python/ccxt/abstract/kucoin.py:3`
- **`kucoin`** (Class) — `research/ccxt/python/ccxt/kucoin.py:33`

## Key Symbols

| Symbol | Type | File | Line |
|--------|------|------|------|
| `ImplicitAPI` | Class | `research/ccxt/python/ccxt/abstract/gate.py` | 3 |
| `gate` | Class | `research/ccxt/python/ccxt/gate.py` | 29 |
| `gateio` | Class | `research/ccxt/python/ccxt/gateio.py` | 10 |
| `ImplicitAPI` | Class | `research/ccxt/python/ccxt/abstract/kucoin.py` | 3 |
| `kucoin` | Class | `research/ccxt/python/ccxt/kucoin.py` | 33 |
| `kucoinfutures` | Class | `research/ccxt/python/ccxt/kucoinfutures.py` | 11 |
| `fetch_tickers` | Method | `research/ccxt/python/ccxt/backpack.py` | 807 |
| `fetch_ticker` | Method | `research/ccxt/python/ccxt/backpack.py` | 823 |
| `fetch_order_book` | Method | `research/ccxt/python/ccxt/backpack.py` | 894 |
| `fetch_ohlcv` | Method | `research/ccxt/python/ccxt/backpack.py` | 931 |
| `fetch_funding_rate` | Method | `research/ccxt/python/ccxt/backpack.py` | 998 |
| `fetch_open_interest` | Method | `research/ccxt/python/ccxt/backpack.py` | 1054 |
| `fetch_funding_rate_history` | Method | `research/ccxt/python/ccxt/backpack.py` | 1096 |
| `fetch_trades` | Method | `research/ccxt/python/ccxt/backpack.py` | 1142 |
| `fetch_my_trades` | Method | `research/ccxt/python/ccxt/backpack.py` | 1171 |
| `fetch_deposits` | Method | `research/ccxt/python/ccxt/backpack.py` | 1350 |
| `fetch_withdrawals` | Method | `research/ccxt/python/ccxt/backpack.py` | 1380 |
| `withdraw` | Method | `research/ccxt/python/ccxt/backpack.py` | 1409 |
| `fetch_deposit_address` | Method | `research/ccxt/python/ccxt/backpack.py` | 1569 |
| `parse_deposit_address` | Method | `research/ccxt/python/ccxt/backpack.py` | 1592 |

## Execution Flows

| Flow | Type | Steps |
|------|------|-------|
| `Fetch_balance → Create_safe_dictionary` | cross_community | 4 |
| `Fetch_balance → Sort_by` | intra_community | 4 |
| `Fetch_balance → To_array` | intra_community | 4 |
| `Fetch_balance → Deep_extend` | cross_community | 4 |
| `Create_order → Create_safe_dictionary` | cross_community | 4 |
| `Create_order → Sort_by` | intra_community | 4 |
| `Create_order → To_array` | intra_community | 4 |
| `Create_order → Deep_extend` | cross_community | 4 |
| `Fetch_markets → Safe_string` | intra_community | 4 |
| `Fetch_markets → Omit` | intra_community | 4 |

## Connected Areas

| Area | Connections |
|------|-------------|
| Async_support | 709 calls |
| Base | 16 calls |
| Ecdsa | 3 calls |
| Crypto | 2 calls |
| Node-fetch | 1 calls |
| Cairo | 1 calls |

## How to Explore

1. `gitnexus_context({name: "ImplicitAPI"})` — see callers and callees
2. `gitnexus_query({query: "ccxt"})` — find related execution flows
3. Read key files listed above for implementation details
